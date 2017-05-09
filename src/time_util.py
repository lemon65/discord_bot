import pytz

def as_helsinki(time):
    """Interpret a time without timezone as Europe/Helsinki without adjusting time"""
    return pytz.timezone('Europe/Helsinki').localize(time)

def to_helsinki(time):
    """Translate existing time with timezone to Europe/Helsinki"""
    return time.astimezone(tz=pytz.timezone('Europe/Helsinki'))

def as_utc(time):
    """Interpret a time without timezone as UTC without adjusting time"""
    return pytz.utc.localize(time)

def to_utc(time):
    """Translate existing time with timezone to UTC"""
    return time.astimezone(tz=pytz.utc)
