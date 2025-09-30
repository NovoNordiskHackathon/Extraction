# import json
# import re
# import pandas as pd
#
#
# # -----------------------
# # Helper functions
# # -----------------------
# def load_json(file_path):
#     with open(file_path, "r", encoding="utf-8") as f:
#         return json.load(f)
#
#
# def get_node_text(node):
#     """Extract all text from a node and its children as a single string."""
#     if not node:
#         return ""
#     text = node.get("text", "") or ""
#     for child in node.get("children", []):
#         text += " " + get_node_text(child)
#     return text.replace('\n', ' ').replace('\r', ' ').strip()
#
#
# def find_nodes_by_name(root, name_prefix):
#     """Find all nodes whose 'name' starts with name_prefix."""
#     found = []
#
#     def walk(node):
#         if isinstance(node, dict):
#             if node.get("name", "").startswith(name_prefix):
#                 found.append(node)
#             for child in node.get("children", []):
#                 walk(child)
#         elif isinstance(node, list):
#             for item in node:
#                 walk(item)
#
#     walk(root)
#     return found
#
#
# def flatten_row(row):
#     """Flatten a table row into a list of cell texts."""
#     texts = []
#     for cell in row.get("children", []):
#         texts.append(get_node_text(cell))
#     return texts
#
#
# def cell_has_marker(text):
#     """Return True if the cell text contains a schedule marker (X, check, YES)."""
#     if not isinstance(text, str):
#         return False
#     return bool(re.search(r'\b(?:X|YES)\b|[✔✓]', text, flags=re.IGNORECASE))
#
#
# # -----------------------
# # Merge broken tables logic
# # -----------------------
# def merge_broken_tables(tables):
#     """
#     Merge consecutive tables if the later one has no visit header row
#     (i.e., it's a continuation of the previous page's table).
#     """
#     if not tables:
#         return []
#     merged = []
#     buffer = None
#     for table in tables:
#         rows = find_nodes_by_name(table, "TR")
#         table_content = [flatten_row(row) for row in rows]
#         has_visits = any(any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row) for row in table_content)
#         if buffer is None:
#             buffer = table
#             buffer_has_visits = has_visits
#             continue
#         if not has_visits:
#             buffer["children"].extend(rows)
#         else:
#             if buffer_has_visits:
#                 merged.append(buffer)
#                 buffer = table
#                 buffer_has_visits = True
#             else:
#                 buf_rows = find_nodes_by_name(buffer, "TR")
#                 table["children"] = buf_rows + table.get("children", [])
#                 buffer = table
#                 buffer_has_visits = True
#     if buffer is not None:
#         merged.append(buffer)
#     return merged
#
#
# # -----------------------
# # Main parsing functions
# # -----------------------
# def find_all_schedule_tables(root):
#     """Return all tables that belong to the schedule (merge continuations)."""
#     tables = find_nodes_by_name(root, "Table")
#     merged_tables = merge_broken_tables(tables)
#     schedule_tables = []
#     for table in merged_tables:
#         rows = find_nodes_by_name(table, "TR")
#         table_content = [flatten_row(row) for row in rows]
#         if any(any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row) for row in table_content):
#             schedule_tables.append(table)
#     return schedule_tables
#
#
# def parse_protocol_schedule(protocol_data):
#     """Parse all multi-page schedule tables into schedule dict {visit: [procedures]} and visit order list."""
#     schedule = {}
#     tables = find_all_schedule_tables(protocol_data)
#     if not tables:
#         print("Error: No schedule tables found.")
#         return None, None
#     all_rows = []
#     for table in tables:
#         rows = find_nodes_by_name(table, "TR")
#         all_rows.extend([flatten_row(row) for row in rows])
#     visit_row = next((row for row in all_rows if any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row)), None)
#     if not visit_row:
#         print("Error: Could not find visit header row.")
#         return None, None
#     print("Found visit header row:", visit_row)
#
#     column_to_visit = {}
#     visit_order = []
#     for i, cell in enumerate(visit_row):
#         if not isinstance(cell, str):
#             continue
#         m = re.search(r'(?:V|P)\d+[A-Za-z]*', cell)  # capture suffixes like V19A
#         if m:
#             visit_name = m.group(0)
#             column_to_visit[i] = visit_name
#             visit_order.append(visit_name)
#
#     for row in all_rows:
#         if not row:
#             continue
#         first_cell = str(row[0]).strip() if len(row) > 0 else ""
#         if not first_cell or first_cell.lower() in ["visit", "procedure"]:
#             continue
#         procedure = first_cell
#         for i, visit_name in column_to_visit.items():
#             cell_text = row[i] if i < len(row) else ""
#             if cell_has_marker(cell_text):
#                 schedule.setdefault(visit_name, []).append(procedure)
#     return schedule, visit_order
#
#
# # -----------------------
# # Function to save CSV
# # -----------------------
# def save_schedule_to_csv(schedule, visit_order, output_path="schedule_output.csv"):
#     """Converts the schedule dictionary to a wide-format DataFrame and saves as CSV."""
#     if not schedule:
#         print("Schedule is empty, not saving CSV.")
#         return
#
#     # all_procedures = sorted(list(set(proc for procs in schedule.values() for proc in procs)))
#     all_procedures = list(dict.fromkeys(proc for procs in schedule.values() for proc in procs))
#
#     all_visits = visit_order  # preserve natural order from JSON
#
#     df = pd.DataFrame(index=all_procedures, columns=all_visits)
#     df = df.fillna('')
#
#     for visit, procedures in schedule.items():
#         for proc in procedures:
#             if proc in df.index:
#                 df.loc[proc, visit] = 'X'
#
#     df.index.name = "Procedure"   # add header for first column
#     df.to_csv(output_path)
#     print(f"\nSchedule successfully saved to '{output_path}'")
#
#
# # ==============================================================================
# # --- MAIN SCRIPT EXECUTION ---
# # ==============================================================================
# if __name__ == "__main__":
#     # Set the path to your JSON file directly here.
#     file_path = "/home/ibab/PycharmProjects/Extraction/acrobattools/structuring_protocol_json/hierarchical_output_final.json"
#
#     print(f"Processing file: {file_path}")
#
#     try:
#         protocol_json = load_json(file_path)
#         schedule, visit_order = parse_protocol_schedule(protocol_json)
#
#         if schedule:
#             print("\nExtracted Schedule (Console View):")
#             for visit in visit_order:
#                 print(f"\n{visit}:")
#                 for proc in schedule.get(visit, []):
#                     print(f"  - {proc}")
#
#             save_schedule_to_csv(schedule, visit_order)
#         else:
#             print("\nNo schedule extracted.")
#
#     except FileNotFoundError:
#         print(f"\nError: The file '{file_path}' was not found.")
#         print("Please make sure it is in the same directory as this Python script.")
#     except Exception as e:
#         print(f"An error occurred: {e}")


import json
import re
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


def is_valid_procedure_row(row):
    """Check if this row represents a valid procedure (not header, TOC, etc.)."""
    if not row or len(row) < 2:
        return False

    first_cell = str(row[0]).strip()

    # Skip empty rows
    if not first_cell:
        return False

    # Skip header rows
    if first_cell.lower() in ["procedure", "visit", "visit short name", "study week", "visit window", "objectives",
                              "primary", "secondary", "exploratory"]:
        return False

    # Skip rows that look like table of contents or section numbers
    if re.match(r'^\d+(\.\d+)*\s', first_cell):  # Pattern like "10.3.4.1"
        return False

    # Skip rows with only dots or formatting
    if re.match(r'^[.\s]+$', first_cell):
        return False

    # Skip rows that are clearly not procedures
    skip_patterns = [
        r'^(to|the|a|an)\s+',  # starts with articles
        r'^(analysis|analyses)\s',
        r'appendix',
        r'^definitions?$',
        r'^notes?:?$',
        r'^abbreviations?:?$',
        r'\berror!\b',
        r'^[a-z]+\s*:$',  # single word followed by colon
    ]

    for pattern in skip_patterns:
        if re.search(pattern, first_cell, re.IGNORECASE):
            return False

    # Check if this row has any visit markers in subsequent columns
    # A valid procedure row should have at least one X marker
    has_markers = any(cell_has_marker(str(cell)) for cell in row[1:])

    return has_markers


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
        has_visits = any(any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row) for row in table_content)

        if buffer is None:
            buffer = table
            buffer_has_visits = has_visits
            continue

        if not has_visits:
            buffer["children"].extend(rows)
        else:
            if buffer_has_visits:
                merged.append(buffer)
                buffer = table
                buffer_has_visits = True
            else:
                buf_rows = find_nodes_by_name(buffer, "TR")
                table["children"] = buf_rows + table.get("children", [])
                buffer = table
                buffer_has_visits = True

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

    schedule_tables = []
    for table in merged_tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]

        # Check if this table has visit columns AND actual procedure rows
        has_visits = any(any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row) for row in table_content)
        has_procedures = any(is_valid_procedure_row(row) for row in table_content)

        if has_visits and has_procedures:
            schedule_tables.append(table)

    return schedule_tables


def parse_protocol_schedule(protocol_data):
    """Parse all multi-page schedule tables into schedule dict {visit: [procedures]} and visit order list."""
    schedule = {}
    tables = find_all_schedule_tables(protocol_data)

    if not tables:
        print("Error: No schedule tables found.")
        return None, None, None

    all_rows = []
    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        all_rows.extend([flatten_row(row) for row in rows])

    visit_row = next((row for row in all_rows if any(re.search(r'(?:V|P)\d+', str(cell)) for cell in row)), None)

    if not visit_row:
        print("Error: Could not find visit header row.")
        return None, None, None

    print("Found visit header row:", visit_row)

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

    # Track procedure order as they appear in the TABLE ROWS
    procedure_order = []

    for row in all_rows:
        if not is_valid_procedure_row(row):
            continue

        procedure = str(row[0]).strip()

        # Add to procedure order if not already present
        if procedure not in procedure_order:
            procedure_order.append(procedure)

        # Build schedule dictionary
        for i, visit_name in column_to_visit.items():
            cell_text = row[i] if i < len(row) else ""
            if cell_has_marker(cell_text):
                schedule.setdefault(visit_name, []).append(procedure)

    return schedule, visit_order, procedure_order


# -----------------------
# Function to save CSV with preserved order
# -----------------------

def save_schedule_to_csv(schedule, visit_order, procedure_order, output_path="schedule_output.csv"):
    """Converts the schedule dictionary to a wide-format DataFrame and saves as CSV."""
    if not schedule:
        print("Schedule is empty, not saving CSV.")
        return

    # Use the procedure_order from table parsing
    all_procedures = procedure_order
    all_visits = visit_order

    df = pd.DataFrame(index=all_procedures, columns=all_visits)
    df = df.fillna('')

    for visit, procedures in schedule.items():
        for proc in procedures:
            if proc in df.index:
                df.loc[proc, visit] = 'X'

    df.index.name = "Procedure"
    df.to_csv(output_path)
    print(f"\nSchedule successfully saved to '{output_path}'")
    print(f"Total procedures extracted: {len(all_procedures)}")


# ==============================================================================
# --- MAIN SCRIPT EXECUTION ---
# ==============================================================================

if __name__ == "__main__":
    file_path = "hierarchical_output_final.json"
    print(f"Processing file: {file_path}")

    try:
        protocol_json = load_json(file_path)
        schedule, visit_order, procedure_order = parse_protocol_schedule(protocol_json)

        if schedule:
            print("\nExtracted Schedule (Console View):")
            for visit in visit_order:
                print(f"\n{visit}:")
                for proc in schedule.get(visit, []):
                    print(f"  - {proc}")

            save_schedule_to_csv(schedule, visit_order, procedure_order)

        else:
            print("\nNo schedule extracted.")

    except FileNotFoundError:
        print(f"\nError: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
