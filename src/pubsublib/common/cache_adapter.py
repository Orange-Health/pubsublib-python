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
        return self.redis_client.get(f"{self.prefix}{key}")

    def set(self, key, value, timeout=None, **kwargs):
        """
        sets the value in cache
        """
        self.redis_client.set(f"{self.prefix}{key}", value, timeout, **kwargs)

    def delete(self, key):
        """
        Deletes a specific key from cache
        """
        self.redis_client.delete(f"{self.prefix}{key}")

    def is_cache_available(self):
        """
        returns a boolean checking if the cache
        is available or not
        """

        try:
            self.redis_client.get(None)
        except (redis.exceptions.ConnectionError,
                redis.exceptions.BusyLoadingError):
            return False

        return True