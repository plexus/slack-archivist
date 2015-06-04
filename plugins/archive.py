from datetime import date
from json import dumps
import codecs


def process_message(data):
    with codecs.open(date.today().strftime('logs/%Y-%m-%d.txt'), 'ab', 'utf-8') as f:
        f.write(dumps(data))
        f.write("\n")
