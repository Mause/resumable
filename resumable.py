import ast
import inspect
import linecache
from uuid import uuid4
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

    def visit_Call(self, node):
        if getattr(node.func, 'id', None) == 'split':
            if len(node.args) == 2:
                name = node.args[1].s
            else:
                name = None

            # this is the expression that contains the call,
            # or basically the value of the assignment/return
            expr = node.parent
            user = expr.parent

            # it's possible more are actually supported,
            # but i'm hesitant to just allow them without
            # further testing
            assert isinstance(user, (ast.Return, ast.Assign))

            # sanity checking
            assert user.parent_field == 'body', user.parent_field
            assert isinstance(user.parent, ast.FunctionDef)

            field = getattr(user.parent, user.parent_field)
            body = field[self.last_idx + 1:user.parent_field_index]

            value = user.value
            value.func = value.func.args[0]  # remove call to split
            body.append(ast.Return(value))

            self.current[self.name] = ast.FunctionDef(
                name=self.name,
                args=self.args,
                body=body,
                decorator_list=[],
                returns=[]
            )

            self.last_idx = user.parent_field_index
            self.name = name
            self.args = self.get_args(user, name)

        return super().generic_visit(node)

    def get_args(self, user, name):
        lineno = user.lineno

        if isinstance(user, ast.Return):
            if name is not None:
                raise Exception('A closing split cannot have a name {}'.format(lineno))
        else:
            if name is None:
                raise Exception('A non-closing split must have a name {}'.format(lineno))

        args = (
            []
            if isinstance(user, ast.Return)
            else
            [ast.arg(user.targets[0].id, None)]
        )

        return ast.arguments(
            args=args,
            vararg=None,
            kwarg=None,
            defaults=[]
        )


def extract(env, node, name):
    loc = dict(env)
    filename = '<ast_{}>'.format(uuid4().hex)
    source = ToSource.to_source(node)

    print(source)

    lines = [line + '\n' for line in source.splitlines()]
    linecache.cache[filename] = len(source), None, lines, filename
    assert filename in linecache.cache

    code = compile(source, filename=filename, mode='exec')
    exec(code, loc, loc)
    return loc[name]


def rebuild(function):
    assert callable(function)
    root, = ast.parse(inspect.getsource(function)).body
    root = ParentNodeTransformer().visit(root)

    visitor = Visitor()
    visitor.visit(root)
    parts = visitor.parts[root]

    return OrderedDict(
        (name, extract(function.__globals__, node, name))
        for name, node in parts.items()
    )
