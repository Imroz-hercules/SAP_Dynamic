#!/usr/bin/env python3
"""
Quick syntax check for the process_orders.py file.
"""

import ast
import sys

def check_syntax():
    """Check if the process_orders.py file has correct syntax."""
    
    try:
        with open('routes/process_orders.py', 'r') as f:
            source = f.read()
        
        # Parse the file to check for syntax errors
        ast.parse(source)
        print("✅ Syntax check passed - no syntax errors found")
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error found:")
        print(f"   Line {e.lineno}: {e.text}")
        print(f"   Error: {e.msg}")
        return False
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

if __name__ == "__main__":
    success = check_syntax()
    sys.exit(0 if success else 1)
