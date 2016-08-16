#!/usr/bin/env python

"""Archivist CLI

Usage:
  cli.py list
  cli.py invite <human_name> <bot_name>
  cli.py export <output_dir>
  cli.py kick <human_name> <bot_name> <channel>
  cli.py (-h | --help)
  cli.py --version

Options:
  -h --help     Show this screen.
  --version     Show version.

"""

import os
import json
import shutil
from glob import glob
from collections import defaultdict, OrderedDict
from datetime import datetime
import codecs
import re
import string
import sys; 

from docopt import docopt
import pystache
import yaml
from slackclient import SlackClient

import hashlib, re
import markdown as markdown_lib

def gfm(text):
    """Processes Markdown according to GitHub Flavored Markdown spec."""
    extractions = {}

    def extract_pre_block(matchobj):
        match = matchobj.group(0)
        hashed_match = hashlib.md5(match.encode('utf-8')).hexdigest()
        extractions[hashed_match] = match
        result = "{gfm-extraction-%s}" % hashed_match
        return result

    def escape_underscore(matchobj):
        match = matchobj.group(0)

        if match.count('_') > 1:
            return re.sub('_', '\_', match)
        else:
            return match

    def newlines_to_brs(matchobj):
        match = matchobj.group(0)
        if re.search("\n{2}", match):
            return match
        else:
            match = match.strip()
            return match + "  \n"

    def insert_pre_block(matchobj):
        string = "\n\n" + extractions[matchobj.group(1)]
        return string

    text = re.sub("(?s)<pre>.*?<\/pre>", extract_pre_block, text)
    text = re.sub("(^(?! {4}|\t)\w+_\w+_\w[\w_]*)", escape_underscore, text)
    text = re.sub("(?m)^[\w\<][^\n]*\n+", newlines_to_brs, text)
    text = re.sub("\{gfm-extraction-([0-9a-f]{32})\}", insert_pre_block, text)

    return text

def markdown(text):
    """Processes GFM then converts it to HTML."""
    text = gfm(text)
    text = markdown_lib.markdown(text)
    return text


special_pat = re.compile(r"<(.*?)>")
quirk_link = re.compile(r"\[<([^#@!].*?)>\]")


def format_special(x, members, channels):
    xs = x.split('|', 2)
    if len(xs) == 2:
        label = xs[1]
    else:
        label = xs[0]
    if x[0] == '#':
        return '#' + channels[xs[0][1:]]['name']
    elif x[0] == '@':
        try:
            return '@' + members[xs[0][1:]]['name']
        except KeyError:
            return label
    elif x[0] == '!':
        return label
    else:
        return '[%s](%s)' % (label.replace('(', '%28').replace(')', '%29').replace(',', '%2C'),
                             xs[0].replace('(', '%28').replace(')', '%29').replace(',', '%2C'))


def format_text(text, members, channels):
    text = string.replace(text, "a/&lt;!", "")
    text = re.sub(quirk_link, lambda x: "[{}]".format(x.group(1)), text)
    text = re.sub(special_pat, lambda x: format_special(x.group(1), members, channels), text)
    return markdown(text)


def export(sc, config, arguments):
    channels = sc.api_call('channels.list')['channels']
    members = sc.api_call('users.list')['members']

    channels = {x['id']: x for x in channels}
    members = {x['id']: x for x in members}

    renderer = pystache.Renderer(search_dirs='template')
    out_dir = arguments['<output_dir>']
    shutil.copy2('template/global.css', out_dir)
    today = datetime.today().strftime('%Y-%m-%d')

    with codecs.open(os.path.join(out_dir, 'index.html'), 'wb', 'utf-8') as f:
        f.write(renderer.render_path('template/index.mustache', {'channels': channels.values(), }))

    for channel in channels.values():
        p = os.path.join(out_dir, channel['name'])
        try:
            os.makedirs(p)
        except OSError:
            pass

    for log in sorted(glob('logs/*.txt')):
        print log
        date, _ = os.path.splitext(os.path.basename(log))
        data = defaultdict(OrderedDict)
        with codecs.open(log, 'rb', 'utf-8') as f:
            for msg in f:
                sys.stdout.write('.') 
                msg = json.loads(msg)
                channel = msg['channel']
                if 'subtype' in msg:
                    if msg['subtype'] == 'message_changed':
                        msg = msg['message']
                        if msg['ts'] not in data[channels[channel]['name']]:
                            continue
                    elif msg['subtype'] == 'message_deleted':
                        try:
                            del data[channels[channel]['name']][msg['deleted_ts']]
                        except KeyError:
                            pass
                        continue
                    elif msg['subtype'] == "file_share":
                        pass
                    else:
                        continue
                if 'user' not in msg:
                    continue
                user_id = msg['user']
                if user_id == u'USLACKBOT':
                    continue
                msg['user'] = members[user_id]['name']
                msg['avatar'] = members[user_id]['profile']['image_48']
                # Generate a message id based on the message ts timestamp.
                # While this could potentially cause a conflict if two messages
                # have the same timestamp, we're already assuming timestamp
                # uniqueness when we're adding it to the `data` hash below.
                msg_datetime = datetime.fromtimestamp(float(msg['ts']))
                msg['msgid'] = msg_datetime.strftime('inst-%Y-%m-%dT%H:%M:%S.%fZ')
                msg['timestamp'] = msg_datetime.strftime('%H:%M:%S')
                msg['text'] = format_text(msg['text'], members, channels)
                try:
                    data[channels[channel]['name']][msg['ts']] = msg
                except KeyError as e:
                    print e

        channel_names = [{'name': name} for name in data.keys()]

        for channel_name, msgs in data.iteritems():
            with codecs.open(os.path.join(out_dir, channel_name, date) + '.html', 'wb', 'utf-8') as f:
                f.write(renderer.render_path('template/day.mustache', {'active_channel': channel_name,
                                                                       'channels': channel_names,
                                                                       'messages': msgs.values(),
                                                                       'date': date}))

        if date < today:
            shutil.move(log, os.path.join('/var/slackbot/backups/logs', os.path.basename(log)))

    for channel in channels.values():
        p = os.path.join(out_dir, channel['name'])
        dates = []
        g = glob(os.path.join(p, '????-??-??.html'))
        g.sort()
        for html in g:
            date, _ = os.path.splitext(os.path.basename(html))
            dates.append({'date': date})
        with codecs.open(os.path.join(p, 'index.html'), 'wb', 'utf-8') as f:
            f.write(renderer.render_path('template/channel-index.mustache', {'dates': dates,
                                                                             'active_channel': channel['name']}))


def get_human_tools(sc, config, arguments):
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

    return channels, members, human_id, bot_id


def invite(sc, config, arguments):
    channels, members, human_id, bot_id = get_human_tools(sc, config, arguments)
    human = SlackClient(config['HUMAN_SLACK_TOKEN'])

    for channel in channels:
        print '>>>', channel['name']

        if channel['name'] in config['IGNORE_CHANNELS']:
            print 'channel ignored'
            continue

        if channel['is_archived']:
            print "is archived"
            continue

        chan_id = channel['id']
        is_human_in_chan = False
        is_bot_in_chan = False

        for member in json.loads(sc.api_call('channels.info', channel=chan_id))['channel']['members']:
            if member == human_id:
                is_human_in_chan = True
            elif member == bot_id:
                is_bot_in_chan = True
                break

        if is_bot_in_chan:
            print "already in chan"
            continue

        if not is_human_in_chan:
            print "join"
            human.api_call('channels.join', name=channel['name'])

        print human.api_call('channels.invite', channel=chan_id, user=bot_id)

        if not is_human_in_chan:
            print "leave"
            human.api_call('channels.leave', channel=chan_id)


def list_channels(sc):
    print ', '.join([c['name'] for c in json.loads(sc.api_call('channels.list'))['channels']])


def kick(sc, config, arguments):
    human = SlackClient(config['HUMAN_SLACK_TOKEN'])
    channels, members, human_id, bot_id = get_human_tools(sc, config, arguments)

    for channel in channels:
        if channel['name'] == arguments['<channel>']:
            is_human_in_chan = False
            is_bot_in_chan = False

            for member in json.loads(sc.api_call('channels.info', channel=channel['id']))['channel']['members']:
                if member == human_id:
                    is_human_in_chan = True
                elif member == bot_id:
                    is_bot_in_chan = True

            if not is_bot_in_chan:
                print "already not in chan"
                continue

            if not is_human_in_chan:
                print "join"
                human.api_call('channels.join', name=channel['name'])

            print human.api_call('channels.kick', channel=channel['id'], user=bot_id)

            if not is_human_in_chan:
                print "leave"
                human.api_call('channels.leave', channel=channel['id'])

            break


if __name__ == "__main__":
    arguments = docopt(__doc__, version='Slack Archivist v0.1')
    config = yaml.load(file('rtmbot.conf', 'r'))
    sc = SlackClient(config['SLACK_TOKEN'])
    if arguments['list']:
        list_channels(sc)
    elif arguments['invite']:
        invite(sc, config, arguments)
    elif arguments['export']:
        export(sc, config, arguments)
    elif arguments['kick']:
        kick(sc, config, arguments)
