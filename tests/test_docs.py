
import pytest
from pygitup.project.docs import extract_python_docs

# Sample Python code for testing
SAMPLE_PYTHON_CODE = """
\"\"\"
This is a module docstring.
It explains the purpose of the module.
\"\"\"

import os

class MyClass(object):
    \"\"\"
    A sample class to demonstrate AST parsing.
    \"\"\"
    def __init__(self, name):
        \"\"\"
        The constructor for MyClass.
        :param name: The name of the instance.
        \"\"\"
        self.name = name

    def my_method(self, value):
        \"\"\"
        A sample method within MyClass.
        :param value: A value to process.
        :return: A processed value.
        \"\"\"
        return value * 2

def my_function(arg1, arg2='default'):
    \"\"\"
    A sample function outside any class.
    :param arg1: The first argument.
    :param arg2: The second argument with a default.
    \"\"\"
    return arg1 + arg2

class AnotherClass:
    \"\"\"
    Another class with no explicit base.
    \"\"\"
    pass

# A constant
MY_CONSTANT = 123
"""

def test_extract_python_docs_module_docstring():
    docs = extract_python_docs(SAMPLE_PYTHON_CODE, "sample.py")
    assert docs['module_docstring'].strip() == "This is a module docstring.\nIt explains the purpose of the module."

def test_extract_python_docs_functions():
    docs = extract_python_docs(SAMPLE_PYTHON_CODE, "sample.py")
    
    # Test my_function
    func = next((f for f in docs['functions'] if f['name'] == 'my_function'), None)
    assert func is not None
    assert func['params'] == 'arg1, arg2'
    assert "A sample function outside any class." in func['docstring']

def test_extract_python_docs_classes():
    docs = extract_python_docs(SAMPLE_PYTHON_CODE, "sample.py")
    
    # Test MyClass
    cls = next((c for c in docs['classes'] if c['name'] == 'MyClass'), None)
    assert cls is not None
    assert cls['parent'] == 'object'
    assert "A sample class to demonstrate AST parsing." in cls['docstring']
    
    # Test MyClass methods
    init_method = next((m for m in cls['methods'] if m['name'] == '__init__'), None)
    assert init_method is not None
    assert init_method['params'] == 'self, name'
    assert "The constructor for MyClass." in init_method['docstring']

    my_method = next((m for m in cls['methods'] if m['name'] == 'my_method'), None)
    assert my_method is not None
    assert my_method['params'] == 'self, value'
    assert "A sample method within MyClass." in my_method['docstring']

    # Test AnotherClass
    another_cls = next((c for c in docs['classes'] if c['name'] == 'AnotherClass'), None)
    assert another_cls is not None
    assert another_cls['parent'] == 'object' # Default parent
    assert "Another class with no explicit base." in another_cls['docstring']
