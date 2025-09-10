#!/usr/bin/env python3
"""
Migration script to update AgentOps code from deprecated end_session() to end_trace()

This script helps you migrate your existing AgentOps code to use the new API.
"""

import re
import os
from pathlib import Path

def migrate_file(file_path):
    """Migrate a single file from end_session to end_trace API."""
    print(f"Migrating: {file_path}")
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern 1: Simple end_session() calls
    content = re.sub(
        r'agentops\.end_session\(\)',
        '# TODO: Replace with proper trace management\n# agentops.end_session()',
        content
    )
    
    # Pattern 2: end_session with status string
    content = re.sub(
        r'agentops\.end_session\(["\']([^"\']+)["\']\)',
        r'# TODO: Replace with proper trace management\n# agentops.end_session("\1")\n# Use: agentops.end_trace(tracer, end_state="\1")',
        content
    )
    
    # Pattern 3: end_session with kwargs
    content = re.sub(
        r'agentops\.end_session\(([^)]+)\)',
        r'# TODO: Replace with proper trace management\n# agentops.end_session(\1)\n# Use: agentops.end_trace(tracer, end_state="Success")',
        content
    )
    
    # Add import and trace management if not present
    if 'agentops.start_trace' not in content and 'agentops.end_session' in original_content:
        # Find where to add the trace management
        lines = content.split('\n')
        new_lines = []
        
        # Add trace start after agentops.init
        for i, line in enumerate(lines):
            new_lines.append(line)
            if 'agentops.init(' in line:
                new_lines.append('')
                new_lines.append('# Start a trace for this workflow')
                new_lines.append('tracer = agentops.start_trace(')
                new_lines.append('    trace_name="Your Workflow Name", ')
                new_lines.append('    tags=["your-tags"]')
                new_lines.append(')')
                new_lines.append('')
        
        content = '\n'.join(new_lines)
    
    if content != original_content:
        # Create backup
        backup_path = str(file_path) + '.backup'
        with open(backup_path, 'w') as f:
            f.write(original_content)
        print(f"  Backup created: {backup_path}")
        
        # Write updated content
        with open(file_path, 'w') as f:
            f.write(content)
        print(f"  Updated: {file_path}")
        return True
    else:
        print(f"  No changes needed: {file_path}")
        return False

def find_python_files(directory):
    """Find all Python files in a directory recursively."""
    python_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def main():
    """Main migration function."""
    print("AgentOps Migration Script")
    print("=" * 50)
    print()
    print("This script will help you migrate from the deprecated agentops.end_session()")
    print("to the new agentops.end_trace() API.")
    print()
    
    # Ask for directory to migrate
    directory = input("Enter the directory path to migrate (or press Enter for current directory): ").strip()
    if not directory:
        directory = "."
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return
    
    # Find Python files
    python_files = find_python_files(directory)
    files_with_end_session = []
    
    for file_path in python_files:
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if 'agentops.end_session' in content:
                    files_with_end_session.append(file_path)
        except Exception as e:
            print(f"Warning: Could not read {file_path}: {e}")
    
    if not files_with_end_session:
        print("No files found with agentops.end_session() calls.")
        return
    
    print(f"Found {len(files_with_end_session)} files with agentops.end_session() calls:")
    for file_path in files_with_end_session:
        print(f"  - {file_path}")
    
    print()
    confirm = input("Proceed with migration? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Migration cancelled.")
        return
    
    print()
    migrated_count = 0
    
    for file_path in files_with_end_session:
        try:
            if migrate_file(file_path):
                migrated_count += 1
        except Exception as e:
            print(f"Error migrating {file_path}: {e}")
    
    print()
    print(f"Migration complete! {migrated_count} files updated.")
    print()
    print("Next steps:")
    print("1. Review the changes in each file")
    print("2. Update the TODO comments with proper trace management")
    print("3. Test your code to ensure it works correctly")
    print("4. Remove the backup files once you're satisfied")

if __name__ == "__main__":
    main()