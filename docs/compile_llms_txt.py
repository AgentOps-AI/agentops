import os
from pathlib import Path

def compile_llms_txt():
    """Compile all relevant documentation into llms.txt for AI model consumption."""
    current_dir = Path(os.getcwd())
    content = ''
    
    # Define names of directories and files to exclude
    excluded_names = {'node_modules', '.git', '__pycache__', '.venv', 'images', '.pytest_cache', 'dist', 'build'}
    
    def should_include_file(file_path):
        """Check if a file should be included based on patterns and exclusions."""
        path_parts = Path(file_path).parts
        
        if any(part in excluded_names for part in path_parts):
            return False
            
        if file_path.endswith(('.md', '.mdx')):
            return True
            
        return False
    
    for root, dirs, files in os.walk('..'):
        dirs[:] = [d for d in dirs if d not in excluded_names]
        
        for file in files:
            if should_include_file(file):
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, '..')
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    content += f"## {relative_path}\n\n{file_content}\n\n"
                except (UnicodeDecodeError, PermissionError) as e:
                    print(f"Warning: Could not read {relative_path}: {e}")
                    continue

    # Write the complete content to llms.txt in the repository root
    output_path = Path('../llms.txt')
    output_path.write_text(content, encoding='utf-8')
    print(f"Successfully compiled documentation to {output_path.absolute()}")
    print(f"Total content length: {len(content)} characters")

if __name__ == "__main__":
    compile_llms_txt()
