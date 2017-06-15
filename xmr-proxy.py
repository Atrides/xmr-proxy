#!/usr/bin/env python
# -*- coding:utf-8 -*-

import time
import os
import socket

from stratum import settings
import stratum.logger
log = stratum.logger.get_logger('proxy')

if __name__ == '__main__':
    if (settings.PAYMENT_ID and len(settings.PAYMENT_ID)!=64) or (len(settings.WALLET)!=95 and len(settings.WALLET)!=106):
        log.error("Wrong PAYMENT_ID or WALLET !!!")
        quit()
    settings.CUSTOM_USER = settings.WALLET if not settings.PAYMENT_ID else "%s.%s" % (settings.WALLET, settings.PAYMENT_ID)
    settings.CUSTOM_PASSWORD = settings.MONITORING_EMAIL if settings.MONITORING_EMAIL and settings.MONITORING else "1"

from twisted.internet import reactor, defer, protocol
from twisted.internet import reactor as reactor2
from stratum.socket_transport import SocketTransportFactory, SocketTransportClientFactory
from stratum.services import ServiceEventHandler
from twisted.web.server import Site
from stratum.custom_exceptions import TransportException

from mining_libs import stratum_listener
from mining_libs import client_service
from mining_libs import jobs
from mining_libs import multicast_responder
from mining_libs import version
from mining_libs.jobs import Job

def on_shutdown(f):
    '''Clean environment properly'''
    log.info("Shutting down proxy...")
    if os.path.isfile('xmr-proxy.pid'):
        os.remove('xmr-proxy.pid')
    f.is_reconnecting = False # Don't let stratum factory to reconnect again

# Support main connection
@defer.inlineCallbacks
def ping(f, id):
    if not f.is_reconnecting:
        return
    try:
        yield (f.rpc('getjob', {"id":id,}))
        reactor.callLater(300, ping, f, id)
    except Exception:
        pass

@defer.inlineCallbacks
def on_connect(f):
    '''Callback when proxy get connected to the pool'''
    log.info("Connected to Stratum pool at %s:%d" % f.main_host)
    #reactor.callLater(30, f.client.transport.loseConnection)
    
    # Hook to on_connect again
    f.on_connect.addCallback(on_connect)
    
    # Get first job and user_id
    initial_job = (yield f.rpc('login', {"login":settings.CUSTOM_USER, "pass":settings.CUSTOM_PASSWORD, "agent":"proxy"}))

    reactor.callLater(300, ping, f, initial_job['id'])

    defer.returnValue(f)
     
def on_disconnect(f):
    '''Callback when proxy get disconnected from the pool'''
    log.info("Disconnected from Stratum pool at %s:%d" % f.main_host)
    f.on_disconnect.addCallback(on_disconnect)
    
    stratum_listener.MiningSubscription.disconnect_all()
    
    # Prepare to failover, currently works very bad
    #if f.main_host==(settings.POOL_HOST, settings.POOL_PORT):
    #    main()
    #else:
    #    f.is_reconnecting = False
    #return f

@defer.inlineCallbacks
def main():
    reactor.disconnectAll()
    failover = False
    if settings.POOL_FAILOVER_ENABLE:
        failover = settings.failover_pool
        settings.failover_pool = not settings.failover_pool

    pool_host = settings.POOL_HOST
    pool_port = settings.POOL_PORT
    if failover and settings.POOL_FAILOVER_ENABLE:
        pool_host = settings.POOL_HOST_FAILOVER
        pool_port = settings.POOL_PORT_FAILOVER

    log.warning("Monero Stratum proxy version: %s" % version.VERSION)
    log.warning("Trying to connect to Stratum pool at %s:%d" % (pool_host, pool_port))
        
    # Connect to Stratum pool, main monitoring connection
    f = SocketTransportClientFactory(pool_host, pool_port,
                debug=settings.DEBUG, proxy=None,
                event_handler=client_service.ClientMiningService)

    job_registry = jobs.JobRegistry(f)
    client_service.ClientMiningService.job_registry = job_registry
    client_service.ClientMiningService.reset_timeout()
    
    f.on_connect.addCallback(on_connect)
    f.on_disconnect.addCallback(on_disconnect)
    # Cleanup properly on shutdown
    reactor.addSystemEventTrigger('before', 'shutdown', on_shutdown, f)

    # Block until proxy connect to the pool
    try:
        yield f.on_connect
    except TransportException:
        log.warning("First pool server must be online first time to start failover")
        return
    
    # Setup stratum listener
    stratum_listener.StratumProxyService._set_upstream_factory(f)
    stratum_listener.StratumProxyService._set_custom_user(settings.CUSTOM_USER, settings.CUSTOM_PASSWORD, settings.ENABLE_WORKER_ID, settings.WORKER_ID_FROM_IP)
    reactor.listenTCP(settings.STRATUM_PORT, SocketTransportFactory(debug=settings.DEBUG, event_handler=ServiceEventHandler), interface=settings.STRATUM_HOST)
    
    # Setup multicast responder
    reactor.listenMulticast(3333, multicast_responder.MulticastResponder((pool_host, pool_port), settings.STRATUM_PORT), listenMultiple=True)

    log.warning("-----------------------------------------------------------------------")
    if settings.STRATUM_HOST == '0.0.0.0':
        log.warning("PROXY IS LISTENING ON ALL IPs ON PORT %d (stratum)" % settings.STRATUM_PORT)
    else:
        log.warning("LISTENING FOR MINERS ON stratum+tcp://%s:%d (stratum)" % \
                 (settings.STRATUM_HOST, settings.STRATUM_PORT))
    log.warning("-----------------------------------------------------------------------")

if __name__ == '__main__':
    fp = file("xmr-proxy.pid", 'w')
    fp.write(str(os.getpid()))
    fp.close()
    settings.failover_pool = False
    main()
    reactor.run()
