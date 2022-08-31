import ast
import string

def extract(elts, res):
  for elem in elts:
    if isinstance(elem, ast.Tuple):
      res.append('(')
      extract(elem.elts, res)
      res.append(')')
    elif isinstance(elem, ast.Constant):
      res.append(str(elem.value))

def delimit(res):
  delimited = ['{']
  for i in range(0, len(res) - 1):
    if (res[i] in string.digits and res[i + 1] in string.digits) \
        or res[i] == ')':
      delimited.append(str(res[i]) + ', ')
    else:
      delimited.append(str(res[i]))
  delimited.append(res[-1])
  delimited.append('}')
  return delimited