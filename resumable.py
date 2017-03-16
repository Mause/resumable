import ast
import inspect
import warnings
import linecache
from uuid import uuid4
from textwrap import dedent
from collections import OrderedDict
from astmonkey.transformers import ParentNodeTransformer
from astmonkey.visitors import SourceGeneratorNodeVisitor


def split(func, name=None):
    return func, name


def get_sub(lst, pred):
    for subnode in lst:
        if pred(subnode):
            lst.remove(subnode)
            return subnode


class ToSource(SourceGeneratorNodeVisitor):
    '''
    The changes in here are primarily to patch
    around differences between python versions
    (I've tested with Python 3.5)
    '''

    @classmethod
    def to_source(cls, node):
        generator = cls('    ')
        generator.visit(node)
        return ''.join(generator.result)

    def visit_Call(self, node):
        node.starargs = get_sub(
            node.args,
            lambda t: isinstance(t, ast.Starred)
        )
        node.kwargs = get_sub(
            node.keywords,
            lambda t: t.arg is None
        )
        return super().visit_Call(node)

    def visit_Lambda(self, node):
        # until i can get the ast compiling directly,
        # we need to make sure precendence is correct
        self.write('(')
        super().visit_Lambda(node)
        self.write(')')

    def signature(self, node):
        if node.vararg:
            node.vararg = node.vararg.arg
        if node.kwarg:
            node.kwarg = node.kwarg.arg
        return super().signature(node)


class Visitor(ast.NodeVisitor):

    def __init__(self):
        self.parts = {}
        self.current = None
        self.name = None
        self.last_idx = -1

    def visit_FunctionDef(self, node):
        self.current = self.parts[node] = OrderedDict()
        self.name = node.name
        self.args = node.args
        return super().generic_visit(node)

    def function_from(self, name, args, body, lineno):
        func = ast.FunctionDef(
            name=name,
            args=args,
            body=body,
            decorator_list=[],
            returns=None
        )
        func.lineno = lineno
        return func

    def visit_Call(self, node):
        if getattr(node.func, 'id', None) == 'split':
            # this is the expression that contains the call,
            # or basically the value of the assignment/return
            expr = node.parent
            user = expr.parent  # by user we mean user of the value

            # it's possible more are actually supported,
            # but i'm hesitant to just allow them without
            # further testing
            if not isinstance(user, (ast.Return, ast.Assign)):
                warnings.warn('This is untested')

            # sanity checking
            assert user.parent_field == 'body', user.parent_field
            assert isinstance(user.parent, ast.FunctionDef)

            field = getattr(user.parent, user.parent_field)
            body = field[self.last_idx + 1:user.parent_field_index]

            value = user.value
            value.func = value.func.args[0]  # remove call to split
            body.append(ast.Return(value))
            body[-1].lineno = value.lineno

            self.current[self.name] = self.function_from(
                self.name, self.args, body, value.lineno
            )

            self.last_idx = user.parent_field_index

            name = node.args[1].s if len(node.args) == 2 else None
            self.name = name
            self.args = self.get_args(user, name)

        return super().generic_visit(node)

    def get_args(self, user, name):
        msg = 'have a name, on line {} of function {}'.format(
            user.lineno,
            user.parent.name
        )

        if isinstance(user, ast.Return):
            if name is not None:
                raise Exception('A closing split cannot {}'.format(msg))
        else:
            if name is None:
                raise Exception('A non-closing split must {}'.format(msg))

        args = []
        if isinstance(user, ast.Assign):
            target = user.targets[0]
            names = target.elts if isinstance(target, ast.Tuple) else [target]
            args = [ast.arg(name.id, None) for name in names]

        return ast.arguments(
            args=args,
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[]
        )


def cache_code(node):
    filename = '<ast_{}>'.format(uuid4().hex)
    source = ToSource.to_source(node)

    lines = [line + '\n' for line in source.splitlines()]
    linecache.cache[filename] = len(source), None, lines, filename
    assert filename in linecache.cache

    return filename


def extract(env, node, name):
    loc = dict(env)
    filename = cache_code(node)

    node = ast.Module(body=[node])
    node = ast.fix_missing_locations(node)

    code = compile(node, filename=filename, mode='exec')
    exec(code, loc, loc)
    return loc[name]


def rebuild(function):
    assert callable(function)
    lines, lineno = inspect.getsourcelines(function)

    lines = ''.join(lines)
    lines = dedent(lines)
    lines = '\n' * (lineno - 1) + lines

    root, = ast.parse(lines).body
    root = ParentNodeTransformer().visit(root)

    visitor = Visitor()
    visitor.visit(root)
    parts = visitor.parts[root]

    return OrderedDict(
        (name, extract(function.__globals__, node, name))
        for name, node in parts.items()
    )
