import re

class Template:
  PLAIN_TEXT = 1
  VARIABLE = 2
  GROUP = 3

  def __init__(self):
    pass

  def parse(self, tmpl):
    parts = re.split(r'(\{\{[#/][^#/}]+\}\})', tmpl)
    stack = [[]]
    tag_stack = []

    for part in parts:
      m = re.match(r'\{\{([#/]?)([^#\}]+)\}\}', part)
      if not m:
        # This is plain text.
        stack[-1].append((Template.PLAIN_TEXT, part, None))
        continue

      if m.group(1) == '':
        # Plain variable
        stack[-1].append((Template.VARIABLE, m.group(2), None))
      elif m.group(1) == '#':
        # Start of a group/conditional
        tag_stack.append(m.group(2))
        stack.append([])
      elif m.group(1) == '/':
        # End of a group/conditional
        if 0 == len(tag_stack): return False
        if m.group(2) != tag_stack[-1]: return False
        back = stack.pop()
        stack[-1].append((Template.GROUP, tag_stack[-1], back))
        tag_stack.pop()

    if 0 != len(tag_stack) or 1 != len(stack):
      return False

    self.parsed = stack[0]
    return True

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
          out += dict[content]
      elif type == Template.GROUP:
        if content in dict:
          val = dict[content]
          assert not hasattr(val, 'lower'), 'Expected boolean, dict or array of dicts but got string (%s)' % content
          if hasattr(val, 'keys'):
            # It's a hash
            out += Template._render(inside, val)
          elif val == True:
            # Just expand with an empty dictionary.
            out += Template._render(inside, {})
          else:
            # It's got to be an array.
            for v in val:
              out += Template._render(inside, v)

    return out
