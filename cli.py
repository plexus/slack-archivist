"""Archivist CLI

Usage:
  cli.py list
  cli.py invite <bot_name>
  cli.py (-h | --help)
  cli.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""

import json

from docopt import docopt

import yaml

from slackclient import SlackClient

if __name__ == "__main__":
    arguments = docopt(__doc__, version='Slack Archivist v0.1')
    config = yaml.load(file('rtmbot.conf', 'r'))
    sc = SlackClient(config['SLACK_TOKEN'])
    human = SlackClient(config['HUMAN_SLACK_TOKEN'])

    if arguments['list']:
        print ', '.join([c['name'] for c in json.loads(sc.api_call('channels.list'))['channels']])

    elif arguments['invite']:
        channels = json.loads(sc.api_call('channels.list'))['channels']
        bot_name = arguments['<bot_name>']
        members = json.loads(sc.api_call('users.list'))['members']
        bot_id = None
        for member in members:
            if member['name'] == bot_name:
                bot_id = member['id']
                break
        if bot_id is None:
            raise Exception('Bot %s is not found.' % bot_name)
        for channel in channels:
            print '>>>', channel['name']
            print human.api_call('channels.invite', channel=channel['id'], user=bot_id)


