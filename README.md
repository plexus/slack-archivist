slack-archivist
=============
A Slack bot aimed to keep team logs. Please, make sure that using it does not violate [Slack API TOS](https://slack.com/terms-of-service/api) before start.
Bot is based on [rtmbot](https://github.com/slackhq/python-rtmbot) and could be extended in the same way. See rtmbot docs for details.
It is pre-alpha quick&dirty (insert your favourite earliest version marker here) implementation, having many to-be-parametrized things hardcoded.
Any cleanup/improvement/bugfix PRs are welcome and are highly appreciated.

Dependencies
----------
See [requirements.txt](requirements.txt)

Installation
-----------

1. Download the code

        git clone git@bitbucket.org:ul/slack-archivist.git
        cd slack-archivist

2. Install dependencies ([virtualenv](http://virtualenv.readthedocs.org/en/latest/) is recommended.)

        pip install -r requirements.txt

3. Configure (https://api.slack.com/bot-users)
        
        vi rtmbot.conf
          DEBUG: False
          SLACK_TOKEN: "xoxb-11111111111-222222222222222"
          HUMAN_SLACK_TOKEN: "xoxb-11111111111-222222222222222"

*Note:* `SLACK_TOKEN` is bot's token, the only one necessary to log & export. `HUMAN_SLACK_TOKEN` is regular user's token and could be provided for automating bot invite to channels, because bots are not allowed to join channels by themselves. 

Log
---
After running, `rtmbot.py` will start to log arriving messages from all channels he is joined to, split by dates, into `logs` directory.
To invite bot to all channels, run `cli.py invite human_name bot_name`, where names corresponds tokens given in the config.

Export to html
--------------
Tune `template` content to match your needs. Specifically, [day.mustache](template/day.mustache) is the root template for messages display,
and [index.mustache](template/index.mustache) & [channel-index.mustache](template/channel-index.mustache) are templates for channels and dates index pages respectively.
Then run `cli.py export output_dir` to convert logs to html and move old logs to backup dir.
*Note:* at the moment too many things, like slack team name, Google CSE widget and backup path are hardcoded, bot was created in hurry. I apologize for that again and will be very grateful for PRs fixing that.