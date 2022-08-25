import ast
import os
import sys
import re
import collections

from typing import NamedTuple as named_tuple

class Exception(named_tuple):
  line: int
  txt: str
  msg: str
  expl: str

  def unpack(self):
    return self.line, self.txt, self.msg, self.expl

class Rule(ast.NodeVisitor):
  def __init__(self):
    self.exceptions = set()

class Linter:
  def __init__(self):
    self.rules = set()
  
  @staticmethod
  def print_exception(rule, file_name):
    for line, txt, msg, expl in rule.exceptions:
      print('******************************')
      if(file_name): print('  File:     %s' % file_name)
      if     (line): print('  Line:     %d' % line)
      if      (txt): print('  Code:     %s' % txt)
      if      (msg): print('  Message:  %s' % msg)
      if     (expl): print('  Hint:     %s' % expl)

  @staticmethod
  def internal_print(exception, file_name):
    line, txt, msg, expl = exception.unpack()
    print('******************************')
    if(file_name): print('  File:     %s' % file_name)
    if     (line): print('  Line:     %d' % line)
    if      (txt): print('  Code:     %d' % txt)
    if      (msg): print('  Message:  %s' % msg)
    if     (expl): print('  Hint:     %s' % expl)
  
  def lint_version(self, file_name):
    major, minor = sys.version_info[:2]
    if(major < 3):
      exception = Exception(
                    msg='Parts of this linter may not work without Python 3',
                    txt='Consider upgrading to Python 3.'
      )
      self.internal_print(exception, file_name)
    if(minor < 9):
      exception = Exception(
                    msg='Parts of this linter may not work without a modern Python',
                    txt='Consider upgrading to Python 3.9.'
      )
      self.internal_print(exception, file_name)

  def lint_lines(self, file_name):
    with open(file_name, mode='rt', encoding='utf-8') as f:
      no = 1
      for line in f.readlines():
        if(80 < len(line)):
          exception = Exception(
                        line=no,
                        txt=line[:78] + '...',
                        msg='Line width exceeds 80 characters',
                        expl='You may not have a line of code longer than 80 characters.'
          )
          self.internal_print(exception, file_name)
        no += 1

  def run(self, source_path):
    file_name = os.path.basename(source_path)

    self.lint_version(file_name)
    self.lint_lines(file_name)

    with open(source_path) as source_file:
      source_code = source_file.read()
    
    tree = ast.parse(source_code)
    
    for rule in self.rules:
      rule.visit(tree)
      self.print_exception(rule, file_name)

class Sets(Rule):
  def visit_Set(self, node):
    seen_values = set()
    for elem in node.elts:
      if not isinstance(elem, ast.Constant):
        continue

      val = elem.value
      if val in seen_values:
        values = ', '.join([str(elem.value) for elem in node.elts if isinstance(elem, ast.Constant)])
        exception = Exception(
                      line=elem.lineno,
                      txt='{' + f'{values}' + '}',
                      msg='Set contains duplicate elements',
                      expl='Set may not explicitly be defined with duplicate elements'
        )
        self.exceptions.add(exception)
        break
      else:
        seen_values.add(val)

class Naming(Rule):
  def __init__(self):
    self.VAR_STYLE = '[A-Z]|[@!#$%^&*()<>?/\|}{~:]'
    self.FUNC_STYLE = '[A-Z]|[@!#$%^&*()<>?/\|}{~:]'
    self.CLS_STYLE = '[0-9]|[@_!#$%^&*()<>?/\|}{~:]'
    self.MOD_STYLE = '[A-Z]|[0-9]|[@_!#$%^&*()<>?/\|}{~:]'
    self.PACK_STYLE = '[A-Z]|[0-9]|[@_!#$%^&*()<>?/\|}{~:]'
    super().__init__()

  def lint_args(self, func, node):
    arguments = node.args.args
    for arg in arguments:
      argument = arg.arg
      if re.search(self.VAR_STYLE, argument):
        args = ', '.join([arg.arg for arg in arguments])
        exception = Exception(
                      line=node.lineno,
                      txt='{name!r}',
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
    self.lint_args(name, node)
    if len(name) < 2 or re.search(self.FUNC_STYLE, name):
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
    if len(name) < 2 or re.search(self.CLS_STYLE, name):
      exception = Exception(
                    line=node.lineno,
                    txt=f'class {name}',
                    msg='Class name does not follow PEP8 Standards',
                    expl='Review PEP8 style for class definition'
      )
      self.exceptions.add(exception)
    super().generic_visit(node)
  
  def visit_Import(self, node):
    name = node.name
    if len(name) < 2 or re.search(self.MOD_STYLE, name):
      exception = Exception(
                    line=node.lineno,
                    txt='{name!r}',
                    msg='Imported module does not follow PEP8 Standards',
                    expl='Review PEP8 style for modules'
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
                      text='The variable {node!r} has not been used',
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
  linter.rules.add(Sets())
  linter.rules.add(Naming())
  
  print('Linting...')
  linter.run(source_path)