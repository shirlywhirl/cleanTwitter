#!/usr/bin/python


import os
import sys
import argparse
import datetime 
import configparser
import time
import json
import tweepy


class Unfollower():
    def __init__(self, args=None):
        self.script_dir = os.path.dirname(os.path.realpath(sys.argv[0]))
        self.config_path = os.path.join(self.script_dir, "settings.ini")
        self.authenticate_from_config()  # check required settings first
        if args:
            self.target_user = args.target_user

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
            self.me = None  # only used to test access
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
        for follower_id in self.limit_handled(tweepy.Cursor(uf.api.followers_ids,id=self.target_user).items()):
            try:
                screen_name=uf.api.get_user(id=follower_id).screen_name 
                print( "Blocking user: %s UserID: %s" %(screen_name,follower_id) )
            except:
                print("ERROR:  couldn't get screen name or follower_id")
            
            try:
                uf.api.create_block(follower_id)
            except:
                print( "FAILED: Couldnt block user: %s UserID: %s" %(screen_name,follower_id) )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Unlike or delete (re-)tweets (and optionally export them first). Set other parameters via configuration file (default: "settings.ini" in script directory) or arguments. Set arguments will overrule the configuration file.')
    parser.add_argument("--user", default=None, dest="target_user", help='Target user to block', type=str, action="store")
    args = parser.parse_args()
    uf = Unfollower(args)
    if args.target_user:
        uf.block_followers()
