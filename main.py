#!/usr/bin/env python
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.api import urlfetch, mail
from django.utils import simplejson as json
import os
import logging
import urllib
import time
import re

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

class AccessToken(db.Model):
    page_id = db.IntegerProperty(required=True)
    user_token = db.StringProperty(required=True)
    page_token = db.StringProperty(required=True)

class PostedNews(db.Model):
    news_id = db.IntegerProperty(required=True)
    page_id = db.IntegerProperty(required=True)

class BaseHandler(webapp.RequestHandler):
    def render(self, file, vars=None):
        self.write(template.render(
                    os.path.join(os.path.dirname(__file__),
                        'template',
                        "%s.html" % file), vars))
    def write(self, str):
        self.response.out.write(str)

class HomeHandler(BaseHandler):
    def get(self):
        #for name in os.environ.keys():
        #    self.response.out.write("%s = %s<br />\n" % (name, os.environ[name]))
        self.render('home')

    def post(self):
        page_id = int(self.request.get('page_id'))
        user_token = self.request.get('user_token')
        page_token = self.request.get('page_token')
        logging.debug(page_token)
        logging.debug(user_token)
        logging.debug(page_id)
        if (page_id and user_token and page_token):
            AccessToken(
                key_name = str(page_id),
                page_id = page_id,
                user_token = user_token,
                page_token = page_token,
            ).put()

class UpdateHandler(BaseHandler):
    def get(self):
        self.fetch_news()
        if not self.news:
            self.alert('No news item found')
            return

        shorted = {}
        counter = 0
        for page in AccessToken.all():
            for url, subject, id in self.news:

                item = PostedNews.gql(
                        'WHERE  news_id = :news_id AND page_id = :page_id',
                        news_id = id,
                        page_id = page.page_id
                ).get()

                if item:
                    logging.debug('Ignore %s',id)
                    continue

                counter += 1

                if (counter > 3):
                    return

                if url.startswith('item?'):
                    url = 'http://news.ycombinator.com/%s' % url

                comment_url = 'http://news.ycombinator.com/item?id=%s' % id

                if id in shorted:
                    comment_url = shorted[id]
                else:
                    bitly = 'http://api.bitly.com/v3/shorten?login=robhsiao&apiKey=R_c5c51827c681f69a3e6d3831e77e1431&longUrl=%s&format=json' % urllib.quote_plus(comment_url)
                    response = urlfetch.fetch(bitly)
                    if (response.status_code == 200):
                        obj = json.loads(response.content)
                        if (obj['status_code'] == 200):
                            comment_url = obj['data']['url']
                            shorted[id] = comment_url

                data = urllib.urlencode({
                    'access_token' : page.page_token,
                    'link' : url,
                    'message' : "%s (Discuss on HN - %s)" % (subject, comment_url)
                })

                response = urlfetch.fetch(
                    'https://graph.facebook.com/%s/links?access_token=%s' % (page.page_id, page.user_token),
                    payload=data,
                    method=urlfetch.POST,
                )

                logging.debug(response.content)
                if (response.status_code == 200):
                    obj = json.loads(response.content)
                    if 'id' in obj:
                        logging.info('Post: %s', obj['id'])
                        PostedNews(
                                page_id = page.page_id,
                                news_id = id
                        ).put()

    def test(self):
        for i in AccessToken.all():
            data = urllib.urlencode({
                'access_token' : i.page_token,
                'link' : 'http://the-paper-trail.org/blog/?page_id=152',
                'message' : time.time()
            })
            self.write(urlfetch.fetch(
                #'https://graph.facebook.com/178568815531741/links?access_token=' + i.user_token,
                'https://graph.facebook.com/178568815531741/links',
                payload=data,
                method=urlfetch.POST,
            ).content)

    # fetch the latest news
    def fetch_news(self):
        self.news = []

        response = urlfetch.fetch('http://news.ycombinator.com/')
        logging.debug('Response code: %d', response.status_code)

        if (response.status_code != 200):
            self.alert("Error reponse while requesting")
            return

        matches = re.findall(r'<a\s+id=up_\d+(.+?)<tr\s+style="height:5px">', \
                response.content, re.DOTALL)

        if not matches:
            self.alert("Can't find any items")
            return

        count = 0
        for item in matches:
            count += 1
            if (count > 10):
                break
            url = subject = id = None
            match = re.search('title"><a\s+href="([^"]+?)".*?>(.+?)</a>', item, re.DOTALL)
            if (match):
                url, subject = match.group(1,2)

            match = re.search('<a\shref="item\?id=(\d+)">', item, re.DOTALL)
            if (match):
                id = match.group(1)
            self.news.append((url, subject, long(id)))

    # send email alert
    def alert(self,msg):
        logging.error(msg)
        message = mail.EmailMessage(
                to = "robin@xiaobin.net",
                subject = "[HackerNewsBot] %s" % msg)
        message.send()

class TestHandler(UpdateHandler):
    def get(self):
        self.fetch_news()
        for url, subject, id in self.news:
            self.write("<a href=%s>%s</a><br>" % (url, subject))
def main():
    application = webapp.WSGIApplication([
        ('/', HomeHandler),
        ('/update', UpdateHandler),
        ('/test', TestHandler),
        ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main()
