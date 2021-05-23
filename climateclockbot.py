#!/usr/bin/python
# -*- coding: utf-8 -*-

import config
import datetime
import json
import logging
import math
import os
import random
import ssl
import sys
import time
import urllib
from datetime import datetime, timezone
from datetime import timedelta
from dateutil.parser import *
from dateutil.relativedelta import relativedelta
from mastodon import Mastodon
from twython import Twython

def connectTwitter():
	# connect to twitter API
	return Twython(config.twitter_key, config.twitter_secret,
		config.access_token, config.access_secret)

def post_tweet(twitter, to_tweet):
	# post the string to twitter
	twitter.update_status(status=to_tweet)

def getClimateData():
	# https://climate-clock.gitbook.io/climate-clock-docs/climate-clock-api
	url = "https://api.climateclock.world/v1/clock"
	data = json.loads(urllib.request.urlopen(url, context=ssl.SSLContext()).read())
	return data['data']['modules']

def assembleTweet(data):
	carbon_budget = 420000000000
	carbon_per_year = 42000000000

	starttime = datetime(2018, 1, 1, 0, 0, 0, 0, timezone.utc)
	endtime = parse(data['carbon_deadline_1']['timestamp'])
	nowtime = datetime.now(timezone.utc)
	remaining = relativedelta(endtime, nowtime)

	assert nowtime < endtime, "But... the future refused to change."

	# annoying! extract years + days, ignoring months
	midtime = nowtime + relativedelta(years=+remaining.years)
	days_remaining = (endtime - midtime).days

	carbon_per_second = carbon_per_year / timedelta(days=365.2422).total_seconds()
	budget_remaining = carbon_budget - (nowtime - starttime).total_seconds() * carbon_per_second

	renew_initial = data['renewables_1']['initial']
	renew_starttime = parse(data['renewables_1']['timestamp'])
	renew_rate = data['renewables_1']['rate']
	renew_current = renew_initial + (nowtime - renew_starttime).total_seconds() * renew_rate

	co2_symbols = [u"\U0001F525", u"\U000026A0", u"\U0001F6E2", u"\U000026FD"]
	format1 = u"%s %.3f Gt of CO%s remaining for +1.5%sC (66%% prob.)"
	tweet1 = format1 % (random.choice(co2_symbols), (budget_remaining / 1E9), u"\U00002082", u"\U000000B0")

	time_symbols = [u"\U000023F3", u"\U000023F0", u"\U000023F2", u"\U0001F4C5"]
	format2 = u"%s %i years %i days %i hours until overshoot"
	tweet2 = format2 % (random.choice(time_symbols), remaining.years, days_remaining, remaining.hours)

	renew_symbols = [u"\U0001F331", u"\U0001F32C", u"\U00002600"]
	format3 = u"%s %.3f%% of world energy from renewables"
	tweet3 = format3 % (random.choice(renew_symbols), renew_current)

	return u"%s\n%s\n%s" % (tweet1, tweet2, tweet3)
	
if __name__ == "__main__":
	# heroku scheduler runs every 12 hours
	try:
		# assemble climate data
		data = getClimateData()
		to_tweet = assembleTweet(data)
		print(to_tweet.encode('ascii', 'ignore'))
		
		# post the tweet
		twitter = connectTwitter()
		post_tweet(twitter, to_tweet)
		
		# post to Mastodon, secret token generated offline
		mastodon = Mastodon(
			access_token = 'mastodon_user.secret',
			api_base_url = 'https://botsin.space'
		)
		mastodon.toot(to_tweet)

		sys.exit(0) # success!
	except SystemExit as e:
		# working as intended, exit normally
		sys.exit(e)
	except:
		logging.exception(sys.exc_info()[0])
