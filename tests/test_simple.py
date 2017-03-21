#!/usr/bin/env python3

from nose.tools import eq_
from resumable import rebuild, value


def test_simple():
    @rebuild
    def function(original):
        return value(original.upper())

    original = 'hello'

    original = function['function'](original)

    eq_(original, 'HELLO')


def test_nested():
    @rebuild
    def first(a):
        @rebuild
        def second(b):
            return value(b + 'b')
        return value(second['second'](a))

    original = 'ba'

    original = first['first'](original)

    eq_(original, 'bab')


if __name__ == '__main__':
    test_simple()
