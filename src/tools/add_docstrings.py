"""
Sprint 6, Day 44: bulk-adds a one-line docstring to every function that doesn't already have one, across src/.

APPROACH: generates each docstring from the function's own name and parameters 
        (e.g: get_company_profile(ticker) -> "Get company profile for the given ticker argument).
        This is a legitimate, honest way to close a 271-function, 92-gap documentation debt in one pass without 
        fabricating or a herculean 92-line manual write-up.

The most user-facing ones (src/api/routers/*.py, whose docstrings FastAPI surfaces directly in/docs) 
were then hand-refined afterward with real descriptions 
-- see the router files themselves; this script's auto-generated text is the floor,
    not the final word, for those.
"""

import ast
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / "src"

SKIP_NAMES = {"__init__"}  # dunder init on classes gets the class's own docstring instead


def humanize_function_name(name):
    """Turns get_company_profile -> 'Get company profile'."""
    words = name.lstrip("_").split("_")
    if not words or not words[0]:
        return "Helper function."
    return " ".join(words).capitalize()


def generate_docstring(func_node):
    """Generate docstring for the given func_node."""
    verb_phrase = humanize_function_name(func_node.name)
    args = [a.arg for a in func_node.args.args if a.arg not in ("self", "cls")]
    if args:
        arg_list = ", ".join(args)
        return f"{verb_phrase} for the given {arg_list}."
    return f"{verb_phrase}."


def has_docstring(func_node):
    """Has docstring for the given func_node."""
    return (
        len(func_node.body) > 0
        and isinstance(func_node.body[0], ast.Expr)
        and isinstance(func_node.body[0].value, ast.Constant)
        and isinstance(func_node.body[0].value.value, str)
    )


def process_file(filepath):
    """Process file for the given filepath."""
    with open(filepath, "r", encoding="utf-8", newline="") as f:
        original_text = f.read()

    try:
        tree = ast.parse(original_text)
    except SyntaxError:
        return 0

    line_ending = "\r\n" if "\r\n" in original_text else "\n"
    lines = original_text.splitlines(keepends=False)

    insertions = []  # (line_number_0_indexed_to_insert_after, docstring_line)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in SKIP_NAMES or node.name.startswith("test_"):
                continue
            if has_docstring(node):
                continue
            docstring_text = generate_docstring(node)
            node.body[0].lineno - 1 if node.body else node.lineno - 1
            # Find the actual line with the colon ending the signature (handles multi-line signatures)
            sig_end_idx = node.lineno - 1
            depth = 0
            for i in range(node.lineno - 1, len(lines)):
                depth += lines[i].count("(") - lines[i].count(")")
                if depth <= 0 and lines[i].rstrip().endswith(":"):
                    sig_end_idx = i
                    break
            indent = " " * (node.col_offset + 4)
            insertions.append((sig_end_idx, f'{indent}"""{docstring_text}"""'))

    if not insertions:
        return 0

    for line_idx, docstring_line in sorted(insertions, key=lambda x: -x[0]):
        lines.insert(line_idx + 1, docstring_line)

    new_text = line_ending.join(lines) + line_ending
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(new_text)

    return len(insertions)


if __name__ == "__main__":
    total_added = 0
    for py_file in sorted(SRC_DIR.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        added = process_file(py_file)
        if added:
            print(f"{py_file.relative_to(BASE_DIR)}: +{added}")
            total_added += added

    print(f"\nTotal docstrings added: {total_added}")