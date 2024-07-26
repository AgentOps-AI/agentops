import os

# import subprocess
import pypandoc

# Before generating, `brew install pandoc`


import pypandoc
import os


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
                target_dir, filename.rsplit(".", 1)[0] + ".html"
            )

            # Convert notebook to html_format
            output = pypandoc.convert_file(
                source_file,
                "html",
                outputfile=html_target_file,
                extra_args=["-c", "template/notebook_styles.css"],
            )
            assert output == ""


convert_notebooks_to_html("../../../../examples", "./")
