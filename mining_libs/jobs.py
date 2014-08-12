from twisted.internet import defer

import stratum.logger
log = stratum.logger.get_logger('proxy')

class Job(object):
    def __init__(self):
        self.job_id = ''
        self.blob = ''
        self.target = ''

    @classmethod
    def build_from_pool(cls, job_id, blob, target):
        '''Build job object from Stratum server broadcast'''
        job = Job()
        job.job_id = job_id
        job.blob = blob
        job.target = target
        return job

class JobRegistry(object):   
    def __init__(self, f):
        self.f = f
        self.jobs = []
        # Hook for LP broadcasts
        self.on_block = defer.Deferred()

    def add_job(self, template, clean_jobs): #????clean
        if clean_jobs:
            # Pool asked us to stop submitting shares from previous jobs
            self.jobs = []
            
        self.jobs.append(template)

        if clean_jobs:
            # Force miners to reload jobs
            on_block = self.on_block
            self.on_block = defer.Deferred()
            on_block.callback(True)
