# HANK Caching Module

## Overview
The HANK Caching module provides a flexible way to add caching capabilities to class methods using decorators. This package supports a variety of caching configurations including Redis-based and in-memory caching with options for key transformations and control over cache behavior.

## Features
- Decorate class methods for caching with Redis or in-memory caches.
- Configure caching on a per-method basis using a simple mapping.
- Easily enable or disable caching, and clear caches when necessary.

## Getting Started

### Installation
To install the HANK Caching module, run:

```bash
pip install HANK_Caching
```

or while it is in pypi test:

```bash
pip install -i https://test.pypi.org/simple/ HANK-Caching
```
### OPTIONAL: If using redis, set environment variables
```
REDIS_HOST = localhost
REDIS_PORT = 6379
REDIS_DB = 0
```

<br>

<br>

---

### Usage
To use the caching capabilities in your project, you can import the CachingBase class and the conditional_lru_cache decorator:
```python
from HANK_Caching.base import CachingBase
from HANK_Caching.decorators import conditional_lru_cache, redis_lru_cache
from HANK_Caching.transforms import dos_transform_YYYYMM, zipcode_4
```

### For shared-caching across all usage of a particular function, apply with a decorator like this: 
```
@conditional_lru_cache(maxsize=25000, enabled=True, tags=['keyphrase'])
def test_func(self, a, b, dos=None, quiet=None, **kwargs):
    quiet = quiet if quiet is not None else self.quiet
    if not quiet: print("  -> **NOT CACHED. EXECUTING TEST_FUNC NOW**")
    t = time.time()
    for i in range(2):
        time.sleep(0.1)
    return a + b, t
```

<br>

### IF YOU WANT CACHING THAT IS SPECIFIC TO EACH INSTANCE OF A CLASS ...
You can define your class methods and apply caching dynamically based on a configuration map. This approach allows you to easily manage caching properties directly within class initialization.

```python
#then look inside TestCachingBase for an example of how to decorate an instance function of a class with decorators.
#kinda like this:
class ClassIdLikeToHaveCachingOn(CachingBase):
    redis_client = CachingBase.create_redis_client()
    def __init__(self, cache_id=None, redis_client=None, use_redis=True, caches_enabled=True, quiet=True):                
        self.enabled = caches_enabled
        self.cache_id = cache_id if cache_id is not None else ""
        if use_redis and redis_client is not None:
            decorator_dict = {'decorator': redis_lru_cache, 'redis_client': self.redis_client}
        else:
            decorator_dict = {'decorator': conditional_lru_cache}
        self.func_cache_map = {
            "test_func": {**decorator_dict, 
                          'enabled':self.enabled, 
                          'quiet':quiet, 
                          'tags':['keyphrase'], #allows you to disable/enable specific groups of caches based upon tags
                          'cache_id': f'{cache_id}_test_func', #want to define a specific cache_id key? Different instances of the same class can then have different cache ids
                          'arg_transforms': #will be used to manipulate parameters of the function based upon value assigned
                              {'dos': dos_transform_YYYYMM, #ie convert the date of service to a YYYYMM format
                               'zipcode': zipcode_4, #ie only use the first 4 digits of the zip code
                               'quiet': lambda x: True #ie ignore quiet or not quiet 
                               }
                            }
            }

        super().__init__(caches_enabled=caches_enabled, quiet=quiet) #will initalize the methods defined in self.func_cache_map with decorations
        
    #NOTE: you don't apply the @redis_lru_cache or @conditional_lru_cache etc directly here. You MUST do it in self.func_cache_map to get the 
    # caches to be instance specific caches on the function
    def test_func(self, a, b, dos=None, quiet=None, **kwargs):
        quiet = quiet if quiet is not None else self.quiet
        if not quiet: print("  -> **NOT CACHED. EXECUTING TEST_FUNC NOW**")
        t = time.time()
        for i in range(2):
            time.sleep(0.1)
        return a + b, t


cachableclass = ClassIdLikeToHaveCachingOn(cache_id='1')
r = cachableclass.test_func(1,2, quiet=False)
# -> ** NOT CACHED. EXECUTING TEST_FUNC_NOW**
r
# 3, ...somerandomtimefloat...
r = cachableclass.test_func(1,2,quiet=False)
# nothing will be printed here
r
# 3, ...samerandomtimefloat...
cachableclass.disable_caching(clear_cache=True)
r = cachableclass.test_func(1,2,quiet=False)
# -> **NOT CACHED. EXECUTING TEST_FUNC NOW**
r
# 3, ...someDIFFERENTrandomtimefloat

#AND IMPORTANTLY
cachableclass2 = ClassIdLikeToHaveCachingOn(cache_id='2')
## this will NOT share the caches above since you set a different cache_id. 
# -> if you used the SAME cache_id then they WILL share the cache if you are using redis. will NOT share the cache if you aren't using redis

```

Another example of using the test class:

```python
from HANK_Caching.test import TestCachingBase
import datetime

# Initialize the class and use the cached methods
instance = TestCachingBase()
result = instance.test_func({'x': 1}, ['y'], dos=datetime.datetime.now())
# Turn off caching
```


## Unit Tests

```bash
conda activate yourenvironment
#make sure you are in the root dir where you cloned the repo
python -m unittest tests/test_cachingbase.py
#or
pytest
```

## Documentation

For more detailed information on configuration options and method usage, please refer to the complete documentation provided with the package.



### How to build and upload to pypi
pip install twine build
python -m build
twine upload --repository testpypi dist/*
