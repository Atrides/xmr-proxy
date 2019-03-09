from twisted.internet import reactor

from stratum.event_handler import GenericEventHandler
from jobs import Job
import version as _version

import stratum_listener

import stratum.logger
log = stratum.logger.get_logger('proxy')

class ClientMiningService(GenericEventHandler):
    job_registry = None # Reference to JobRegistry instance
    timeout = None # Reference to IReactorTime object
    
    @classmethod
    def reset_timeout(cls):
        if cls.timeout != None:
            if not cls.timeout.called:
                cls.timeout.cancel()
            cls.timeout = None
            
        cls.timeout = reactor.callLater(960, cls.on_timeout)

    @classmethod
    def on_timeout(cls):
        '''
            Try to reconnect to the pool after 16 minutes of no activity on the connection.
            It will also drop all Stratum connections to sub-miners
            to indicate connection issues.
        '''
        log.error("Connection to upstream pool timed out")
        cls.reset_timeout()
        cls.job_registry.f.reconnect()
                
    def handle_event(self, method, params, connection_ref):
        '''Handle RPC calls and notifications from the pool'''
        # Yay, we received something from the pool,
        # let's restart the timeout.
        self.reset_timeout()
        
        if method == 'job':
            '''Proxy just received information about new mining job'''
            
            (blob, job_id, target, user_id, height) = params["blob"],params["job_id"],params["target"],params["id"],params["height"]
        
            # Broadcast to Stratum client
            stratum_listener.MiningSubscription.on_template(job_id, blob, target, user_id, height)
            
            # Broadcast to getwork clients
            job = Job.build_from_pool(job_id, blob, target, height)
            log.info("New job %s for %s on height %s" % (job_id, user_id, height))

            self.job_registry.add_job(job, True)
            
        else:
            '''Pool just asked us for something which we don't support...'''
            log.error("Unhandled method %s with params %s" % (method, params))

