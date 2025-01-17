import os

os.environ["GEMINI_API_KEY"] = "${GEMINI_API_KEY}"

# Now run the test notebook
with open("test_notebook.py") as f:
    exec(f.read())
