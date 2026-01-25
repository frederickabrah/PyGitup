"""
This is a sample module for testing documentation generation.
It contains various functions and classes for demonstration purposes.
"""

def hello_world(name):
    """
    Print a greeting to the specified name.
    
    Args:
        name (str): The name to greet
        
    Returns:
        None
    """
    print(f"Hello, {name}!")

def add_numbers(a, b):
    """
    Add two numbers together.
    
    Args:
        a (int): First number
        b (int): Second number
        
    Returns:
        int: The sum of a and b
    """
    return a + b

class Calculator:
    """
    A simple calculator class for basic arithmetic operations.
    """
    
    def __init__(self):
        """Initialize the calculator."""
        pass
    
    def multiply(self, x, y):
        """
        Multiply two numbers.
        
        Args:
            x (float): First number
            y (float): Second number
            
        Returns:
            float: The product of x and y
        """
        return x * y