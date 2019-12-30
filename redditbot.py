import time
import re
import urllib2
import signal, sys
import redis
import json
import HTMLParser

import praw

import itemparser as ip

FOOTER_TEXT = u"---\n\n^^Questions? ^^Message ^^/u/ha107642 ^^\u2014 ^^Call ^^wiki ^^pages ^^\\(e.g. ^^items ^^or ^^gems)) ^^with ^^[[NAME]] ^^\u2014 ^^I ^^will ^^only ^^post ^^panels ^^for ^^*unique* ^^items ^^\u2014 ^^[Github](https://github.com/ha107642/RedditPoEBot/)\n"
IGNORE_LIST_FILENAME = "username_ignore_list.txt"

# Are comments, submissions and messages really unique among each other?
# Can a comment and a private message have the same ID?
def is_parsed(comment_id):
    return redis.sismember("parsed_comments", comment_id)

def add_parsed(comment_id):
    return redis.sadd("parsed_comments", comment_id)

def is_ignored(username):
    return username in ignore_list

def bot_comments():
    sub_comments = subreddit.comments()
    for comment in sub_comments:
        # Checks if the post is not actually the bot itself (since the details say [[NAME]])
        if not is_parsed(comment.id) and not is_ignored(comment.author):
            reply = build_reply(comment.body)
            if reply:
                try:
                    comment.reply(reply)
                except Exception, e:
                    print str(e)
            # Add the post to the set of parsed comments
            add_parsed(comment.id)

def bot_submissions():
    sub_subs = subreddit.new(limit=5)
    for submission in sub_subs:
        if not is_parsed(submission.id):
            reply = build_reply(submission.selftext)
            if reply:
                try:
                    submission.add_comment(reply)
                except Exception, e:
                    print str(e)
            add_parsed(submission.id)

def bot_messages():
    msg_messages = r.inbox.messages(limit=20)
    for message in msg_messages:
        if not is_parsed(message.id):
            reply = build_reply(message.body)
            if reply:
                try:
                    message.reply(reply)
                except Exception, e:
                    print str(e)
            add_parsed(message.id)

# Regex Magic that finds the text encaptured with [[ ]]
pattern = re.compile("\[\[([^\[\]]*)\]\]")

def build_reply(text):
    reply = ""
    if text is None: return None
    links = pattern.findall(text)
    if not links: return None
    # Remove duplicates
    unique_links = []
    for i in links:
        if i not in unique_links:
            unique_links.append(i)
    # Because a comment can only have a max length, limit to only the first 30 requests
    if len(unique_links) > 30: unique_links = unique_links[0:30]
    for i in unique_links:
        if not i: continue
        name, link = lookup_name(i)
        if link is None: continue
        escaped_link = link.replace("(", "\\(").replace(")", "\\)")
        specific_name, panel = get_item_panel(name)
        if panel is not None:
            if specific_name != name:
                reply += "[%s](%s) *(Showing %s)*\n\n" % (name, escaped_link, specific_name)
            else:
                reply += "[%s](%s)\n\n" % (name, escaped_link)
            reply += ip.parse_item(panel)
    if reply is "":
        return None
    return reply + FOOTER_TEXT

# Fetches a page and returns the response.
def get_page(link):
    try:
        request = urllib2.Request(link, headers={"User-Agent": "PoEWikiBot", "Accept": "*/*"})
        response = urllib2.urlopen(request)
        return response.read()
    except urllib2.HTTPError, e:
        return None
    except AttributeError, e:
        print "ERROR: %s" % str(e)
        return None

# The input name might differ from what we return as name.
# E.g. input "Vessel of Vinktar" may return "Vessel of Vinktar (Added Lightning Damage to Attacks)",
# since there are several versions of Vessel of Vinktar.
def get_item_panel(name):
    name = urllib2.quote(name)
    url = "https://pathofexile.gamepedia.com/api.php?action=cargoquery&tables=items&fields=items.html,items.name&where=items.name%%20=%%20%%22%s%%22&format=json" % name
    response = get_page(url)
    json_data = json.loads(response)
    if "cargoquery" not in json_data:
        return (None, None)

    for item in json_data["cargoquery"]:
        obj = item["title"]
        if obj is not None:
            return (obj["name"], HTMLParser.HTMLParser().unescape(obj["html"]))
    return (None, None)

def lookup_name(name):
    name = urllib2.quote(name)
    search_url = "http://pathofexile.gamepedia.com/api.php?action=opensearch&search=%s" % name
    response = get_page(search_url)
    try:
        hits = json.loads(response)
    except ValueError:
        return (None, None)
    # opensearch returns a json array in a SoA fashion,
    # where arr[0] is the search text, arr[1] matching pages,
    # arr[2] ??, arr[3] links to the matching pages.
    # e.g. ["facebreaker",["Facebreaker","FacebreakerUnarmedMoreDamage"],["",""],["http://pathofexile.gamepedia.com/Facebreaker","http://pathofexile.gamepedia.com/FacebreakerUnarmedMoreDamage"]]
    if not hits[1]:
        return (None, None) # If we did not find anything, return None.
    return (hits[1][0], hits[3][0]) # Otherwise, return the first match in a tuple with (name, url).

def signal_handler(signal, frame):
    redis.save()
    sys.exit(0)

# Only run the following if we are actually executing this file directly.
if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)

    ignore_list = [line.rstrip('\n') for line in open(IGNORE_LIST_FILENAME)]

    # This string is sent by praw to reddit in accordance to the API rules
    user_agent = ("REDDIT Bot v1.5 by /u/ha107642")
    r = praw.Reddit(user_agent=user_agent)

    redis = redis.StrictRedis(host="PathOfExileFR+pathofexile")

    username = r.user.me().name

    # Fill in the subreddit(s) here. Multisubs are done with + (e.g. MagicTCG+EDH)
    subreddit = r.subreddit('pathofexile')

    # Infinite loop that calls the function. The function outputs the post-ID's of all parsed comments.
    # The ID's of parsed comments is compared with the already parsed comments so the list stays clean
    # and memory is not increased. It sleeps for 15 seconds to wait for new posts.
    while True:
        try:
            bot_comments()
            time.sleep(5)
            bot_submissions()
            time.sleep(5)
            bot_messages()
            time.sleep(5)
        except praw.exceptions.PRAWException as e:
            print e
            time.sleep(60)