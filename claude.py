from pathlib import Path

import anthropic

# Collect all Python files in your main folders
folders = [
    "B.o.B",
    "config",
    "modules",
    "ui",
    "utils",
    "app.py",
]  # Add more folders/files as needed
code_blocks = []

for folder in folders:
    path = Path(folder)
    if path.is_file() and path.suffix == ".py":
        code_blocks.append(path.read_text())
    elif path.is_dir():
        for py_file in path.rglob("*.py"):
            code_blocks.append(py_file.read_text())

# Combine code for analysis (limit size if needed)
combined_code = "\n\n".join(code_blocks)[:15000]  # Limit to 15,000 chars for API

prompt = """
You are a code review assistant. Analyze the following Python code from multiple files and identify any duplicate code blocks, functions, or patterns. Provide a summary of duplicates found.

CODE:
{code}
"""

# Create an Anthropic client instance (replace YOUR_API_KEY with your actual key)
client = anthropic.Anthropic(api_key="YOUR_API_KEY")

# Read your file
with open("app.py", "r") as f:
    code_content = f.read()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt.format(code=code_content)}],
    )

print(response.content)
