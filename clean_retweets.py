#!/usr/bin/python


import os
import sys
import argparse
import datetime 
import configparser
import time
import json
import tweepy
import pprint


class Unfollower():
    def __init__(self, args=None):
        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.config_path = os.path.join(self.script_dir, "settings.ini")
        self.authenticate_from_config()  # check required settings first
        if args:
            self.target_user = args.target_user
            self.target_id = args.target_id

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

    def block_followers(self):
        for follower_id in self.limit_handled(tweepy.Cursor(self.api.followers_ids,id=self.target_user).items()):
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


    def unretweet(self):
        """ If the wtweet is a retweet will unretweet it """
        status = self.api.get_status(self.target_id, tweet_mode="extended")
        ## Works!
        #try:
        #    print(status.retweeted_status.full_text)
        #    print( "Is a retweet" )
        #except AttributeError:  # Not a Retweet
        #    print( "Is not a retweet" )
        #    print(status.full_text)

        if hasattr(status, "retweeted_status"):  # Check if Retweet
            print( "Has attribute: retweeted_status" )
        else:
            print( "does NOT have attribute: rewteeted_status" )
            self.api.unretweet(id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Unlike or delete (re-)tweets (and optionally export them first). Set other parameters via configuration file (default: "settings.ini" in script directory) or arguments. Set arguments will overrule the configuration file.')
    parser.add_argument("--user", default=None, dest="target_user", help='Target user to block', type=str, action="store")
    parser.add_argument("--id", default=None, dest="target_id", help='Target id to delete if not retweet', type=str, action="store")
    parser.add_argument("--unfavorite", default=None, dest="target_id", help='Target id to delete if not retweet', type=str, action="store")
    args = parser.parse_args()
    unfollower = Unfollower(args)
    if args.target_user:
        unfollower.block_followers()
    if args.target_id:
        unfollower.on_status()
