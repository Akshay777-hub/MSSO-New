import datetime

def convert_datetime_to_strings(obj):
    """
    Convert all datetime, date and time objects in the given object (dict, list, etc.)
    to their string representations recursively.
    
    Args:
        obj: The object to process (can be dict, list, or simple value)
        
    Returns:
        The object with all datetime objects converted to strings
    """
    if isinstance(obj, dict):
        return {k: convert_datetime_to_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_strings(item) for item in obj]
    elif isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    elif isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')
    elif isinstance(obj, datetime.time):
        return obj.strftime('%H:%M:%S')
    else:
        return obj