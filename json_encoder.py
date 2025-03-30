import datetime
from json import JSONEncoder

# Custom JSON encoder to handle datetime, date and time objects
class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(o, datetime.date):
            return o.strftime('%Y-%m-%d')
        elif isinstance(o, datetime.time):
            return o.strftime('%H:%M:%S')
        return super().default(o)