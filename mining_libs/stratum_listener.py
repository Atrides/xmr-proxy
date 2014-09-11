import time
import binascii
import struct
import re

from twisted.internet import defer

from stratum.services import GenericService
from stratum.pubsub import Pubsub, Subscription
from stratum.custom_exceptions import ServiceException, RemoteServiceException
from stratum.socket_transport import SocketTransportFactory, SocketTransportClientFactory
from mining_libs import client_service
from mining_libs.jobs import Job

import stratum.logger
log = stratum.logger.get_logger('proxy')

def var_int(i):
    if i <= 0xff:
        return struct.pack('>B', i)
    elif i <= 0xffff:
        return struct.pack('>H', i)
    raise Exception("number is too big")

class UpstreamServiceException(ServiceException):
    code = -2

class SubmitException(ServiceException):
    code = -2

class MiningSubscription(Subscription):
    '''This subscription object implements
    logic for broadcasting new jobs to the clients.'''
    
    event = 'job'
    subscribers = {}
    
    @classmethod
    def disconnect_all(cls):
        StratumProxyService.registered_tails = []
        for subs in cls.subscribers:
            try:
                cls.subscribers[subs].connection_ref().transport.abortConnection()
            except Exception:
                pass
        #for subs in Pubsub.iterate_subscribers(cls.event):
        #    if subs.connection_ref().transport != None:
        #        subs.connection_ref().transport.loseConnection()

    @classmethod
    def add_user_id(cls, subsc, user_id):
        cls.subscribers[user_id] = subsc
        
    @classmethod
    def on_template(cls, job_id, blob, target, user_id):
        '''Push new job to subscribed clients'''
        #cls.last_broadcast = (job_id, blob, target)
        #if user_id:
        #    cls.user_id = user_id
        if cls.subscribers.has_key(user_id):
            subscr = cls.subscribers[user_id]
            subscr.emit_single({'job_id':job_id, 'blob':blob, 'target':target})
        
    def _finish_after_subscribe(self, result):
        '''Send new job to newly subscribed client'''
        #try:
        #    (job_id, blob, target) = self.last_broadcast
        #except Exception:
        #    log.error("Template not ready yet")
        #    return result
        
        #self.emit_single({'job_id':job_id, 'blob':blob, 'target':target})
        return result
             
    def after_subscribe(self, *args):
        '''This will send new job to the client *after* he receive subscription details.
        on_finish callback solve the issue that job is broadcasted *during*
        the subscription request and client receive messages in wrong order.'''
        #self.add_user_id(self, user_id)
        self.connection_ref().on_finish.addCallback(self._finish_after_subscribe)
        
class StratumProxyService(GenericService):
    service_type = 'mining'
    service_vendor = 'mining_proxy'
    is_default = True
    
    _f = None # Factory of upstream Stratum connection
    custom_user = None
    custom_password = None
    enable_worker_id = False
    worker_id_from_ip = False
    tail_iterator = 0
    registered_tails = []
    
    @classmethod
    def _set_upstream_factory(cls, f):
        cls._f = f

    @classmethod
    def _set_custom_user(cls, custom_user, custom_password, enable_worker_id, worker_id_from_ip):
        cls.custom_user = custom_user
        cls.custom_password = custom_password
        cls.enable_worker_id = enable_worker_id
        cls.worker_id_from_ip = worker_id_from_ip

    @classmethod
    def _is_in_tail(cls, tail):
        if tail in cls.registered_tails:
            return True
        return False

    @classmethod
    def _get_unused_tail(cls):
        '''Currently adds up to two bytes to extranonce1,
        limiting proxy for up to 65535 connected clients.'''
        
        for _ in range(0, 0xffff):  # 0-65535
            cls.tail_iterator += 1
            cls.tail_iterator %= 0xffff

            # Zero extranonce is reserved for getwork connections
            if cls.tail_iterator == 0:
                cls.tail_iterator += 1

            # var_int throws an exception when input is >= 0xffff
            tail = var_int(cls.tail_iterator)

            if tail not in cls.registered_tails:
                cls.registered_tails.append(tail)
                return binascii.hexlify(tail)
            
        raise Exception("Extranonce slots are full, please disconnect some miners!")
    
    def _drop_tail(self, result, tail):
        tail = binascii.unhexlify(tail)
        if tail in self.registered_tails:
            self.registered_tails.remove(tail)
        else:
            log.error("Given extranonce is not registered1")
        return result
    
    @defer.inlineCallbacks
    def login(self, params, *args):
        if self._f.client == None or not self._f.client.connected:
            yield self._f.on_connect

        if self._f.client == None or not self._f.client.connected:
            raise UpstreamServiceException("Upstream not connected")

        tail = self._get_unused_tail()
        
        session = self.connection_ref().get_session()
        session['tail'] = tail

        custom_user = self.custom_user
        if self.enable_worker_id and params.has_key("login"):
            if self.worker_id_from_ip:
                ip_login = self.connection_ref()._get_ip()
                ip_temp = ip_login.split('.')
                ip_int = int(ip_temp[0])*16777216 + int(ip_temp[1])*65536 + int(ip_temp[2])*256 + int(ip_temp[3])
                custom_user = "%s.%s" % (custom_user, ip_int)
            else:
                params_login = re.sub(r'[^\d]', '', params["login"])
                if params_login and int(params_login)>0:
                    custom_user = "%s.%s" % (custom_user, params_login)

        first_job = (yield self._f.rpc('login', {"login":custom_user, "pass":self.custom_password}))

        try:
            self.connection_ref().on_disconnect.addCallback(self._drop_tail, tail)
        except Exception:
            pass
        subs = Pubsub.subscribe(self.connection_ref(), MiningSubscription())[0]

        MiningSubscription.add_user_id(subs[2], first_job['id'])

        defer.returnValue(first_job)
            
    @defer.inlineCallbacks
    def submit(self, params, *args):
        if self._f.client == None or not self._f.client.connected:
            self.connection_ref().transport.abortConnection()
            raise SubmitException("Upstream not connected")

        session = self.connection_ref().get_session()
        tail = session.get('tail')
        if tail == None:
            raise SubmitException("Connection is not subscribed")

        ip = self.connection_ref()._get_ip()
        start = time.time()
        
        try:
            result = (yield self._f.rpc('submit', params))
        except RemoteServiceException as exc:
            response_time = (time.time() - start) * 1000
            log.info("[%dms] Share from '%s' REJECTED: %s" % (response_time, ip, str(exc)))
            raise SubmitException(*exc.args)

        response_time = (time.time() - start) * 1000
        log.info("[%dms] Share from '%s' accepted" % (response_time, ip))
        defer.returnValue(result)

    @defer.inlineCallbacks
    def get_job(self, params, *args):
        if self._f.client == None or not self._f.client.connected:
            raise SubmitException("Upstream not connected")

        session = self.connection_ref().get_session()
        tail = session.get('tail')
        if tail == None:
            raise SubmitException("Connection is not subscribed")

        ip = self.connection_ref()._get_ip()
        start = time.time()

        try:
            result = (yield self._f.rpc('get_job', params))
        except RemoteServiceException as exc:
            response_time = (time.time() - start) * 1000
            log.info("[%dms] GetJob to '%s' ERROR: %s" % (response_time, ip, str(exc)))
            raise SubmitException(*exc.args)

        response_time = (time.time() - start) * 1000
        log.info("[%dms] send GetJob to '%s'" % (response_time, ip))
        defer.returnValue(result)
