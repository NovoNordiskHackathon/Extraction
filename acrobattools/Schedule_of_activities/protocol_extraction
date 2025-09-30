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

def cell_has_marker(text):
    """Return True if the cell text contains a schedule marker (X, check, YES)."""
    if not isinstance(text, str):
        return False
    return bool(re.search(r'\b(?:X|YES)\b|[✔✓]', text, flags=re.IGNORECASE))

# -----------------------
# Merge broken tables logic
# -----------------------
def merge_broken_tables(tables):
    """
    Merge consecutive tables if the later one has no visit header row
    (i.e., it's a continuation of the previous page's table).
    """
    if not tables:
        return []

    merged = []
    buffer = None

    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]

        # does this table contain visit or phone headers (V1, P13, etc.) anywhere in its rows?
        has_visits = any(
            any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row)
            for row in table_content
        )

        if buffer is None:
            buffer = table
            buffer_has_visits = has_visits
            continue

        if not has_visits:
            # continuation → append TR nodes from this table to buffer's children
            buffer["children"].extend(rows)
        else:
            # this table has headers:
            # flush buffer if buffer had headers, else (rare) merge buffer into this as continuation
            if buffer_has_visits:
                merged.append(buffer)
                buffer = table
                buffer_has_visits = True
            else:
                # previous buffer had no visits -> treat it as continuation of current table
                # prepend buffer rows to current table children (keep order logical)
                # collect buffer TRs
                buf_rows = find_nodes_by_name(buffer, "TR")
                table["children"] = buf_rows + table.get("children", [])
                buffer = table
                buffer_has_visits = True

    # flush final buffer
    if buffer is not None:
        merged.append(buffer)

    return merged

# -----------------------
# Main parsing functions
# -----------------------
def find_all_schedule_tables(root):
    """Return all tables that belong to the schedule (merge continuations)."""
    tables = find_nodes_by_name(root, "Table")
    merged_tables = merge_broken_tables(tables)

    # keep only those merged tables that actually contain visits
    schedule_tables = []
    for table in merged_tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]
        if any(any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row) for row in table_content):
            schedule_tables.append(table)
    return schedule_tables

def parse_protocol_schedule(protocol_data):
    """Parse all multi-page schedule tables into schedule dict {visit: [procedures]}."""
    schedule = {}
    tables = find_all_schedule_tables(protocol_data)
    if not tables:
        print("❌ No schedule tables found")
        return None

    # Merge all rows from all (now possibly merged) tables
    all_rows = []
    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        all_rows.extend([flatten_row(row) for row in rows])

    # DEBUG: print all rows (comment out if too verbose)
    for i, row in enumerate(all_rows):
        print(f"DEBUG Row {i}: {row}")

    # Identify visit header row (first row that contains any V or P id)
    visit_row = next(
        (row for row in all_rows if any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row)),
        None
    )
    if not visit_row:
        print("❌ Could not find visit header row")
        return None

    print("✅ Found visit header row:", visit_row)

    # Map column index -> visit name (extract exact V/P token, e.g. "P13" from "c P13")
    column_to_visit = {}
    for i, cell in enumerate(visit_row):
        if not isinstance(cell, str):
            continue
        m = re.search(r'(?:V|P)\d+', cell)
        if m:
            column_to_visit[i] = m.group(0)

    # Collect procedures per visit
    for row in all_rows:
        if not row:
            continue
        first_cell = str(row[0]).strip() if len(row) > 0 else ""
        if not first_cell or first_cell.lower() in ["visit", "procedure"]:
            continue
        procedure = first_cell
        for i, visit_name in column_to_visit.items():
            cell_text = row[i] if i < len(row) else ""
            if cell_has_marker(cell_text):
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
