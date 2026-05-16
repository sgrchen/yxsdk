import redis
import json

class RedisClient:
    def __init__(self, host, port, db):
        self.redisClient = redis.StrictRedis(host=host, port=port, db=db, decode_responses=True)
    
    def selectdb(self, db):
        self.redisClient.select(db)

    def set(self, key, value):
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        self.redisClient.set(key, value)

    def get(self, key):
        value = self.redisClient.get(key)
        if value is not None:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return value

    def exists(self, key):
        return self.redisClient.exists(key)

    def setex(self, key, value, seconds):
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        self.redisClient.setex(key, value, seconds)
    
    def delete(self, key):
        self.redisClient.delete(key)
    
    def keys(self, pattern):
        return self.redisClient.keys(pattern)

    def llen(self, key):
        return self.redisClient.llen(key)
    
    def rpush(self, key, value):
        if not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        self.redisClient.rpush(key, value)

    def lrange(self, key, start, end):
        values = self.redisClient.lrange(key, start, end)
        return [json.loads(value) if isinstance(value, str) else value for value in values]
    
    def lpop(self, key):
        value = self.redisClient.lpop(key)
        if value is not None:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        return value
    
    def xgroup_create(self, key, group):
        self.redisClient.xgroup_create(key, group, id='0', mkstream=True)

    def xadd(self, key, value):
        self.redisClient.xadd(key, value)

    def xreadgroup(self, stream, group, consumer, block=0):
        return self.redisClient.xreadgroup(group, consumer, {stream: '>'}, block=block)

    def xack(self, stream, group, id):
        self.redisClient.xack(stream, group, id)

    def incr(self, key):
        return self.redisClient.incr(key)

    def expire(self, key, seconds):
        self.redisClient.expire(key, seconds)

    
    
    