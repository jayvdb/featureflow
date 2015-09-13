import lmdb
from data import Database, KeyBuilder
from dependency_injection import dependency
from io import BytesIO

class WriteStream(object):
    
    def __init__(self, key, env, db_getter = None):
        self.key = key
        self.db_getter = db_getter
        self.env = env
        self.buf = BytesIO()

    def __enter__(self):
        return self

    def __exit__(self, t, value, traceback):
        self.close()
    
    def close(self):
        _id, db = self.db_getter(self.key)
        self.buf.seek(0)
        with self.env.begin(write = True) as txn:
            txn.put(_id, self.buf.read(), db = db)
        
    def write(self, data):
        self.buf.write(data)

class ReadStream(object):
    
    def __init__(self, buf):
        self.view = memoryview(buf)
        self.pos = 0
    
    def __enter__(self):
        return self
    
    def __exit__(self, t, value, traceback):
        pass
    
    def seek(self, pos, whence = 0):
        # BUG: What about whence argument
        self.pos = pos
    
    def read(self, nbytes = None):
        if nbytes is None:
            nbytes = len(self.view)
        v = self.view[self.pos : self.pos + nbytes]
        self.pos += nbytes
        # KLUDGE: This negates most of the benefit of returning pointers
        # directly to the memory-mapped data, because it creates a copy.
        # Is there any way to treat this as a string/bytes without copying
        # the data?
        return v.tobytes()

class LmdbDatabase(Database):
    
    def __init__(self, path, map_size = 1000000000):
        super(Database, self).__init__()
        self.path = path
        self.env = lmdb.open(\
             self.path, 
             max_dbs = 10, 
             map_size = map_size,
             writemap = True,
             map_async = True,
             metasync = False)
        self.dbs = dict()
    
    def _get_db(self, key):
        _id, feature = self.key_builder.decompose(key)
        try:
            return _id, self.dbs[feature]
        except KeyError:
            db = self.env.open_db(feature)
            self.dbs[feature] = db
            return _id, db
    
    def _get_read_db(self, key):
        _id, feature = self.key_builder.decompose(key)
        try:
            return _id, self.dbs[feature]
        except KeyError:
            raise KeyError(key)
    
    @property
    @dependency(KeyBuilder)
    def key_builder(self): pass
    
    def write_stream(self, key, content_type):
        return WriteStream(key, self.env, self._get_db)
    
    def read_stream(self, key):
        _id, db = self._get_read_db(key)
        with self.env.begin(buffers = True) as txn:
            buf = txn.get(_id, db = db)
        
        if buf is None:
            raise KeyError(key)
        
        # POSSIBLE BUG:  Is it safe to keep the buffer around after the
        # transaction is complete?
        return ReadStream(buf)
    
    def iter_ids(self):
        db = self.dbs.values()[0]
        with self.env.begin() as txn:
            cursor = txn.cursor(db)
            for _id in cursor.iternext(keys = True, values = False):
                yield _id

    def __contains__(self, key):
        try:
            _id, db = self._get_read_db(key)
        except KeyError:
            return False
        with self.env.begin(buffers = True) as txn:
            buf = txn.get(_id, db = db)
        return buf is not None