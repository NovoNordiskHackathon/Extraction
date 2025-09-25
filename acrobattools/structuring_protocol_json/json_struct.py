import json
import re

def get_header_level(path):
    """Detect header level from path (Title, H1, H2, etc.)."""
    if path.endswith("/Title"):
        return 0
    match = re.search(r'/H(\d+)(\[\d+\])?$', path)
    if match:
        return int(match.group(1))
    return None

def is_table_path(path):
    """Return True if element belongs to table hierarchy."""
    return re.search(r'/(Table|TR|TD|TH|P|Span)', path) is not None

def get_parent_path(path):
    """Get parent path by removing last component."""
    if not path or path == "/":
        return ""
    parts = path.strip("/").split("/")
    if len(parts) <= 1:
        return ""
    return "/" + "/".join(parts[:-1])

def parse_hierarchy(elements):
    root = {"name": "Document Root", "children": []}
    header_context = {0: root}  # Tracks current headers by level
    path_to_node = {"": root}   # Tracks all nodes by full path

    # Helper to ensure any ancestor path exists (creates placeholders if needed)
    def ensure_path_exists(target_path):
        """
        Ensure a node exists for target_path in path_to_node.
        If missing, recursively create parent(s) and attach placeholder nodes.
        For top-level parent (empty), attach to current header context.
        """
        if target_path in path_to_node:
            return path_to_node[target_path]

        if not target_path:
            return path_to_node[""]

        parent_path = get_parent_path(target_path)

        # Determine parent node: either recursively ensure parent or attach to current header
        if parent_path == "":
            parent_node = header_context[max(header_context.keys())]
        else:
            parent_node = ensure_path_exists(parent_path)

        node_name = target_path.split("/")[-1]
        new_node = {"name": node_name, "text": "", "path": target_path, "children": []}
        path_to_node[target_path] = new_node
        parent_node.setdefault("children", []).append(new_node)
        return new_node

    for elem in elements:
        path = elem.get("path") or elem.get("Path") or ""
        text = elem.get("text") or elem.get("Text") or ""
        name = path.split("/")[-1] if path else ""

        # Create new node and register it immediately
        node = {"name": name, "text": text, "path": path, "children": []}
        path_to_node[path] = node

        header_level = get_header_level(path)

        # --- Handle Headers (Title, H1, H2, …) ---
        if header_level is not None:
            parent_level = max([lvl for lvl in header_context if lvl < header_level], default=0)
            parent = header_context[parent_level]
            parent.setdefault("children", []).append(node)
            header_context[header_level] = node
            # Clean up deeper headers no longer valid
            for lvl in list(header_context.keys()):
                if lvl > header_level:
                    del header_context[lvl]

        # --- Handle Tables (STRICT hierarchy enforcement) ---
        elif is_table_path(path):
            # derive base name (strip index like TD[2] -> TD)
            m = re.match(r'^([A-Za-z]+)', name)
            base_name = m.group(1) if m else name

            # For Span: ensure its paragraph exists, then append Span under the paragraph
            if base_name == "Span":
                para_path = get_parent_path(path)  # e.g., .../P[1]
                para_node = ensure_path_exists(para_path)
                para_node.setdefault("children", []).append(node)

            # For Paragraphs (P...): ensure its parent cell (TD/TH) exists, then append P under cell
            elif base_name == "P":
                cell_path = get_parent_path(path)  # e.g., .../TD[1] or .../TH[1]
                cell_node = ensure_path_exists(cell_path)
                cell_node.setdefault("children", []).append(node)

            # For TD/TH: ensure row (TR) exists, then append cell under TR
            elif base_name in ("TD", "TH"):
                tr_path = get_parent_path(path)  # e.g., .../TR[1]
                tr_node = ensure_path_exists(tr_path)
                tr_node.setdefault("children", []).append(node)

            # For TR: ensure its table exists, then append TR under Table
            elif base_name == "TR":
                table_path = get_parent_path(path)  # e.g., .../Table[1]
                table_node = ensure_path_exists(table_path)
                table_node.setdefault("children", []).append(node)

            # For Table: attach under its parent (usually /Document or header)
            elif base_name == "Table":
                parent_path = get_parent_path(path)
                if parent_path:
                    parent_node = ensure_path_exists(parent_path)
                else:
                    parent_node = header_context[max(header_context.keys())]
                parent_node.setdefault("children", []).append(node)

            else:
                # Fallback: attach to the immediate parent if possible, otherwise to current header
                parent_path = get_parent_path(path)
                parent = path_to_node.get(parent_path) or header_context[max(header_context.keys())]
                parent.setdefault("children", []).append(node)

        # --- Default (non-table, non-header): attach to current header context ---
        else:
            parent = header_context[max(header_context.keys())]
            parent.setdefault("children", []).append(node)

    return root


# --- Usage Example ---
if __name__ == "__main__":
    input_file = "/Users/sharmishtaganesh/Desktop/Hackathon_docs/Extraction/acrobattools/texttablestructured_protocol.json"
    output_file = "/Users/sharmishtaganesh/Desktop/Hackathon_docs/Extraction/acrobattools/structuring_protocol_json/hierarchical_output_final.json"

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    elements = data.get('elements', []) if isinstance(data, dict) else []
    hierarchy = parse_hierarchy(elements)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(hierarchy, f, indent=2)

    print(f"✅ Full, robust document hierarchy saved to {output_file}")
