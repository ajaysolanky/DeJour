import os, sys
import tiktoken
import json
import pytz
from datetime import datetime
from dateutil import parser

LOCAL_DB_FOLDER = 'local_db_files'

class HiddenPrints:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

class TokenCountCalculator:
    ENCODING_TYPE = "gpt2"  # encoding for text-davinci-003
    
    def __init__(self):
        self.encoding = tiktoken.get_encoding(self.ENCODING_TYPE)
    
    def get_num_tokens(self, text):
        return len(self.encoding.encode(text))

class GhettoDiskCache:
    def __init__(self):
        self.cache_dir = "./disk_cache_dir/"
    
    def get_key(self, *args):
        return ','.join(args)

    def get_cache_path(self, key):
        return self.cache_dir + f"{key}.json"

    def get_cache(self, key):
        if not os.path.isfile(self.get_cache_path(key)):
            return {}
        else:
            with open(self.get_cache_path(key), 'rb') as f:
                cache = json.load(f)
            return cache

    def check_cache(self, *args):
        key = self.get_key(*args)
        cache = self.get_cache(key)
        if key in cache:
            return cache[key]

    def save_to_cache(self, value, *args):
        key = self.get_key(*args)
        cache = self.get_cache(key)
        cache[key] = value
        cache_path = self.get_cache_path(key)
        try:
            os.makedirs(os.path.dirname(cache_path))
        except:
            pass
        with open(self.get_cache_path(key), 'w+') as f:
            json.dump(cache, f)

def use_ghetto_disk_cache(func):
    def wrapper(*args):
        gdc = GhettoDiskCache()
        cache_val = gdc.check_cache(*args)
        if cache_val:
            return cache_val
        result = func(*args)
        gdc.save_to_cache(result, *args)
        return result
    return wrapper


def get_structured_time_string_from_dt(dt):
    return dt.strftime('%a, %b %d, %Y %I:%M%p')

def get_current_structured_time_string():
    et_dt = pytz.utc.localize(datetime.utcnow()).astimezone(pytz.timezone('America/New_York'))
    return get_structured_time_string_from_dt(et_dt)

def unstructured_time_string_to_structured(unstructured_time_string):
    return get_structured_time_string_from_dt(parser.parse(unstructured_time_string))
