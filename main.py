#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template
from google.appengine.api import urlfetch
import os
import logging
import urllib
import time

class AccessToken(db.Model):
    page_id = db.IntegerProperty(required=True)
    user_token = db.StringProperty(required=True)
    page_token = db.StringProperty(required=True)

class NewsItem(db.Model):
    id = db.IntegerProperty(required=True)

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
                key_name = 'page_id',
                page_id = page_id,
                user_token = user_token,
                page_token = page_token,
            ).put()

class UpdateHandler(BaseHandler):
    def get(self):
        for i in AccessToken.all():
            data = urllib.urlencode({
                'access_token' : i.page_token,
                'link' : 'http://www.google.com/',
                'message' : time.time()
            })
            self.write(urlfetch.fetch(
                #'https://graph.facebook.com/178568815531741/links?access_token=' + i.user_token,
                'https://graph.facebook.com/178568815531741/links',
                payload=data,
                method=urlfetch.POST,
            ).content)

def main():
    application = webapp.WSGIApplication([
        ('/', HomeHandler),
        ('/update', UpdateHandler),
        ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main()
