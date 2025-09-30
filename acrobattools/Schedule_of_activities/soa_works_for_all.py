import json
import re
import sys
import pandas as pd

# -----------------------
# ENHANCED CONFIGURATION
# -----------------------
CONFIG = {
    # Enhanced visit pattern detection - ordered by specificity
    "VISIT_PATTERNS": [
        # Most specific patterns first
        r'S\d+D[\s-]?\d+[A-Za-z]*',  # S1D-2, S10D-1, S10D  2 a
        r'S\d*[xX]D[\s-]?\d+[A-Za-z]*',  # SxD-1, SxD1, S1D-2 b
        r'S[xX]D[\s-]?\d+[A-Za-z]*',  # SxD-1, SxD1, SxD2

        # Standard formats
        r'(?:V|P)\d+[A-Za-z]*',  # V1, V2, V19A, P3, P20c
        r'D\d+[A-Za-z]*',  # D1, D30, D90
        r'W\d+[A-Za-z]*',  # W1, W12, W24
        r'M\d+[A-Za-z]*',  # M1, M6, M12

        # Additional complex patterns
        r'[A-Z]\d+[A-Z]\d+[A-Za-z]*',  # T1D5, C2W3 type patterns
        r'CYCLE\s*\d+[A-Za-z]*',  # CYCLE 1, CYCLE2
        r'TREAT\s*\d+[A-Za-z]*',  # TREAT 1, TREAT2
        r'PERIOD\s*\d+[A-Za-z]*',  # PERIOD 1, PERIOD2

        # Generic patterns (last resort)
        r'[A-Z]{2,4}\d+[A-Za-z]*',  # ABC123, WXYZ4
    ],

    # Cell markers
    "CELL_MARKERS": [r'\b(?:X|YES|Y)\b', r'[✔✓●√■]'],

    # Keywords for additional validation
    "HEADER_KEYWORDS": ['visit', 'screening', 'week', 'day', 'baseline', 'follow.?up']
}


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
    """Return True if the cell text contains a schedule marker."""
    if not isinstance(text, str):
        return False

    for pattern in CONFIG["CELL_MARKERS"]:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def extract_complete_visit_identifier(text):
    """Extract the most complete visit identifier from text."""
    if not isinstance(text, str):
        return None

    # Clean the text first
    text = text.strip()

    # Try patterns in order of specificity (most specific first)
    for pattern in CONFIG["VISIT_PATTERNS"]:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Return the longest match (most complete)
            return max(matches, key=len)

    return None


def detect_visit_header_row(all_rows):
    """Find the row that contains the visit headers."""
    best_row = None
    best_score = 0

    for row_idx, row in enumerate(all_rows):
        if not row:
            continue

        visit_count = 0
        unique_visits = set()

        for cell in row:
            visit_id = extract_complete_visit_identifier(str(cell))
            if visit_id:
                visit_count += 1
                unique_visits.add(visit_id.upper())

        # Score based on number of unique visits found
        score = len(unique_visits)

        # Bonus for having "visit" or similar keywords
        row_text = ' '.join(str(cell).lower() for cell in row)
        for keyword in CONFIG["HEADER_KEYWORDS"]:
            if re.search(keyword, row_text):
                score += 2

        if score > best_score and score >= 3:  # At least 3 unique visits
            best_score = score
            best_row = row

    return best_row


def find_schedule_end(all_rows, column_to_visit, start_from=0):
    """Find where schedule procedures end."""
    procedure_count = 0
    consecutive_non_procedures = 0

    # Count total procedures first
    total_procedures = 0
    for i, row in enumerate(all_rows[start_from:], start_from):
        if not row:
            continue
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())
        if has_markers:
            total_procedures += 1

    print(f"🔍 Found {total_procedures} total rows with visit markers")

    # Look for natural end point
    for i, row in enumerate(all_rows[start_from:], start_from):
        if not row:
            continue

        first_cell = str(row[0]).strip()
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())

        if has_markers:
            procedure_count += 1
            consecutive_non_procedures = 0
        else:
            consecutive_non_procedures += 1

            if procedure_count >= 20 and consecutive_non_procedures > 15:
                print(f"📍 Found schedule end at row {i} ({procedure_count} procedures found)")
                return i

            # Check for section breaks
            if procedure_count >= 15:
                section_breaks = [
                    r'^Objectives$', r'^Primary$', r'^Secondary$', r'^Event type$',
                    r'^Participant analysis', r'^Laboratory assessments$',
                    r'Classification of', r'^Notes:$', r'^Endpoints?$'
                ]

                for pattern in section_breaks:
                    if re.match(pattern, first_cell, re.IGNORECASE):
                        print(f"📍 Found section break at row {i}: '{first_cell}' ({procedure_count} procedures)")
                        return i

    return len(all_rows)


def merge_broken_tables(tables):
    """Merge consecutive tables if the later one has no visit header row."""
    if not tables:
        return []

    merged = []
    buffer = None

    for table in tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]

        # Check if this table contains visit patterns
        has_visits = False
        for row in table_content:
            visit_count = sum(1 for cell in row if extract_complete_visit_identifier(str(cell)))
            if visit_count >= 2:  # At least 2 visit identifiers
                has_visits = True
                break

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


def find_all_schedule_tables(root):
    """Return all tables that belong to the schedule."""
    tables = find_nodes_by_name(root, "Table")
    merged_tables = merge_broken_tables(tables)

    schedule_tables = []
    for table in merged_tables:
        rows = find_nodes_by_name(table, "TR")
        table_content = [flatten_row(row) for row in rows]

        # Check if table contains visit patterns
        has_visit_patterns = False
        for row in table_content:
            visit_count = sum(1 for cell in row if extract_complete_visit_identifier(str(cell)))
            if visit_count >= 3:  # At least 3 visit identifiers
                has_visit_patterns = True
                break

        if has_visit_patterns:
            schedule_tables.append(table)

    return schedule_tables


def parse_protocol_schedule(protocol_data):
    """Parse schedule with enhanced visit pattern detection."""
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

    # Find visit header row using enhanced detection
    visit_row = detect_visit_header_row(all_rows)

    if not visit_row:
        print("❌ Could not find visit header row")
        return None, None, None

    print("✅ Found visit header row:",
          [str(cell)[:20] + "..." if len(str(cell)) > 20 else str(cell) for cell in visit_row[:10]])

    # Map column index -> visit name with duplicate handling
    column_to_visit = {}
    visit_order = []
    seen_visits = set()

    for i, cell in enumerate(visit_row):
        visit_id = extract_complete_visit_identifier(str(cell))
        if visit_id:
            # Handle duplicates by adding suffix
            original_visit = visit_id
            counter = 1
            while visit_id in seen_visits:
                visit_id = f"{original_visit}_{counter}"
                counter += 1

            column_to_visit[i] = visit_id
            visit_order.append(visit_id)
            seen_visits.add(visit_id)

    print(f"🎯 Detected {len(visit_order)} unique visits: {visit_order}")

    if len(visit_order) == 0:
        print("❌ No visit columns detected")
        return None, None, None

    # Find header row index
    header_row_index = -1
    for i, row in enumerate(all_rows):
        if row == visit_row:
            header_row_index = i
            break

    # Smart end detection
    end_index = find_schedule_end(all_rows, column_to_visit, header_row_index + 1)
    print(f"🎯 Processing rows {header_row_index + 1} to {end_index}")

    # Track procedure order
    procedure_order = []

    # Process rows
    for i, row in enumerate(all_rows[header_row_index + 1:end_index], header_row_index + 1):
        if not row:
            continue
        first_cell = str(row[0]).strip() if len(row) > 0 else ""

        # Skip header-like rows and visit identifiers
        if (not first_cell or
                first_cell.lower() in ["visit", "procedure", "study week", "visit window", "activity", "assessment"] or
                extract_complete_visit_identifier(first_cell)):
            continue

        procedure = first_cell

        # Only add if this row has visit markers
        has_markers = any(cell_has_marker(str(row[col])) if col < len(row) else False
                          for col in column_to_visit.keys())

        if has_markers:
            if procedure not in procedure_order:
                procedure_order.append(procedure)

            for col, visit_name in column_to_visit.items():
                cell_text = row[col] if col < len(row) else ""
                if cell_has_marker(cell_text):
                    schedule.setdefault(visit_name, []).append(procedure)

    return schedule, visit_order, procedure_order


def save_schedule_to_csv(schedule, visit_order, procedure_order, output_path="schedule_fixed_headers.csv"):
    """Save schedule to CSV with proper headers."""
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
    print(f"📊 Total visits: {len(visit_order)}")


# -----------------------
# Main script
# -----------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        file_path = "../structuring_protocol_json/hierarchical_output_final.json"
    else:
        file_path = sys.argv[1]

    print(f"🔍 Processing file: {file_path}")

    try:
        protocol_json = load_json(file_path)
        schedule, visit_order, procedure_order = parse_protocol_schedule(protocol_json)

        if schedule:
            print(f"\n✅ Successfully extracted schedule")
            print(f"📋 Visits detected: {visit_order}")
            print(f"📋 First 10 procedures:")
            for i, proc in enumerate(procedure_order[:10], 1):
                print(f"  {i:2d}. {proc}")

            save_schedule_to_csv(schedule, visit_order, procedure_order)

            print(f"\n📊 Visit summary:")
            for visit in visit_order:
                proc_count = len(schedule.get(visit, []))
                print(f"  {visit}: {proc_count} procedures")
        else:
            print("❌ No schedule extracted.")

    except FileNotFoundError:
        print(f"❌ Error: The file '{file_path}' was not found.")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
