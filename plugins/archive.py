from datetime import date
from json import dumps

def process_message(data):
    with open(date.today().strftime('logs/%Y-%m-%d.txt'), 'ab') as f:
        f.write(dumps(data))
        f.write("\n")
