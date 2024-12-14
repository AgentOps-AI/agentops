import nbformat
import json
from pathlib import Path


def verify_notebook_output():
    """Read and verify the notebook output."""
    notebook_path = Path(__file__).parent / "voyage_example.ipynb"

    with open(notebook_path, "r", encoding="utf-8") as f:
        nb = nbformat.read(f, as_version=4)

    found_event_data = False
    found_session_url = False

    for cell in nb.cells:
        if cell.cell_type == "code" and hasattr(cell, "outputs"):
            for output in cell.outputs:
                if hasattr(output, "text"):
                    text = str(output.text)

                    # Check for event data
                    if '"type": "llms"' in text:
                        print("\nFound event data:")
                        print(text)
                        found_event_data = True

                    # Check for session URL
                    if "Session URL:" in text or "session_url" in text.lower():
                        print("\nFound session URL:")
                        print(text)
                        found_session_url = True

    if not found_event_data:
        print("\nWarning: No event data found in notebook output")
    if not found_session_url:
        print("\nWarning: No session URL found in notebook output")


if __name__ == "__main__":
    verify_notebook_output()
