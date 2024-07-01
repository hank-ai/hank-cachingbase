from HANK_Caching.test import TestCachingBase
from HANK_Caching.base import CachingBase
import unittest
import datetime

class TestCachingBaseMethods(unittest.TestCase):
    def setUp(self):
        quiet = True
        # Setup instances with in-memory and Redis caching
        self.redis_client = CachingBase.create_redis_client()
        self.memory_instance = TestCachingBase(caches_enabled=True, use_redis=False, quiet=quiet)
        self.redis_instance = TestCachingBase(caches_enabled=True, use_redis=True, redis_client=self.redis_client, quiet=quiet)

    def test_memory_caching(self):
        # Test in-memory caching
        self.memory_instance.enable_caching()
        print("Testing memory caching, cache_enabled=True")
        result1 = self.memory_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        result2 = self.memory_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        self.assertEqual(result1, result2, "Shit. Failure. Memory caching should return the same result for the same inputs")
        print(" -> Great. Memory caching test passed")

    def test_redis_caching(self):
        # Test Redis caching
        self.redis_instance.enable_caching()
        print(f"Testing Redis caching, cache_enabled=True")
        result1 = self.redis_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        result2 = self.redis_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        self.assertEqual(result1, result2, "Shit. Failure. Redis caching should return the same result for the same inputs")
        print(" -> Great. Redis caching test passed")

    def test_disable_caching(self):
        # Test disabling caching in both setups
        self.memory_instance.disable_caching()
        self.memory_instance.clear_caches()
        print(f"Testing memory caching, cache_enabled=False")
        result1 = self.memory_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        result2 = self.memory_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        self.assertNotEqual(result1, result2, "Shit. Failure. Memory caching should be disabled and results should differ")
        print(f" -> Great. Memory caching test passed")

        print(f"Testing Redis caching, cache_enabled=False")
        self.redis_instance.disable_caching()
        self.redis_instance.clear_caches()
        result3 = self.redis_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        result4 = self.redis_instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
        self.assertNotEqual(result3, result4, "Shit. Failure. Redis caching should be disabled and results should differ")
        print(f" -> Great. Redis caching test passed")

if __name__ == '__main__':
    unittest.main()