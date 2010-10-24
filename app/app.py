# This is a Python/App Engine port of "DHTML Crossword Server", written in Ruby
# by Evan Martin and Dan Erat.
# Copyright (C) 2010 Dan Vanderkam <danvdk@gmail.com>
# http://github.com/danvk/lmnopuz

__author__ = 'danvdk@gmail.com (Dan Vanderkam)'

import datetime
import logging
import os
import re
from crossword import Crossword
from django.utils import simplejson
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# Raw .puz data from users.
class CrosswordStore(db.Model):
  user = db.UserProperty()
  upload_time = db.DateTimeProperty(auto_now=True)
  filename = db.StringProperty()
  data = db.BlobProperty(required=True)

  # A few bits from the parsed PUZ file for easier browsing.
  title = db.TextProperty(required=True)
  author = db.TextProperty()
  copyright = db.TextProperty()

class PuzzleListPage(webapp.RequestHandler):
  def get(self):
    logging.info("PuzzlePage: %s" % self.request.path)
    puzzles = CrosswordStore.all().order("-upload_time").fetch(100)
    path = os.path.dirname(__file__) + "/puzzles.html"
    vals = {
      'puzzles': puzzles
    }
    self.response.out.write(template.render(path, vals))

class PuzzlePage(webapp.RequestHandler):
  def get(self):
    m = re.match(r'/crossword/(.*)', self.request.path)
    assert m
    key = m.group(1)
    puz = CrosswordStore.get(key)
    assert puz
    path = os.path.dirname(__file__) + "/puzzle_page.html"
    vals = {
      'c': puz
    }
    self.response.out.write(template.render(path, vals))

class UploadHandler(webapp.RequestHandler):
  def post(self):
    """Store a new puzzle file in the DB"""
    logging.info("UploadHandler")
    x = self.request.get('puz')
    c = Crossword.FromString(x)

    logging.info("Title: %s" % c.title)
    logging.info("Author: %s" % c.author)
    logging.info("Copyright: %s" % c.copyright)

    # TODO(danvk): get the filename
    puz = CrosswordStore(data=x, title=c.title)
    if c.author: puz.author = c.author
    if c.copyright: puz.copyright = c.copyright

    db.put(puz)
    logging.info("Stored %s in DB" % c.title)

    self.redirect('/crossword')


application = webapp.WSGIApplication([
  ('/crossword', PuzzlePage),
  ('/crossword/.*', PuzzlePage),
  ('/uploadpuz', UploadHandler),
], debug=True)

run_wsgi_app(application)
