import time
from datetime import datetime

def get_ISO_time():
    return datetime.fromtimestamp(time.time()).isoformat(timespec='milliseconds') + 'Z'