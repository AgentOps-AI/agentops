#!/usr/bin/env python3
"""
Script to update imports from SpannedBase to TracedObject after merging the two classes.
"""

import os
import re
from pathlib import Path

def update_file(file_path):
    """Update imports and class references in a file."""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Update import statements
    content = re.sub(
        r'from agentops\.sdk\.spanned import SpannedBase',
        'from agentops.sdk.traced import TracedObject',
        content
    )
    
    # Update class inheritance
    content = re.sub(
        r'class (\w+)\(SpannedBase\)',
        r'class \1(TracedObject)',
        content
    )
    
    # Update type annotations
    content = re.sub(
        r'SpannedBase',
        'TracedObject',
        content
    )
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Updated {file_path}")

def main():
    """Find and update all files that import SpannedBase."""
    root_dir = Path('agentops')
    test_dir = Path('tests')
    
    # Process all Python files in the project
    for directory in [root_dir, test_dir]:
        if not directory.exists():
            continue
            
        for file_path in directory.glob('**/*.py'):
            with open(file_path, 'r') as f:
                content = f.read()
                
            if 'SpannedBase' in content:
                update_file(file_path)

if __name__ == "__main__":
    main() 