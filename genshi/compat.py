# -*- coding: utf-8 -*-
#
# Copyright (C) 2006-2009 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://genshi.edgewall.org/wiki/License.
#
# This software consists of voluntary contributions made by many
# individuals. For the exact contribution history, see the revision
# history and logs, available at http://genshi.edgewall.org/log/.

# The add_metaclass and exec_ functions in this module were copied
# from 'six' version 1.17.0 (https://github.com/benjaminp/six/blob/main/six.py).
# and are copyrighted under the following license:
#
# Copyright (c) 2010-2024 Benjamin Peterson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Various Python version compatibility classes and functions."""

try:
    # in Python 3.9 the "_ast" module does not provide "Index" anymore but
    # "ast" does.
    import ast
except ImportError:
    import _ast as ast
import sys
import warnings
from types import CodeType

IS_PYTHON2 = (sys.version_info[0] == 2)


# Import moved modules

if IS_PYTHON2:
    import __builtin__ as builtins
    import htmlentitydefs as html_entities
    import HTMLParser as html_parser
else:
    import builtins
    import html.entities as html_entities
    import html.parser as html_parser


# String types for Python 2 and 3.

if IS_PYTHON2:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode
    unichr = unichr
else:
    string_types = str,
    integer_types = int,
    text_type = str
    unichr = chr

numeric_types = (float, ) + integer_types

# This function should only be called in Python 2, and will fail in Python 3

if IS_PYTHON2:
    def stringrepr(string):
        ascii = string.encode('ascii', 'backslashreplace')
        quoted = "'" +  ascii.replace("'", "\\'") + "'"
        if len(ascii) > len(string):
            return 'u' + quoted
        return quoted
else:
    def stringrepr(string):
        raise RuntimeError(
                'Python 2 compatibility function. Not usable in Python 3.')


# We need to test if an object is an instance of a string type in places

def isstring(obj):
    return isinstance(obj, string_types)

# We need to differentiate between StringIO and BytesIO in places

if IS_PYTHON2:
    from StringIO import StringIO
    try:
        from cStringIO import StringIO as BytesIO
    except ImportError:
        BytesIO = StringIO
else:
    from io import StringIO, BytesIO


# We want to test bytestring input to some stuff.

if IS_PYTHON2:
    def wrapped_bytes(bstr):
        assert bstr.startswith('b')
        return bstr[1:]
else:
    def wrapped_bytes(bstr):
        assert bstr.startswith('b')
        return bstr


# Define a common exec function

if IS_PYTHON2:
    def exec_(_code_, _globs_=None, _locs_=None):
        """Execute code in a namespace."""
        if _globs_ is None:
            frame = sys._getframe(1)
            _globs_ = frame.f_globals
            if _locs_ is None:
                _locs_ = frame.f_locals
            del frame
        elif _locs_ is None:
            _locs_ = _globs_
        exec("""exec _code_ in _globs_, _locs_""")

else:
    exec_ = getattr(builtins, "exec")


# Class decorator for adding a metaclass

def add_metaclass(metaclass):
    """Class decorator for creating a class with a metaclass."""
    def wrapper(cls):
        orig_vars = cls.__dict__.copy()
        slots = orig_vars.get('__slots__')
        if slots is not None:
            if isinstance(slots, str):
                slots = [slots]
            for slots_var in slots:
                orig_vars.pop(slots_var)
        orig_vars.pop('__dict__', None)
        orig_vars.pop('__weakref__', None)
        if hasattr(cls, '__qualname__'):
            orig_vars['__qualname__'] = cls.__qualname__
        return metaclass(cls.__name__, cls.__bases__, orig_vars)
    return wrapper


# We do some scary stuff with CodeType() in template/eval.py

if IS_PYTHON2:
    def get_code_params(code):
        return (code.co_nlocals, code.co_stacksize, code.co_flags,
                code.co_code, code.co_consts, code.co_names, code.co_varnames,
                code.co_filename, code.co_name, code.co_firstlineno,
                code.co_lnotab, (), ())

    def build_code_chunk(code, filename, name, lineno):
        return CodeType(0, code.co_nlocals, code.co_stacksize,
                        code.co_flags | 0x0040, code.co_code, code.co_consts,
                        code.co_names, code.co_varnames, filename, name,
                        lineno, code.co_lnotab, (), ())
else:
    def get_code_params(code):
        params = []
        if hasattr(code, "co_posonlyargcount"):
            # PEP 570 -- Python Positional-Only Parameters
            params.append(code.co_posonlyargcount)
        params.extend([code.co_kwonlyargcount, code.co_nlocals,
                       code.co_stacksize, code.co_flags, code.co_code,
                       code.co_consts, code.co_names, code.co_varnames,
                       code.co_filename, code.co_name])
        if hasattr(code, "co_qualname"):
            # https://bugs.python.org/issue13672
            params.append(code.co_qualname)
        params.append(code.co_firstlineno)
        if hasattr(code, "co_linetable"):
            # PEP 626 -- Precise line numbers for debugging and other tools.
            params.append(code.co_linetable)
        else:
            params.append(code.co_lnotab)
        if hasattr(code, "co_endlinetable"):
            # PEP 657 -- Include Fine Grained Error Locations in Tracebacks
            params.append(code.co_endlinetable)
        if hasattr(code, "co_columntable"):
            # PEP 657 -- Include Fine Grained Error Locations in Tracebacks
            params.append(code.co_columntable)
        if hasattr(code, "co_exceptiontable"):
            # https://bugs.python.org/issue40222
            params.append(code.co_exceptiontable)
        params.extend([(), ()])
        return tuple(params)


    def build_code_chunk(code, filename, name, lineno):
        if hasattr(code, 'replace'):
            # Python 3.8+
            return code.replace(
                co_filename=filename,
                co_name=name,
                co_firstlineno=lineno,
            )
        # XXX: This isn't equivalent to the above "replace" code (we overwrite
        # co_argcount, co_flags, co_freevars, and co_cellvars). Should one of
        # them be changed?
        return CodeType(0, code.co_kwonlyargcount, code.co_nlocals,
                        code.co_stacksize, code.co_flags | 0x0040, code.co_code,
                        code.co_consts, code.co_names, code.co_varnames,
                        filename, name, lineno, code.co_lnotab, (), ())


# In Python 3.8, Str and Ellipsis was replaced by Constant

with warnings.catch_warnings():
    warnings.filterwarnings('error', category=DeprecationWarning)
    try:
        _ast_Ellipsis = ast.Ellipsis
        _ast_Ellipsis_value = lambda obj: Ellipsis
        _ast_Str = ast.Str
        _ast_Str_value = lambda obj: obj.s
    except (AttributeError, DeprecationWarning):
        _ast_Ellipsis = ast.Constant
        _ast_Ellipsis_value = lambda obj: obj.value
        _ast_Str = ast.Constant
        _ast_Str_value = lambda obj: obj.value

class _DummyASTItem(object):
    pass
try:
    _ast_Constant = ast.Constant
except AttributeError:
    # Python 2
    _ast_Constant = _DummyASTItem
