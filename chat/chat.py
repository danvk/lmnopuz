#!/usr/bin/python2.4
#
# Copyright 2010 Dan Vanderkam (danvdk@gmail.com)
#
# Plan:
# - factor out "broadcast" routine
# - add support for "rooms"
# - deploy and test w/ actual hanging connections

"""Simple Chat application

This app is a way for me to play around with app engine's Channel API before
attempting to implement a puzzle server using it.
"""

import datetime
import logging
import os
from django.utils import simplejson
from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

# ActiveUsers.user.user_id winds up getting used as the channel token.
class ActiveUsers(db.Model):
  user = db.UserProperty()
  last_update_time = db.DateTimeProperty(auto_now=True)

class ChatLine(db.Model):
  user = db.UserProperty(required=True)
  time = db.DateTimeProperty(auto_now=True)
  text = db.StringProperty(required=True)

class MainPage(webapp.RequestHandler):
  def get(self):
    logging.info("MainPage")
    user = users.get_current_user()
    if user:
      nick = user.nickname()
      logging.info("Registering user: " + nick)
      user_data = ActiveUsers.get_or_insert(user.user_id(), user=user)

      logging.info("Create channel: " + nick)
      channel_token = channel.create_channel(user.user_id())
      lines = ChatLine.all().order("-time").fetch(10)
      vals = {
        'channel_id': channel_token,
        'nickname': nick,
        'lines': '\n'.join(reversed(["%s: %s" % (line.user.nickname(), line.text) for line in lines]))
      }
      path = os.path.dirname(__file__) + "/index.html"
      self.response.out.write(template.render(path, vals))
    else:
      logging.info("redirect")
      self.redirect(users.create_login_url(self.request.url))

class ReceiveChat(webapp.RequestHandler):
  def post(self):
    user = users.get_current_user()
    if not user:
      self.response.set_status(401)
      return

    text = self.request.get("text")
    line = ChatLine(user=user, text=text)
    db.put(line)

    # Send an update to everyone who's listening.
    # TODO(danvk): write a function to do this.
    msg = { 'lines': [ "%s: %s" % (user.nickname(), text) ] }
    active_users=db.GqlQuery("SELECT * FROM ActiveUsers")
    for user in active_users:
      if (datetime.datetime.now() - user.last_update_time
          > datetime.timedelta(hours=1)):
        logging.info("Removing inactive user: " + user.user.nickname())
        user.delete()
      else:
        logging.info("Sending message on channel: " + user.user.user_id())
        try:
          channel.send_message(user.user.user_id(), simplejson.dumps(msg))
        except channel.InvalidChannelKeyError:
          # This happens when you restart the server and sever connections.
          pass

    self.response.out.write('ok')


application = webapp.WSGIApplication([
  ('/', MainPage),
  ('/chat', ReceiveChat)
], debug=True)

run_wsgi_app(application)
