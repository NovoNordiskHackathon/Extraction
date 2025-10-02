import json
import re


def normalize_path(path):
    """Normalize path by ensuring consistent double-slash prefix."""
    if not path:
        return ""
    path = path.lstrip("/")
    return "//" + path if path else ""


def get_header_level(path):
    """Detect header level from path (Title, H1, H2, etc.)."""
    normalized = normalize_path(path)
    if normalized.endswith("/Title"):
        return 0
    match = re.search(r'/H(\d+)(\[\d+\])?$', normalized)
    if match:
        return int(match.group(1))
    return None


def is_table_or_complex_structure(path):
    """Return True only for complex nested structures like tables, lists, etc."""
    return re.search(r'/(TR|TD|TH|LBody|LI|Lbl|Caption|Footnote|Aside)', path) is not None


def is_inline_content(path):
    """Return True for inline content like Span, Sub that should nest under paragraphs."""
    return re.search(r'/(Span|Sub|StyleSpan|ExtraCharSpan)$', path) is not None


def is_top_level_table(path):
    """Return True if this is a top-level table directly under Document."""
    normalized = normalize_path(path)
    return re.match(r'^//Document/Table(\[\d+\])?$', normalized) is not None


def get_parent_path(path):
    """Get parent path by removing last component."""
    normalized = normalize_path(path)
    if not normalized or normalized == "//":
        return ""
    parts = normalized[2:].split("/")  # Remove // prefix and split
    if len(parts) <= 1:
        return ""
    return "//" + "/".join(parts[:-1])


def parse_hierarchy(elements):
    root = {"name": "Document Root", "children": []}
    header_context = {0: root}
    path_to_node = {"": root, "//Document": root}

    def ensure_path_exists(target_path):
        """Ensure node exists for target_path, create placeholders if missing."""
        normalized = normalize_path(target_path)

        if normalized == "//Document" or normalized == "":
            return root

        if normalized in path_to_node:
            return path_to_node[normalized]

        parent_path = get_parent_path(normalized)

        if parent_path == "//Document" or parent_path == "":
            parent_node = header_context[max(header_context.keys())]
        else:
            parent_node = ensure_path_exists(parent_path)

        node_name = normalized.split("/")[-1] if normalized else "Unknown"
        new_node = {"name": node_name, "text": "", "path": normalized, "children": []}
        path_to_node[normalized] = new_node
        parent_node.setdefault("children", []).append(new_node)
        return new_node

    for elem in elements:
        original_path = elem.get("path") or elem.get("Path") or ""
        path = normalize_path(original_path)
        text = elem.get("text") or elem.get("Text") or ""
        name = path.split("/")[-1] if path else ""

        # Skip creating separate Document nodes
        if name == "Document" and path == "//Document":
            continue

        node = {"name": name, "text": text, "path": path, "children": []}
        path_to_node[path] = node

        header_level = get_header_level(path)

        if header_level is not None:
            # Headers: nest under appropriate parent header
            parent_level = max([lvl for lvl in header_context if lvl < header_level], default=0)
            parent = header_context[parent_level]
            parent.setdefault("children", []).append(node)
            header_context[header_level] = node
            # Clean up deeper headers
            for lvl in list(header_context.keys()):
                if lvl > header_level:
                    del header_context[lvl]

        elif is_top_level_table(path):
            # Top-level tables: place under current header context, not root
            parent = header_context[max(header_context.keys())]
            parent.setdefault("children", []).append(node)

        elif is_inline_content(path):
            # Inline content: nest under parent paragraph/element
            parent_path = get_parent_path(path)
            parent_node = ensure_path_exists(parent_path)
            parent_node.setdefault("children", []).append(node)

        elif is_table_or_complex_structure(path):
            # Complex structures: use strict path hierarchy
            parent_path = get_parent_path(path)
            parent_node = ensure_path_exists(parent_path)
            parent_node.setdefault("children", []).append(node)

        else:
            # Default: Paragraphs and other content under current header context
            parent = header_context[max(header_context.keys())]
            parent.setdefault("children", []).append(node)

    return root


def run_hierarchy(input_file, output_file=None):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    elements = data.get('elements', []) if isinstance(data, dict) else []
    hierarchy = parse_hierarchy(elements)

      # If output_file is None, create from input_file by inserting '_output' before extension
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_output{ext}"


    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)

    print(f"✅ Fixed table placement hierarchy saved to {output_file}")

if __name__ == "__main__":
    import sys
    input_file = sys.argv[1] if len(sys.argv) > 1 else "texttablestructured_protocol2.json"
    run_hierarchy(input_file)

