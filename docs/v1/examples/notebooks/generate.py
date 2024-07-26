import os
import subprocess

# Before generating, `brew install pandoc`


def convert_notebooks_to_html(source_dir: str, target_dir: str):
    # Ensure the target directory exists
    os.makedirs(target_dir, exist_ok=True)

    # Loop over all files in the source directory
    for filename in os.listdir(source_dir):
        # Check if current file has a .ipynb extension
        if filename.endswith(".ipynb"):
            # Construct full file path
            source_file = os.path.join(source_dir, filename)
            # Construct target file path
            html_target_file = os.path.join(
                target_dir, filename[:-6] + ".html"
            )  # remove '.ipynb' and add '.html'

            # Convert notebook to HTML using pandoc
            subprocess.check_call(
                [
                    "pandoc",
                    source_file,
                    "-s",
                    "-o",
                    html_target_file,
                    "-c",
                    "https://app.agentops.ai/notebook_styles.css",
                ]
            )


# Example usage:
convert_notebooks_to_html("../../../../examples", "./")
