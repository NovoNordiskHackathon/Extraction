import json
import re
import sys
import pandas as pd


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


def find_schedule_end(all_rows, column_to_visit, start_from=0):
    """
    Find where schedule procedures end by looking for a significant drop
    in procedure density AFTER we've found some procedures.
    """
    procedure_count = 0
    consecutive_non_procedures = 0

    # First, count total procedures to get a baseline
    total_procedures = 0
    for i, row in enumerate(all_rows[start_from:], start_from):
        if not row:
            continue
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())
        if has_markers:
            total_procedures += 1

    print(f"🔍 Found {total_procedures} total rows with visit markers")

    # Now look for natural end point
    for i, row in enumerate(all_rows[start_from:], start_from):
        if not row:
            continue

        first_cell = str(row[0]).strip()

        # Check if this row has visit markers
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())

        if has_markers:
            procedure_count += 1
            consecutive_non_procedures = 0
        else:
            consecutive_non_procedures += 1

            # Stop if we've found a good chunk of procedures (at least 30)
            # and now hit many consecutive non-procedure rows
            if procedure_count >= 30 and consecutive_non_procedures > 20:
                print(f"📍 Found schedule end at row {i} ({procedure_count} procedures found)")
                return i

            # Also check for obvious section breaks after we have some procedures
            if procedure_count >= 20:
                if (re.match(r'^Objectives$', first_cell) or
                        re.match(r'^Primary$', first_cell) or
                        re.match(r'^Secondary$', first_cell) or
                        re.match(r'^Event type$', first_cell) or
                        first_cell == "Objectives"):
                    print(f"📍 Found section break at row {i}: '{first_cell}' ({procedure_count} procedures)")
                    return i

    return len(all_rows)  # Process all if no clear end found


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
    """Parse schedule with smart end detection."""
    schedule = {}
    tables = find_all_schedule_tables(protocol_data)
    if not tables:
        print("❌ No schedule tables found")
        return None, None, None

    # Merge all rows from all tables
    all_rows = []
    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        all_rows.extend([flatten_row(row) for row in rows])

    # Find visit header row
    visit_row = next(
        (row for row in all_rows if any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row)),
        None
    )
    if not visit_row:
        print("❌ Could not find visit header row")
        return None, None, None

    print("✅ Found visit header row:", visit_row[:8])

    # Map column index -> visit name and preserve visit order
    column_to_visit = {}
    visit_order = []
    for i, cell in enumerate(visit_row):
        if not isinstance(cell, str):
            continue
        m = re.search(r'(?:V|P)\d+[A-Za-z]*', cell)
        if m:
            visit_name = m.group(0)
            column_to_visit[i] = visit_name
            visit_order.append(visit_name)

    # Find where the visit header row is located
    header_row_index = -1
    for i, row in enumerate(all_rows):
        if row == visit_row:
            header_row_index = i
            break

    # SMART END DETECTION (start looking after header row)
    end_index = find_schedule_end(all_rows, column_to_visit, header_row_index + 1)
    print(f"🎯 Processing rows {header_row_index + 1} to {end_index}")

    # Track procedure order as they appear in JSON
    procedure_order = []

    # Process only rows between header and detected end
    for i, row in enumerate(all_rows[header_row_index + 1:end_index], header_row_index + 1):
        if not row:
            continue
        first_cell = str(row[0]).strip() if len(row) > 0 else ""
        if not first_cell or first_cell.lower() in ["visit", "procedure", "study week", "visit window"]:
            continue

        procedure = first_cell

        # Only add if this row has visit markers (actual procedure)
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())

        if has_markers:
            # Add to procedure order when first encountered
            if procedure not in procedure_order:
                procedure_order.append(procedure)

            for col, visit_name in column_to_visit.items():
                cell_text = row[col] if col < len(row) else ""
                if cell_has_marker(cell_text):
                    schedule.setdefault(visit_name, []).append(procedure)

    return schedule, visit_order, procedure_order


def save_schedule_to_csv(schedule, visit_order, procedure_order, output_path="schedule_fixed.csv"):
    """Save schedule to CSV preserving order."""
    if not schedule:
        print("❌ Schedule is empty, not saving CSV.")
        return

    df = pd.DataFrame(index=procedure_order, columns=visit_order)
    df = df.fillna('')

    for visit, procedures in schedule.items():
        for proc in procedures:
            if proc in df.index:
                df.loc[proc, visit] = 'X'

    df.index.name = "Procedure"
    df.to_csv(output_path)
    print(f"✅ Schedule saved to '{output_path}'")
    print(f"📊 Total procedures: {len(procedure_order)}")


# -----------------------
# Main script
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        file_path = "hierarchical_output_final.json"
    else:
        file_path = sys.argv[1]

    print(f"🔍 Processing file: {file_path}")

    try:
        protocol_json = load_json(file_path)
        schedule, visit_order, procedure_order = parse_protocol_schedule(protocol_json)

        if schedule:
            print(f"\n✅ Successfully extracted schedule")
            print(f"📋 First 10 procedures:")
            for i, proc in enumerate(procedure_order[:10], 1):
                print(f"  {i:2d}. {proc}")

            save_schedule_to_csv(schedule, visit_order, procedure_order)
        else:
            print("❌ No schedule extracted.")

    except Exception as e:
        print(f"❌ Error: {e}")
