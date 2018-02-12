# -*- coding: utf-8 -*-

from dotenv import load_dotenv
import tweepy
from tweepy.error import TweepError
import gitlab as gitlabApi
import os
import datetime

dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(dotenv_path)

class Twitter(object):
    def __init__(self):
        consumer_key = os.environ.get("TWITTER_CONSUMER_KEY")
        consumer_secret = os.environ.get("TWITTER_CONSUMER_SECRET")
        access_token = os.environ.get("TWITTER_ACCESS_TOKEN")
        access_secret = os.environ.get("TWITTER_ACCESS_SECRET")
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_secret)
        self.api = tweepy.API(auth)
    
    def notify(self, text, reply_id=None):
        try:
            if reply_id is None:
                status = self.api.update_status(text)
            else:
                status = self.api.update_status(text, reply_id)
            return status
        except TweepError as e:
            print("send message failed " + e.reason)
            raise TweepError

class Gitlab(object):
    def __init__(self):
        personal_access_token = os.environ.get("GITLAB_PERSONAL_ACCESS_TOKEN")
        gl = gitlabApi.Gitlab('https://gitlab.com', private_token=personal_access_token)
        gl.auth()
        self.api = gl
    
    def getEvents(self):
        # 昨日の0:00より前は除外
        after = datetime.date.today() - datetime.timedelta(days=2)
        # 今日の0:00以降は除外
        before = datetime.date.today()
        events = self.api.events.list(after=after, before=before)
        return events
    
    def analyzeEvents(self):
        events = self.getEvents()
        event_data = {}
        event_data["events_count"] = len(events)
        event_data["commits_count"] = 0
        event_data["comments_count"] = 0
        event_data["opened_merge_request"] = 0
        event_data["closed_merge_request"] = 0
        for event in events:
            action_name = event.action_name.split()[0]
            if action_name == "commented":
                event_data["comments_count"] = event_data["comments_count"] + 1
            elif action_name == "opened":
                if event.target_type == "MergeRequest":
                    event_data["opened_merge_request"] = event_data["opened_merge_request"] + 1
            elif action_name == "closed":
                if event.target_type == "MergeRequest":
                    event_data["closed_merge_request"] = event_data["closed_merge_request"] + 1
            event_data["commits_count"] = event_data["commits_count"] + self.getCommitCountFromEvent(event)

        return event_data

    def getCommitCountFromEvent(self, event):
        try:
            commit_count = event.push_data["commit_count"]
        except Exception:
            commit_count = 0
        return commit_count

def main():
    gl = Gitlab()
    data = gl.analyzeEvents()
    target_day = datetime.date.today() - datetime.timedelta(days=1)
    target_day_str = target_day.strftime('%Y/%m/%d')
    data['date'] = target_day_str
    twitter = Twitter()
    author = twitter.api.me().screen_name
    data['author'] = author
    text = "%(author)s さんの %(date)s のGitlabでの活動は %(events_count)s 件でした。\n" + \
    "コミット数 %(commits_count)s\n" + \
    "#gitlab_activities_tweeter" % data
    twitter.notify(text)

if __name__ == '__main__':
    main()
