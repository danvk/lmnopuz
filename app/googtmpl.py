import cgi
import json
import re
import logging

class Template:
  PLAIN_TEXT = 1
  VARIABLE = 2
  GROUP = 3

  def parse(self, tmpl):
    parts = re.split(r'(\{\{[^\}]+\}\})', tmpl)
    stack = [[]]
    tag_stack = []

    for part in parts:
      m = re.match(r'\{\{([#/]?)([^#\:}]+)(:[jhr])?\}\}', part)
      if not m:
        # This is plain text.
        stack[-1].append((Template.PLAIN_TEXT, part, None))
        continue

      var = m.group(2).lower()  # We want lower-case dict keys.

      if m.group(1) == '':
        # Plain variable
        stack[-1].append((Template.VARIABLE, var, m.group(3)))
      elif m.group(1) == '#':
        # Start of a group/conditional
        tag_stack.append(var)
        stack.append([])
      elif m.group(1) == '/':
        # End of a group/conditional
        if 0 == len(tag_stack):
          logging.error('Popping empty tag stack')
          return False
        if var != tag_stack[-1]:
          logging.error('Open/close tag mismatch: %s vs. %s' % (var, tag_stack[-1]))
          return False
        back = stack.pop()
        stack[-1].append((Template.GROUP, tag_stack[-1], back))
        x = tag_stack.pop()
      else:
        assert False, 'Weird tag: %s' % part


    if 0 != len(tag_stack) or 1 != len(stack):
      logging.error('Non-empty tag stack (%s) or len(stack)=%d>1' % (
                      ','.join(tag_stack), len(stack)))
      return False

    self.parsed = stack[0]
    return self  # support t = Template().parse(...)

  def render(self, dict):
    return Template._render(self.parsed, dict)

  @staticmethod
  def _render(data, dict):
    out = ""
    for type, content, inside in data:
      if type == Template.PLAIN_TEXT:
        out += content
      elif type == Template.VARIABLE:
        if content in dict:
          if inside == ':j':
            # TODO(danvk): don't think this is quite right.
            out += json.dumps(str(dict[content]))
          elif inside == ':h':
            out += cgi.escape(str(dict[content]))
          elif inside == ':r':
            out += str(dict[content])
          elif inside == None:
            out += cgi.escape(str(dict[content]))
          else:
            assert False, "Invalid variable escape: %s" % inside
      elif type == Template.GROUP:
        if content in dict:
          val = dict[content]
          assert not hasattr(val, 'lower'), 'Expected boolean, dict or array of dicts but got string (%s)' % content
          if hasattr(val, 'keys'):
            # It's a hash
            out += Template._render(inside, val)
          elif hasattr(val, 'append'):
            # It's got to be an array.
            for v in val:
              out += Template._render(inside, v)
          elif val:
            # Just expand with an empty dictionary.
            out += Template._render(inside, {})

    return out
