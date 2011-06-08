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
import os
import facebook
import logging

class AccessToken(db.Model):
    page_id = db.IntegerProperty(required=True)
    access_token = db.StringProperty(required=True)

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
        self.write(type(self.request.get('page_id')))
        access_token = self.request.get('access_token')
        if (page_id and access_token):
            AccessToken(
                key_name = 'page_id',
                page_id = page_id,
                access_token = access_token
            ).put()

class ListHandler(BaseHandler):
    def get(self):
        for i in AccessToken.all():
            self.write(i.access_token)

def main():
    application = webapp.WSGIApplication([
        ('/', HomeHandler),
        ('/list', ListHandler),
        ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    main()
