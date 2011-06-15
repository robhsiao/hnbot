# -*- encoding: utf8 -*-

from bottle import route, run, request, template, abort, debug #TODO remove
from google.appengine.ext import db
from google.appengine.api import urlfetch, mail, taskqueue, memcache
from django.utils import simplejson as json
import urllib, time, datetime, re
import logging
#import feedparser

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

# ---------- Datastore -------------------

class AccessToken(db.Model):#{{{
    page_id = db.IntegerProperty(required=True)
    user_token = db.StringProperty(required=True)
    page_token = db.StringProperty(required=True)
#}}}

class PostedNews(db.Model): #{{{
    news_id = db.IntegerProperty(required=True)
#}}}

# ----------------------------------------

# ---------- Functions -------------------
def fetch(url, data=None, retry=0):#{{{
    content = None
    retries = retry
    logging.debug('Fetching %s', url)
    while True:
        try:
            if data:
                response = urlfetch.fetch(url,
                        payload=urllib.urlencode(data), method=urlfetch.POST)
            else:
                response = urlfetch.fetch(url,deadline=60)

            if (response.status_code == 200):
                logging.debug('Fetching %s OK', url)
                content = response.content
                break
            else:
                raise urlfetch.DownloadError('Response code error')
        except:
            if retries > 0:
                logging.exception("Error while fetcing %s, will try again 1 seconds later", url)
                time.sleep(1)
                retries -= 1
            else:
                logging.exception("Error while fetcing %s", url)
                raise
                break
    return content#}}}

# ----------------------------------------

MAXNUM = 5

@route('/')#{{{
def action():
    return template('home')
#}}}

@route('/',method='POST')#{{{
def action():
    page_id = request.forms.get('page_id')
    user_token = request.forms.get('user_token')
    page_token = request.forms.get('page_token')

    logging.debug('page_id = %s, user_token = %s, page_token = %s',
            page_id, user_token, page_token)

    AccessToken(key_name = '1', page_id = long(page_id), user_token = user_token, page_token = page_token).put()
    return {'status' : True}
#}}}

@route('/fetch')#{{{
def action():
    key_names = []
    extracted = {}
    urls = (
        'http://news.ycombinator.com/',
        'http://xiaobin.net/proxy.php?url=http%3A%2F%2Fnews.ycombinator.com%2F', # Fallback
        'http://robhsiao.sinaapp.com/proxy.php?url=http%3A%2F%2Fnews.ycombinator.com%2F'
    )


    for index in xrange(len(urls)):
        try:
            content = fetch(urls[index])
            if content:
                break
            else:
                raise urlfetch.DownloadError('Response error')
        except urlfetch.DownloadError:
            if index >= len(urls):
                raise

    news = re.findall(r'<a\s+id=up_\d+(.+?)<tr\s+style="height:5px">', content, re.DOTALL)
    if not news: abort(500)

    cursor = 0
    max = min(MAXNUM, len(news));

    while cursor < max:
        url = title = id = None

        matches = re.search('title"><a\s+href="([^"]+?)".*?>(.+?)</a>', news[cursor], re.DOTALL)
        if (matches): url, title = matches.group(1,2)

        match = re.search('<a\shref="item\?id=(\d+)">', news[cursor], re.DOTALL)
        if (match): id = match.group(1)

        key_names.append(id)
        extracted[id] = {'url' : url, 'title' : title, 'id' : long(id)}
        cursor += 1

    rows = PostedNews.get_by_key_name(key_names)

    for index, row in enumerate(rows):
        story = extracted[key_names[index]]
        if not row:
            logging.debug('Add news story: %(id)s - %(title)s to queue', story)
            taskqueue.add(url='/publish', params=story)
        else:
            logging.debug('Ignore news story: %(id)s - %(title)s', story)
#}}}

@route('/publish', method='POST') #{{{ Task Queue worker
def action():
    id    = request.forms.get('id')
    title = request.forms.get('title')
    url   = request.forms.get('url')

    logging.info('Publish news story "%s" (id:%s)', title, id)

    cache_key = "access_token";
    page = memcache.get(cache_key)
    if not page:
        page = AccessToken.get_by_key_name('1')
        if not page:
            logging.error("No access_token found in datastore")
            abort(500)
        memcache.add(cache_key, page)

    if url.startswith('item?'):
        url = 'http://news.ycombinator.com/%s' % url


    # Shorten HN comment URL via bit.ly
    comment_url = 'http://news.ycombinator.com/item?id=%s' % id
    content = fetch('http://api.bitly.com/v3/shorten?login=robhsiao&apiKey=R_c5c51827c681f69a3e6d3831e77e1431&longUrl=%s&format=json'
            % urllib.quote_plus(comment_url), retry=3)
    if content:
        obj = json.loads(content)
        if (obj['status_code'] == 200):
            comment_url = obj['data']['url']

    logging.debug('Comment URL is: %s', comment_url)

    exist = PostedNews.get_by_key_name(id)
    if not exist:
        data = {'access_token' : page.page_token, 'link' : url, 'message' : "%s \n(Discuss on HN - %s)" % (title, comment_url) }
        content = fetch('https://graph.facebook.com/%s/links?access_token=%s' % (page.page_id, page.user_token), data, 3)
        if content:
            obj = json.loads(content)
            if 'id' in obj:
                logging.debug('News story "%s"(id:%s) was published successful', title, id)
                PostedNews(key_name=id, news_id = long(id)).put()
    else:
        logging.warn('News story "%s"(id:%s) was exists in datastore', title, id)
#}}}

@route('/tool/env')#{{{
def action():
    content = '<pre>'
    for key, value in request.environ.items():
        content += "%s => %s\n" % (key, value)
    content += '</pre>'
    return content
#}}}

@route('/tool/remove')#{{{ Flush all posted link
def action():
    page = memcache.get("access_token")
    if not page:
        page = AccessToken.get_by_key_name('1')
        if not page: abort(500)

    while True:
        content = fetch('https://graph.facebook.com/%s/links?access_token=%s' % (page.page_id, page.page_token), retry=3)
        if content:
            obj = json.loads(content)

            if not obj['data']:
                return "Done"

            for item in obj['data']:
                logging.debug(item['id'])
                content = fetch('https://graph.facebook.com/%s_%s?method=delete&access_token=%s'
                        % (page.page_id, item['id'], page.page_token))
                logging.debug(content)
#}}}

@route('/tool/url/:url#.+#')#{{{ Test fetch function on server
def action(url):
    if request.environ['QUERY_STRING']:
        url += '?' + request.environ['QUERY_STRING']
    return fetch(url, retry=5)
#}}}

#debug(True)
logging.getLogger().setLevel(logging.DEBUG)
run(server='gae')
