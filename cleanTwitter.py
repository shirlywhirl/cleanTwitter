#!/usr/bin/env python


import os
import sys
import argparse
#import datetime 
from datetime import datetime, timedelta, time
import configparser
import time
import json
import tweepy
import pprint


class TwitterClean():
    def __init__(self, args=None):
        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.config_path = os.path.join(self.script_dir, "settings.ini")
        self.authenticate_from_config()  # check required settings first

    def authenticate_from_config(self, config_path=None):
        if config_path is not None:
            self.config_path = config_path
        config = configparser.ConfigParser()
        try:
            with open(self.config_path) as h:
                config.read_file(h)
        except IOError:
            print("Please specify a valid config file.")
        else:
            try:
                ck = config.get('Authentication', 'ConsumerKey')
                cs = config.get('Authentication', 'ConsumerSecret')
                at = config.get('Authentication', 'AccessToken')
                ats = config.get('Authentication', 'AccessTokenSecret')
            except (configparser.NoSectionError,):
                print("Please check the [Authentication] information in your configuration file.")
                self.api = None
            else:
                if all([ck, cs, at, ats]):
                    self.authenticate(ck, cs, at, ats)
                else:
                    self.api = None
                    print("Please check the options set under [Authentication] in your configuration file.")

    def authenticate(self, consumer_key, consumer_secret, access_token, access_token_secret):
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit_notify=True, wait_on_rate_limit=True)
        try:
            self.me = self.api.me()
            #self.me = None  # only used to test access
            self.followers=self.api.followers_ids(id=self.me.id)
            self.friends=self.api.friends_ids(id=self.me.id)
        except tweepy.error.TweepError as e:
            print("Please check the authentication information:\n{}".format(e))
            self.api = None
            self.me = None

    def limit_handled(self,cursor):
        while True:
            try:
                yield cursor.next()
            except tweepy.RateLimitError:
                time.sleep(15 * 60)
            except StopIteration:
                return

    def block_followers(self,target_user):
        for follower_id in self.limit_handled(tweepy.Cursor(self.api.followers_ids,id=target_user).items()):
            try:
                screen_name=self.api.get_user(id=follower_id).screen_name 
                print( "Blocking user: %s UserID: %s" %(screen_name,follower_id) )
            except tweepy.error.TweepError:
                print("ERROR:  couldn't get screen name or follower_id")
            
            try:
                if follower_id not in self.followers:
                    if follower_id not in self.friends:
                        print( "> user: %s is  not a friend"%(screen_name) )
                        self.api.create_block(follower_id)
                        time.sleep(1)
                    else:
                        print( "> user: %s is a friend" %(screen_name) )
                else:
                    print( "> user: %s is a friend" %(screen_name) )
            except tweepy.error.TweepError:
                print( "FAILED: Couldnt block user: %s UserID: %s" %(screen_name,follower_id) )

    def unretweet(self,target_id):
        """ If the wtweet is a retweet will unretweet it """
        status = self.api.get_status(target_id, tweet_mode="extended")
        if hasattr(status, "retweeted_status"):  # Check if Retweet
            print( "%s Has attribute: retweeted_status" % (target_id) )
            self.api.unretweet(target_id)
            self.api.destroy_status(target_id)
        else:
            print( "%s does NOT have attribute: rewteeted_status" % (target_id)  )

    def unlike(self,target_id):
        """ unlike tweet """
        try:
            self.api.destroy_favorite(target_id)
        except tweepy.error.TweepError as e:
            print( "%s could not be unliked,trying like/unlike" % (target_id)  )
            try:
                self.api.create_favorite(target_id)
                self.api.destroy_favorite(target_id)
                print( ">> %s likely unliked" % (target_id)  )
            except:
                print( ">> %s could not be unliked" % (target_id)  )

    def unlike_old_tweets(self, max_age=30):
        for page in self.limit_handled( tweepy.Cursor(self.api.favorites).pages() ):
            for favorite in page:
              try: 
                  if favorite.created_at < datetime.now() - timedelta(days=max_age) :
                      print( ">> %s unliking old tweet from %s" % (favorite.id,favorite.created_at) )
                      self.unlike( favorite.id )
                  else:
                      print( ">> %s keeping like on old tweet from %s" % (favorite.id,favorite.created_at) )
                      
              except:
                  print( ">> %s old tweet errored" % ( favorite.id ) )
  

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Unlike or delete (re-)tweets (and optionally export them first). Set other parameters via configuration file (default: "settings.ini" in script directory) or arguments. Set arguments will overrule the configuration file.')
    parser.add_argument("--blockchain", default=None, dest="target_user", help='Target user to block followers', type=str, action="store")
    parser.add_argument("--unretweet", default=None, dest="untweet_id", help='Target id to delete if not retweet', type=str, action="store")
    parser.add_argument("--unlike", default=None, dest="unlike_id", help='Target id to delete if not retweet', type=str, action="store")
    parser.add_argument("--oldlikes", default=None, dest="old_likes_age", help='Tweets older then X days', type=int, action="store")
    args = parser.parse_args()
    twitter = TwitterClean(args)
    if args.target_user:
        twitter.block_followers(args.target_user)
    if args.untweet_id:
        twitter.unretweet(args.untweet_id)
    if args.unlike_id:
        twitter.unlike(args.unlike_id)
    if args.old_likes_age:
        twitter.unlike_old_tweets(max_age=args.old_likes_age)
