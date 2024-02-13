import redis

class CacheAdapter:
    """
    A class which serves as an adapter for Cache
    """
    def __init__(self, redis_location):
        """
        Constructor
        """
        self.prefix = "PUBSUB:"
        self.redis_client = redis.from_url(redis_location)

    def get(self, key):
        """
        Returns the set value
        """
        redis_client = self.get_redis_client()
        return redis_client.get(f"{self.prefix}{key}")

    def set(self, key, value, timeout=None, **kwargs):
        """
        sets the value in cache
        """
        redis_client = self.get_redis_client()
        redis_client.set(f"{self.prefix}{key}", value, timeout, **kwargs)

    def delete(self, key):
        """
        Deletes a specific key from cache
        """
        redis.delete(f"{self.prefix}{key}")

    def is_cache_available(self):
        """
        returns a boolean checking if the cache
        is available or not
        """

        try:
            self.get(None)
        except (redis.exceptions.ConnectionError,
                redis.exceptions.BusyLoadingError):
            return False

        return True