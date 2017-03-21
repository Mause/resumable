#!/usr/bin/env python3

from nose.tools import eq_
from resumable import rebuild, split


def test_simple():
    @rebuild
    def function(original):
        return split(str.upper)(original)

    original = 'hello'

    original = function['function'](original)

    eq_(original, 'HELLO')


def test_value():
    @rebuild
    def function(original):
        return value(original + ' world')

    original = 'hello'

    original = function['function'](original)

    eq_(original, 'hello world')


def test_nested():
    @rebuild
    def first(a):
        @rebuild
        def second(b):
            return split(lambda s: s + 'b')(b)
        return split(second['second'])(a)

    original = 'ba'

    original = first['first'](original)

    eq_(original, 'bab')


if __name__ == '__main__':
    test_simple()
