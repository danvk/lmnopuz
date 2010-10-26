# This is a Python/App Engine port of "DHTML Crossword Server", written in Ruby
# by Evan Martin and Dan Erat.
# Copyright (C) 2010 Dan Vanderkam <danvdk@gmail.com>
# http://github.com/danvk/lmnopuz

__author__ = 'danvdk@gmail.com (Dan Vanderkam)'

import datetime
import googtmpl
import logging
import os
import re
import crossword
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


# General structure:
# SessionState
#   [Cell]
#   [Roster]
#   [Message]
class SessionState(db.Model):
  # .key() = session_id
  start_time = db.DateTimeProperty(auto_now=True)
  crossword = db.ReferenceProperty(CrosswordStore)
  name = db.StringProperty()


class Cell(db.Model):
  session = db.ReferenceProperty(SessionState)
  x = db.IntegerProperty(required=True)
  y = db.IntegerProperty(required=True)
  guess = db.BooleanProperty(default=False)
  user = db.UserProperty()
  last_updated = db.DateTimeProperty(auto_now=True)


class Roster(db.Model):
  session = db.ReferenceProperty(SessionState)
  user = db.UserProperty()
  color = db.StringProperty()
  cursor_x = db.IntegerProperty()
  cursor_y = db.IntegerProperty()


class Message(db.Model):
  session = db.ReferenceProperty(SessionState)
  user = db.UserProperty()
  time = db.DateTimeProperty(auto_now=True)
  text = db.StringProperty()



def GetTemplate(name):
  # TODO(danvk): cache templates?
  path = os.path.dirname(__file__) + "/templates/" + name
  return googtmpl.Template().parse(open(path, "r").read())


def ServeTemplatedPage(response, title, letters, depth, filename, data):
  csspath = '../' * depth + 'static/site.css'
  content = GetTemplate(filename).render(data)
  # head['Content-type'] = 'text/html'
  vals = {
    'title': title,
    'letters': [{'l': let} for let in letters],
    'css': csspath,
    'content': content
  }
  response.out.write(GetTemplate('page.tmpl').render(vals))


class PuzzlePage(webapp.RequestHandler):
  """Serves /crossword/, /crossword/<key>/ and /crossword/<key>/crossword.js"""
  def get(self):
    if self.request.path == '/crossword':
      self.redirect('/crossword/')
      return

    parts = self.request.path.split('/')
    del parts[0:2]  # '' and 'crossword'

    if parts[0] == '':
      # Return a list of all puzzles.
      puzzles = CrosswordStore.all().order("-upload_time").fetch(100)
      ServeTemplatedPage(
          self.response, 'Choose Crossword', 'CROSSWORDS', 1,
          'crosswordlist.tmpl',
          {
            'crossword': [
              {
                'title': c.title,
                'url': '/crossword/%s/' % c.key()
              }
            for c in puzzles]
          })
    else:
      key = parts[0]
      del parts[0]
      puz = CrosswordStore.get(key)
      assert puz

      if parts[0] == '':
        logging.info("Serving crossword page for %s" % key)
        # This page contains all the UI bits. It requests "crossword.js".
        self.response.out.write(GetTemplate('crossword.tmpl').render({
          'multiplayer': False
        }))
      elif parts[0] == 'crossword.js':
        # Serve up crossword JSON.
        # TODO(danvk): set response type to text/javascript
        json = crossword.Convert(puz.data).ToJSON()
        self.response.out.write("var Crossword = " + json + ";")


class UploadHandler(webapp.RequestHandler):
  def post(self):
    """Store a new puzzle file in the DB"""
    logging.info("UploadHandler")
    x = self.request.get('puz')
    c = crossword.Crossword.FromString(x)

    logging.info("Title: %s" % c.title)
    logging.info("Author: %s" % c.author)
    logging.info("Copyright: %s" % c.copyright)

    # TODO(danvk): get the filename
    puz = CrosswordStore(data=x, title=c.title)
    if c.author: puz.author = c.author
    if c.copyright: puz.copyright = c.copyright

    db.put(puz)
    logging.info("Stored %s in DB" % c.title)

    self.redirect('/')


class FrontPage(webapp.RequestHandler):
  def get(self):
    num_puz = CrosswordStore.all().count()
    ServeTemplatedPage(self.response, 'lmnopuz', 'LMNOPUZ', 0,
                       'frontpage.tmpl',
                       { 'numcrosswords': num_puz,
                         'multi': False
                       })


application = webapp.WSGIApplication([
  ('/', FrontPage),
  ('/crossword.*', PuzzlePage),
  ('/uploadpuz', UploadHandler),
], debug=True)

run_wsgi_app(application)
