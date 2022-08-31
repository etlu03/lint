import ast
import os
import sys
import re
import collections
import string

from typing import NamedTuple as named_tuple

def extract(elts, res=[]):
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

class Exception(named_tuple):
  line: int
  txt: str
  msg: str
  expl: str

class Rule(ast.NodeVisitor):
  def __init__(self):
    self.exceptions = set()

class Linter:
  def __init__(self):
    self.rules = [Sets()]
    self.internal = Rule()
  
  @staticmethod
  def print_exception(file_name, rule=None):
    for line, txt, msg, expl in rule.exceptions:
      print('******************************')
      if(file_name): print('  File:     %s' % file_name)
      if     (line): print('  Line:     %d' % line)
      if      (txt): print('  Code:     %s' % txt)
      if      (msg): print('  Message:  %s' % msg)
      if     (expl): print('  Hint:     %s' % expl)

  def lint_version(self, file_name):
    major, minor = sys.version_info[:2]
    if(major < 3):
      exception = Exception(
                    msg='Parts of this linter may not work without Python 3',
                    txt='Consider upgrading to Python 3.'
      )

      self.internal.exceptions.add(exception)

    if(minor < 9):
      exception = Exception(
                    msg='Parts of this linter may not work without a modern Python',
                    txt='Consider upgrading to Python 3.9.'
      )

      self.internal.exceptions.add(exception)

  def lint_lines(self, file_name):
    with open(file_name, mode='rt', encoding='utf-8') as f:
      no = 1
      for line in f.readlines():
        if(79 < len(line)):
          exception = Exception(
                        line=no,
                        txt=line[:60].strip() + '...',
                        msg='Line width exceeds 80 characters',
                        expl='You may not have a line of code longer than 80 characters.'
          )

          self.internal.exceptions.add(exception)

        no += 1

  def run(self, source_path):
    file_name = os.path.basename(source_path)

    self.lint_version(file_name)
    self.lint_lines(file_name)

    self.rules.append(self.internal)    

    with open(source_path) as source_file:
      source_code = source_file.read()
    
    tree = ast.parse(source_code)
    
    for rule in self.rules:
      rule.visit(tree)
      self.print_exception(file_name, rule=rule)

class Sets(Rule):
  def visit_Set(self, node):
    res = list()
    extract(node.elts, res)
    result = ''.join(res); final = ''.join(delimit(result))
    if len(node.elts) != len(ast.literal_eval(final)):
      exception = Exception(
                    line=node.lineno,
                    txt=f'{final}',
                    msg='Set contains duplicate elements',
                    expl='Set may not explicitly be defined with duplicate elements'
      )
      self.exceptions.add(exception)

class Imports(Rule):
  def __init__(self):
    self.index = -1;

    super().__init__()

  def visit_Import(self, node):
    packages = node.names

    if self.index < node.lineno:
      if 3 < (node.lineno - self.index):
        exception = Exception(
                      line=None,
                      txt=None,
                      msg='Import statements are spread out too much',
                      expl='Declare imports at the top of every file'
        )

        self.exceptions.add(exception)

    self.index = node.lineno

    if 1 < len(packages):
      error = ', '.join([package.name for package in packages])
      exception = Exception(
                      line=node.lineno,
                      txt=f'import {error}',
                      msg='Import more than one module on a single line',
                      expl='Have only one import per line'
      )

      self.exceptions.add(exception)

class Naming(Rule):
  def __init__(self):
    self.VAR_STYLE = '[A-Z]|[@!#$%^&*()<>?/\|}{~:]'
    self.FUNC_STYLE = '[A-Z]|[@!#$%^&*()<>?/\|}{~:]'
    self.CLASS_STYLE = '[0-9]|[@_!#$%^&*()<>?/\|}{~:]'
    self.PACKAGE_STYLE = '[A-Z]|[0-9]|[@_!#$%^&*()<>?/\|}{~:]'

    self.default_expression = '{variable}={value}'

    super().__init__()

  def lint_args(self, node):
    arguments = node.args.args
    for arg in arguments:
      argument = arg.arg
      if re.search(self.VAR_STYLE, argument):
        defaults = node.args.defaults
        offset = len(arguments) - len(defaults)

        text = list()
        for index in range(len(arguments)):
          if index < offset:
            text.append(arguments[index].arg)
          else:
            text.append(self.default_expression.format(
                                      variable=arguments[index].arg, 
                                      value=str(defaults[index-offset].value)
                        )
            )

        statement = ', '.join(text)

        exception = Exception(
                      line=node.lineno,
                      txt=f'{node.name}({statement})',
                      msg='Function arguments do not follow PEP8 Standards',
                      expl='Review PEP8 style for argument definition'
        )

        self.exceptions.add(exception)
        break

  def visit_Name(self, node):
    if isinstance(node.ctx, ast.Store):
      name = node.id
      if re.search(self.VAR_STYLE, name):
        exception = Exception(
                      line=node.lineno,
                      txt=name,
                      msg='Variable does not follow PEP8 Standards',
                      expl='Review PEP8 style for for variable definition'
        )

        self.exceptions.add(exception)

    super().generic_visit(node)
  
  def visit_FunctionDef(self, node):
    name = node.name
    self.lint_args(node)
    if len(name) == 1:
      exception = Exception(
                    line=node.lineno,
                    txt=f'{name}()',
                    msg='Function name must be at least two characters long',
                    expl='Review PEP8 style for function definition'
      )
      
      self.exceptions.add(exception)

    if re.search(self.FUNC_STYLE, name):
      exception = Exception(
                    line=node.lineno,
                    txt=f'{name}()',
                    msg='Function name does not follow PEP8 Standards',
                    expl='Review PEP8 style for function definition'
      )

      self.exceptions.add(exception)

    super().generic_visit(node)
  
  def visit_ClassDef(self, node):
    name = node.name
    if len(name) < 2 or re.search(self.CLASS_STYLE, name):
      exception = Exception(
                    line=node.lineno,
                    txt=f'class {name}()',
                    msg='Class name does not follow PEP8 Standards',
                    expl='Review PEP8 style for class definition'
      )

      self.exceptions.add(exception)

    super().generic_visit(node)
  
  def visit_Import(self, node):
    packages = node.names
    if len(packages) == 1:
      alias = packages[0].asname
      
      if alias and re.search(self.PACKAGE_STYLE, alias):
        exception = Exception(
                    line=node.lineno,
                    txt=f'import {alias}',
                    msg='Alias name does not follow PEP8 Standards',
                    expl='Review PEP8 style for module importing'
        )
        
        self.exceptions.add(exception)

    super().generic_visit(node)

class VariableScopeUsage(Rule):
  def __init__(self):
    self.unused = collections.Counter()
    self.names = collections.Counter()

    super().__init__()

  def visit_Name(self, node):
    name = node.id

    if isinstance(node.ctx, ast.Store):
      if name not in self.names:
        self.names[name] = node
      
      if name not in self.unused:
        self.unused[name] = True
    else:
      self.unused[name] = False

class Variable(Rule):
  def lint_variables(self, node):
    visitor = VariableScopeUsage()
    visitor.visit(node)

    for name, unused in visitor.unused.items():
      if unused:
        node = visitor.names[name]
        exception = Exception(
                      line=node.lineno,
                      text=f'The variable {node} has not been used',
                      msg='Unused variable',
                      expl='Your previously defined variable has not been used'
        )

        self.exceptions.add(exception)
  
  def visit_FunctionDef(self, node):
    self.lint_variables(node)

    super().generic_visit(node)

  def visit_ClassDef(self, node):
    self.lint_variables(node)

    super().generic_visit(node)
  
  def visit_Module(self, node):
    self.lint_variables(node)

    super().generic_visit(node)

if __name__ == '__main__':
  source_path = sys.argv[1]

  linter = Linter()

  print('Linting...')
  linter.run(source_path)