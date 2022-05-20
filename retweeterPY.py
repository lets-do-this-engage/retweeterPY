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

accountsToWatch = ['JTKirkmanWF', 'WFSly', 'WilsonWildingWF']
mainScreenName = 'TheWorstFans'
mainConsumerKey= accountList[mainScreenName]['consumer_key']
mainConsumerSecret= accountList[mainScreenName]['consumer_secret']
mainAccessToken= accountList[mainScreenName]['access_token']
mainAccessToken_secret= accountList[mainScreenName]['access_token_secret']
mainBearerToken= accountList[mainScreenName]['bearer_token']

def getKeywords():
	with open('/var/scripts/retweeterPY/.keywords') as file:
		for line in file:
			if not line.startswith('#'):
				line = line.rstrip()
				#print("getKeywords : " + line)
				screen_name = line[0:line.index('=')]
				#print("screen_name: [" + screen_name + "]")
				keyword = line[line.index('=') + 1:len(line)]
				#print("keyword: [" + keyword + "]")
				keywordList = []
				if 'keywordList' in accountList[screen_name]:
					keywordList = accountList[screen_name]['keywordList']
				keywordList.append(keyword)
				accountList[screen_name]['keywordList'] = keywordList
	
def retweetAndLike(screen_name, tweetId):
	consumer_key = accountList[screen_name]['consumer_key']
	consumer_secret = accountList[screen_name]['consumer_secret']
	access_token = accountList[screen_name]['access_token']
	access_token_secret = accountList[screen_name]['access_token_secret']
	bearer_token = accountList[screen_name]['bearer_token']
	client = tweepy.Client(bearer_token=bearer_token, 
							consumer_key=consumer_key, 
							consumer_secret=consumer_secret, 
							access_token=access_token, 
							access_token_secret=access_token_secret)
	print("retweeting! screen_name: [" + str(screen_name) + "] tweetId : [" + str(tweetId) + "]")
	client.retweet(tweetId)
	client.like(tweetId)

def processTweet(userTweet, retweet):
	tweets = [userTweet, retweet]
	for tweet in tweets:
		if tweet:
			tweetText = re.sub(r'http\S+', '', tweet.text)
			#print("tweet id: [" + str(tweet.id) + "] tweet: [" + str(tweetText) + "] accountList: [" + str(accountList) + "]")
			for screen_name in accountList:
				if 'keywordList' in accountList[screen_name]:
					keywordList = accountList[screen_name]['keywordList']
					for keyword in keywordList:
						print("Processing: [" + str(screen_name) + "] keyword : [" + keyword + "] tweetText : [" + tweetText + "]")
						if keyword.lower() in tweetText:
							print("Found the keyword [" + keyword + "] in [" + tweetText + "], retweet this motha!")
							retweetAndLike(screen_name, userTweet.id)

getKeywords()
#setup db
con = sl.connect(os.getenv('db_path'))
sql = "create table if not exists users_latestest_tweet (screen_name text, last_tweet_id text)"
cur = con.cursor()
cur.execute(sql)
#retrieve tweets from specified accounts
for accountToWatch in accountsToWatch:
	print("Processing: [" + str(accountToWatch) + "]")
	#set up API connection
	print("[" + str(datetime.now()) +  "] Setting up API connection...", flush=True)
	client = tweepy.Client(bearer_token=mainBearerToken, 
							consumer_key=mainConsumerKey, 
							consumer_secret=mainConsumerSecret, 
							access_token=mainAccessToken, 
							access_token_secret=mainAccessToken_secret)
	userId = client.get_user(username = accountToWatch)[0].id
	lastTweetId = 0
	cur.execute("select last_tweet_id from users_latestest_tweet where screen_name = '" + accountToWatch + "';")
	result = cur.fetchall()
	if len(result) != 0:
		#print ("executed : [" + "select last_tweet_id from users_latestest_tweet where screen_name = '" + accountToWatch + "'" + "]")
		#print("result : [" + str(result[0][0]) + "]")
		lastTweetId = result[0][0]
		#break
	print("lastTweetId : [" + str(lastTweetId) + "]")
	paginationToken = None
	while True:
		try:
			tweets = client.get_users_tweets(userId, exclude='replies', max_results=100, since_id=lastTweetId, pagination_token=paginationToken, tweet_fields=['referenced_tweets'])
			#print("loopin tweets: [" + str(tweets) + "]")
			if tweets.data:
				for tweet in tweets.data:
					#print("loopin tweet: [" + str(tweet) + "]")
					#print("loopin referenced_tweets: [" + str(tweet.referenced_tweets) + "]")
					retweet = None
					if tweet.referenced_tweets:
						print("this is a rt!! tweet.referenced_tweets : [" + str(tweet.referenced_tweets) + "]")
						for referenced_tweet_id in tweet.referenced_tweets:
							print("referenced_tweet_id : [" + str(referenced_tweet_id.id) + "]")
							#processTweet(client.get_tweet(referenced_tweet_id.id))
							retweet = client.get_tweet(referenced_tweet_id.id).data
					processTweet(tweet, retweet)
					if int(tweet.id) > int(lastTweetId):
						lastTweetId = tweet.id
				if 'next_token' in tweets.meta:
					paginationToken = tweets.meta['next_token']
				else:
					break
			else:
				print("Ran out of tweets")
				sql = "INSERT INTO users_latestest_tweet (screen_name, last_tweet_id) values ('" + accountToWatch + "','" + str(lastTweetId) + "')"
				cur.execute(sql)
				break
		except tweepy.errors.TooManyRequests as e:
			print("[" + str(datetime.now()) +  "] Caught a TooManyRequests exception: " + str(e), flush=True)
			print("[" + str(datetime.now()) +  "] Taking a 15 minute nap.", flush=True)
			time.sleep(60 * 15)
		except tweepy.errors.TweepyException as e:
			print("[" + str(datetime.now()) +  "] Caught an exception: " + str(e), flush=True)
			print("[" + str(datetime.now()) +  "] api_codes: " + str(e.api_codes), flush=True)
#Clean up
con.commit()
cur.close()
print("[" + str(datetime.now()) +  "] Fin.", flush=True)