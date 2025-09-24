import re
import json

def parse_hierarchy(elements):
    def get_level_from_path(path):
        if path.endswith("/Title"):
            return 0
        match = re.search(r'/H(\d+)(\[\d+\])?$', path)
        if match:
            return int(match.group(1))
        return 100  # Non-heading elements get max level

    root = {"text": "Document Root", "children": []}
    stack = [(0, root)]  # Always start with root in stack

    for elem in elements:
        path = elem.get("path") or elem.get("Path") or ""
        text = elem.get("text") or elem.get("Text") or ""
        level = get_level_from_path(path)

        node = {"text": text, "path": path, "children": []}

        # Pop stack until top level is less than current level
        while stack and stack[-1][0] >= level:
            stack.pop()

        # If stack empty after pop (edge case), re-add root
        if not stack:
            stack.append((0, root))

        stack[-1][1].setdefault("children", []).append(node)
        stack.append((level, node))

    return root

# Load elements
with open('../texttablestructured_ecrf.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
elements = data.get('elements', []) if isinstance(data, dict) else []

hierarchy = parse_hierarchy(elements)
with open('hierarchical_output_v3.json', 'w', encoding='utf-8') as f:
    json.dump(hierarchy, f, indent=2)
