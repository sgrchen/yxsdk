import os
import sys
import time
import json
import uuid


def datetime_str(timestamp = None):
    if timestamp is None:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))

def log_debug(appliaction, msg):
    dt_str = datetime_str(None)
    print(f'[{dt_str}] {appliaction}: {msg}')
    sys.stdout.flush()

def uuid_generate():
    return str(uuid.uuid4().hex.upper())

def json_dumps(data, **kwargs):
    return json.dumps(data, ensure_ascii=False, **kwargs)


