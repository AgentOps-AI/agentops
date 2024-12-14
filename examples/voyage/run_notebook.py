import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os


def run_notebook():
    # Load the notebook
    notebook_path = os.path.join(os.path.dirname(__file__), "voyage_example.ipynb")

    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    # Configure the notebook executor
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    try:
        # Execute the notebook
        ep.preprocess(nb, {"metadata": {"path": os.path.dirname(os.path.abspath(__file__))}})

        # Save the executed notebook
        with open(notebook_path, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)

        print("Notebook executed successfully!")

    except Exception as e:
        print(f"Error executing notebook: {str(e)}")
        raise


if __name__ == "__main__":
    run_notebook()
