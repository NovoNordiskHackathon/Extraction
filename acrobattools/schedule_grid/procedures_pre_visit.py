import json
import re
import sys

# -----------------------
# Helper functions
# -----------------------
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_node_text(node):
    """Extract all text from a node and its children as a single string."""
    if not node:
        return ""
    text = node.get("text", "") or ""
    for child in node.get("children", []):
        text += " " + get_node_text(child)
    return text.replace('\n', ' ').replace('\r', ' ').strip()

def find_nodes_by_name(root, name_prefix):
    """Find all nodes whose 'name' starts with name_prefix."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("name", "").startswith(name_prefix):
                found.append(node)
            for child in node.get("children", []):
                walk(child)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(root)
    return found

def flatten_row(row):
    """Flatten a table row into a list of cell texts."""
    texts = []
    for cell in row.get("children", []):
        texts.append(get_node_text(cell))
    return texts

# -----------------------
# Main parsing functions
# -----------------------
def find_all_schedule_tables(root):
    """Return all tables that contain visit headers (V1, V2, ...)."""
    tables = find_nodes_by_name(root, "Table")
    schedule_tables = []
    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]
        if any(any(re.search(r'\bV\d+\b', str(cell)) for cell in row) for row in table_content):
            schedule_tables.append(table)
    return schedule_tables

def parse_protocol_schedule(protocol_data):
    """Parse all multi-page schedule tables."""
    schedule = {}
    tables = find_all_schedule_tables(protocol_data)
    if not tables:
        print("❌ No schedule tables found")
        return None

    # Merge all rows from all tables
    all_rows = []
    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        all_rows.extend([flatten_row(row) for row in rows])

    # DEBUG: print all rows
    for i, row in enumerate(all_rows):
        print(f"DEBUG Row {i}: {row}")

    # Identify visit header row (first occurrence of V1, V2...)
    visit_row = next((row for row in all_rows if any(re.match(r'^V\d+', str(cell).strip()) for cell in row)), None)
    if not visit_row:
        print("❌ Could not find visit header row")
        return None

    print("✅ Found visit header row:", visit_row)
    column_to_visit = {i: cell.strip() for i, cell in enumerate(visit_row) if re.match(r'^V\d+', cell.strip())}

    # Collect procedures per visit
    for row in all_rows:
        if not row or row[0].strip().lower() in ["visit", "procedure"]:
            continue
        procedure = row[0].strip()
        for i, visit_name in column_to_visit.items():
            cell_text = row[i] if i < len(row) else ""
            if "X" in cell_text.upper():
                schedule.setdefault(visit_name, []).append(procedure)

    return schedule

# -----------------------
# Main script
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug2.py path/to/json_file")
        sys.exit(1)

    file_path = sys.argv[1]
    protocol_json = load_json(file_path)
    schedule = parse_protocol_schedule(protocol_json)

    if schedule:
        print("\n--- Extracted Schedule ---")
        for visit, procedures in schedule.items():
            print(f"{visit}: {procedures}")
    else:
        print("No schedule extracted.")
