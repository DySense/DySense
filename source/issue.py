
import time

class Issue(object):
    
    min_expire_increment = 1 # second
    
    def __init__(self, **kargs):
        self._id = kargs['id']
        self._sub_id = kargs['sub_id']
        self._issue_type = kargs['type']
        self._reason = kargs.get('reason', '')
        self._level = kargs.get('level', 'error')
    
        self.start_time = kargs.get('start_time', time.time())
        self.expiration_time = kargs.get('expiration_time', 0)
        
        # Right now these are only used by presenter.  Should consider storing these outside of class.
        self.acked = False
        self.resolved = False
    
    @property
    def public_info(self):
        return {'id': self.id,
                'sub_id': self.sub_id,
                'type': self.issue_type,
                'reason': self._reason,
                'level': self._level,
                'start_time': self.start_time,
                'end_time': self.expiration_time,
                }
        
    @property
    def id(self):
        return self._id
    
    @property
    def sub_id(self):
        return self._sub_id
    
    @property
    def issue_type(self):
        return self._issue_type
        
    @property
    def reason(self):
        return self._reason
        
    @property
    def level(self):
        return self._level
        
    @reason.setter
    def reason(self, new_value):
        self._reason = new_value
        
    @level.setter
    def level(self, new_value):
        self._level = new_value
        
    @property
    def expired(self):
        return (self.expiration_time > 0) and (time.time() >= self.expiration_time)
        
    def matches(self, info):
        return self._id == info['id'] and self._sub_id == info['sub_id'] and self._issue_type == info['type']
    
    def renew(self):
        self.expiration_time = 0
    
    def expire(self, force_expire=False):
        if self.expiration_time > 0:
            return # already set to expire
        if force_expire:
            self.expiration_time = time.time()
        else:
            self.expiration_time = time.time() + Issue.min_expire_increment
        
    