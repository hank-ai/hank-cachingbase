from HANK_Caching.base import CachingBase
from HANK_Caching.decorators import conditional_lru_cache, redis_lru_cache
from HANK_Caching.transforms import dos_transform_YYYYMM, zipcode_4
import time, datetime, random    

class TestCachingBase(CachingBase):
    redis_client = CachingBase.create_redis_client()
    
    def __init__(self, redis_client=None, use_redis=True, caches_enabled=True, quiet=True):                
        self.enabled = caches_enabled
        # if redis_client is None and use_redis:
        #     redis_client = CachingBase.create_redis_client()
        # self.redis_client = redis_client
        # self.test_func = redis_lru_cache(self.redis_client, enabled=self.enabled, quiet=True, tags=['keyphrase'], arg_transforms={'dos': dos_transform_YYYYMM, 'zipcode': zipcode_4})(self.test_func)
        if use_redis and redis_client is not None:
            decorator_dict = {'decorator': redis_lru_cache, 'redis_client': self.redis_client}
        else:
            decorator_dict = {'decorator': conditional_lru_cache}
        self.func_cache_map = {
            #self.test_func: {'decorator': conditional_lru_cache, 'enabled':self.enabled, 'quiet':True, 'tags':['keyphrase'], 'arg_transforms':{'dos': dos_transform_YYYYMM, 'zipcode': zipcode_4}}
            "test_func": {**decorator_dict, 
                          'enabled':self.enabled, 
                          'quiet':quiet, 
                          'tags':['keyphrase'], 
                          'cache_id': 'test_func',
                          'arg_transforms':
                              {'dos': dos_transform_YYYYMM, 
                               'zipcode': zipcode_4, 
                               'quiet': lambda x: True
                               }
                            }
            }
        # self.test_func = conditional_lru_cache(enabled=self.enabled, quiet=True, tags=['keyphrase'], arg_transforms={'dos': dos_transform_YYYYMM, 'zipcode': zipcode_4})(self.test_func)
        if not quiet: print("Initializing TestCachingBase ...")
        super().__init__(caches_enabled=caches_enabled, quiet=quiet)
        #self.initialize_caching(func_cache_map, decorator=conditional_lru_cache)
        

    def test_func(self, a, b, dos=None, quiet=None, **kwargs):
        quiet = quiet if quiet is not None else self.quiet
        if not quiet: print("  -> **NOT CACHED. EXECUTING TEST_FUNC NOW**")
        t = time.time()
        for i in range(2):
            time.sleep(0.1)
        return list(a.keys()) + b, t
    
    def test_cache_on(self, iters=6, tags=[]):
        self.enable_caching(tags=tags)
        self.test(iters=iters)
    def test_cache_off(self, iters=6, tags=[]):
        self.disable_caches_and_force_gc(tags=tags)
        self.test(iters=iters)
    def test(self, iters=6, quiet=False):
        a = {1: 2, 3: 4}
        b = [1, 2, 3]
        dos = datetime.datetime.now()
        zipcodes = [29220, 29221, 29222, 29223, 29224, 29225, 29226, 29227, 29228, 29229, 29230]
        zipcodes = [29220, 29230, 29240, 29250, 29260, 29270, 29280, 29290, 29300, 29310, 29320]
        st = time.time()
        tt = 0
        for i in range(iters):
            if i < len(zipcodes):
                zipcode = zipcodes[i]
            else:
                zipcode = random.choice(zipcodes)
            self.test_func(a, b, dos=dos, zipcode=zipcode, quiet=True)
            sti = time.time()
            self.test_func(a, b, dos=dos, zipcode=zipcode)
            eti = time.time()
            tt += eti - sti
            # print(f"Iter {i}. Time taken: {time.time() - sti:.6f}")
        et = time.time()
        
        if not quiet: print(f"Total time taken with test_func.enabled={self.test_func.enabled}: {et - st:.6f} seconds. ({(et - st)/iters:.6f} per iter)")
        if not quiet: print(f" -> time spent on second calls: {tt:.6f} seconds. ({tt/iters:.6f} per iter)")
        
if __name__ == "__main__":
    import time, datetime, random
    
    tc1 = TestCachingBase(quiet=False)
    tc2 = TestCachingBase(quiet=False)
    print(tc1)
    print(tc2)
    print("testing caching base tc1 with cache on ...")
    tc1.test_cache_on(iters=10)
    print("testing caching base tc2 with cache on ...")
    tc2.test_cache_on(iters=10)
    # print("testing caching base tc1 with cache off ...")
    # tc1.test_cache_off(iters=10, tags=['keyphrase'])
    # print("testing caching base tc2 with cache off ...")
    # tc2.test_cache_off(iters=10, tags=['keyphrase'])
    
    #%%
    tc2.disable_caching()
    print(tc1)
    print(tc2)

    # %%
    tc1._cached_methods
    # %%

    tc2._cached_methods
    # %%
    id(tc1.test_func)

    # %%
    id(tc2.test_func)
    #%%
