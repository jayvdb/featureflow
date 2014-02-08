import simplejson
from extractor import Extractor

class IdentityEncoder(Extractor):
    
    content_type = 'application/octet-stream'
    
    def __init__(self, needs = None):
        super(IdentityEncoder,self).__init__(needs = needs)
    
    def _update_cache(self,data,final_push,pusher):
        if data:
            self._cache = data
        else:
            self._cache = ''
    
    def _can_process(self,final_push):
        return self._cache is not None
    
    def _process(self,final_push):
        return self._cache

class JSONEncoder(Extractor):
    
    content_type = 'application/json'
    
    def __init__(self, needs = None):
        super(JSONEncoder,self).__init__(needs = needs)
        
    def _process(self,final_push):
        return simplejson.dumps(self._cache)

class ShittyNumpyEncoder(Extractor):
    
    content_type = 'application/octet-stream'
    
    def __init__(self, needs = None):
        super(ShittyNumpyEncoder,self).__init__(needs = needs)
    
    def _can_process(self,final_push):
        return self._cache.size
    
    def _process(self,final_push):
        return self._cache.tostring()  