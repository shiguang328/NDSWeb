from datetime import datetime

def datetime_to_timestamp(time):
    if not time:
        return None
    if not isinstance(time, datetime):
        raise TypeError('Only accept datetime value.')
    return int(time.timestamp())