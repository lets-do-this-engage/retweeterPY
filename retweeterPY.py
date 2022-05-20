import tweepy
import os
import re
from dotenv import load_dotenv
from datetime import datetime
import sqlite3 as sl

print("[" + str(datetime.now()) +  "] Begin.", flush=True)

#load config
print("[" + str(datetime.now()) +  "] Loading variables...", flush=True)
accountList = {}
load_dotenv()
for envVar in os.environ:
	if re.search('consumer_key', envVar, re.IGNORECASE) or re.search('consumer_secret', envVar, re.IGNORECASE) or re.search('access_token', envVar, re.IGNORECASE) or re.search('access_token_secret', envVar, re.IGNORECASE) or re.search('bearer_token', envVar, re.IGNORECASE):
		if envVar[0:envVar.index('.')] not in accountList:
			accountList[envVar[0:envVar.index('.')]] = {}
		accountList[envVar[0:envVar.index('.')]][envVar[envVar.index('.') + 1:]] = os.getenv(envVar)
#setup db
con = sl.connect(os.getenv('db_path'))
sql = "create table if not exists users_latestest_tweet (screen_name text, last_tweet_id text)"
cur = con.cursor()
cur.execute(sql)
#retrieve tweets from specified accounts
for screen_name in accountList:
	print("Processing: [" + str(screen_name) + "]")
	consumer_key= accountList[screen_name]['consumer_key']
	consumer_secret= accountList[screen_name]['consumer_secret']
	access_token= accountList[screen_name]['access_token']
	access_token_secret= accountList[screen_name]['access_token_secret']
	bearer_token= accountList[screen_name]['bearer_token']
	#set up API connection
	print("[" + str(datetime.now()) +  "] Setting up API connection...", flush=True)
	
	client = tweepy.Client(bearer_token=bearer_token, 
							consumer_key=consumer_key, 
							consumer_secret=consumer_secret, 
							access_token=access_token, 
							access_token_secret=access_token_secret)
	user_id = client.get_user(username = 'JTKirkmanWF')[0].id
	last_tweet_id = 0
	cur.execute("select last_tweet_id from users_latestest_tweet where screen_name = '" + screen_name + "'")
	if len(cur.fetchall()) != 0:
		last_tweet_id = cur.fetchall()[0]
	print("last_tweet_id : [" + str(last_tweet_id) + "]")
	pagination_token = None
	while True:
		try:
			tweets = client.get_users_tweets(user_id, exclude='replies', max_results=100, since_id=last_tweet_id, pagination_token=pagination_token)
			print("loopin tweets: [" + str(tweets) + "]")
			if tweets.data:
				for tweet in tweets.data:
					tweetText = re.sub(r'http\S+', '', tweet.text)
					print("tweet id: [" + str(tweet.id) + "] tweet: [" + str(tweetText) + "]")
					last_tweet_id = tweet.id
				if 'next_token' in tweets.meta:
					pagination_token = tweets.meta['next_token']
				else:
					break
			else:
				print("Ran out of tweets")
				sql = "INSERT INTO users_latestest_tweet (screen_name, last_tweet_id) values ('" + screen_name + "','" + str(last_tweet_id) + "')"
				cur.execute(sql)
				break
		except tweepy.errors.TooManyRequests as e:
			print("[" + str(datetime.now()) +  "] Caught a TooManyRequests exception: " + str(e), flush=True)
			print("[" + str(datetime.now()) +  "] Taking a 15 minute nap.", flush=True)
			time.sleep(60 * 15)
		except tweepy.errors.TweepyException as e:
			print("[" + str(datetime.now()) +  "] Caught an exception: " + str(e), flush=True)
			print("[" + str(datetime.now()) +  "] api_codes: " + str(e.api_codes), flush=True)
	#check to see if tweet matches our config
		#if so retweet