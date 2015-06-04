"""Archivist CLI

Usage:
  cli.py list
  cli.py invite <human_name> <bot_name>
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
        members = json.loads(sc.api_call('users.list'))['members']

        bot_name = arguments['<bot_name>']
        human_name = arguments['<human_name>']
        bot_id = None
        human_id = None

        for member in members:
            if member['name'] == bot_name:
                bot_id = member['id']
            elif member['name'] == human_name:
                human_id = member['id']
            if bot_id and human_id:
                break

        if bot_id is None:
            raise Exception('Bot %s is not found.' % bot_name)
        if human_id is None:
            raise Exception('Human %s is not found.' % human_name)

        for channel in channels:
            print '>>>', channel['name']
            chan_id = channel['id']
            is_human_in_chan = False
            for member in json.loads(sc.api_call('channels.info', channel=chan_id))['channel']['members']:
                if member == human_id:
                    is_human_in_chan = True
                    break

            if not is_human_in_chan:
                human.api_call('channels.join', name=channel['name'])

            print human.api_call('channels.invite', channel=chan_id, user=bot_id)

            if not is_human_in_chan:
                human.api_call('channels.leave', channel=chan_id)


