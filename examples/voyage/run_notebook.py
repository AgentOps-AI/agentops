import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import os
import sys


def run_notebook():
    """Run the notebook and display output."""
    # Load the notebook
    notebook_path = os.path.join(os.path.dirname(__file__), "voyage_example.ipynb")

    with open(notebook_path) as f:
        nb = nbformat.read(f, as_version=4)

    # Configure the notebook executor
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")

    try:
        # Execute the notebook
        ep.preprocess(nb, {"metadata": {"path": os.path.dirname(os.path.abspath(__file__))}})

        # Display output from each cell
        for cell in nb.cells:
            if cell.cell_type == "code" and hasattr(cell, "outputs"):
                for output in cell.outputs:
                    if hasattr(output, "text"):
                        print("\nCell output:")
                        print(output.text)
                    elif hasattr(output, "data"):
                        if "text/plain" in output.data:
                            print("\nCell output:")
                            print(output.data["text/plain"])

        # Save the executed notebook
        with open(notebook_path, "w", encoding="utf-8") as f:
            nbformat.write(nb, f)

        print("\nNotebook executed successfully!")

    except Exception as e:
        print(f"Error executing notebook: {str(e)}", file=sys.stderr)
        raise


if __name__ == "__main__":
    run_notebook()
