# FINAL WORKING CODE
import json
import pandas as pd
import re

# Load JSON
with open("/home/ibab/novohackathon/Extraction/acrobattools/structuring_protocol_json/hierarchical_output_final.json",
          "r") as f:
    doc = json.load(f)


# Recursively find SOA tables
def find_all_soa_tables(node, soa_tables=None):
    if soa_tables is None:
        soa_tables = []
    if isinstance(node, dict):
        if node.get("name", "").startswith("Table") and "children" in node:
            for row in node["children"]:
                if "children" not in row or not row["children"]:
                    continue
                first_cell = row["children"][0]
                if "children" in first_cell and first_cell["children"]:
                    for p in first_cell["children"]:
                        if p.get("text") and "Procedure" in p["text"]:
                            soa_tables.append(node)
                            break
        for child in node.get("children", []):
            find_all_soa_tables(child, soa_tables)
    elif isinstance(node, list):
        for item in node:
            find_all_soa_tables(item, soa_tables)
    return soa_tables


# Normalize visit names and filter unwanted ones
def normalize_visit_name(v):
    m = re.match(r'^([VP]\d+)(?:\s([a-zA-Z]+))?$', v.strip())
    if not m:
        # Keep specific names like P20 even if they don't match the V1/P1 pattern
        if v.strip().upper() in ['P20']:
            return v.strip().upper()
        return None
    base, suffix = m.groups()
    # Normalize P20 as well if it comes in as P20
    if base.upper() == 'P20':
        return 'P20'
    if suffix:
        if len(suffix) == 1:  # single-letter suffix → normalize
            return base
        else:  # multi-letter suffix → remove completely
            return None
    return base


# Extract visits and study weeks
def extract_visits_and_weeks(tables):
    visit_names = []
    study_weeks = []

    for table in tables:
        rows = table.get("children", [])
        for row in rows:
            if "children" not in row:
                continue
            first_cell = row["children"][0]
            if not first_cell or "children" not in first_cell:
                continue
            first_text = first_cell["children"][0].get("text", "").strip() if first_cell["children"] else ""

            if first_text.lower().startswith("visit short name"):
                for cell in row["children"][1:]:
                    if "children" in cell:
                        for p in cell["children"]:
                            txt = p.get("text", "").strip()
                            norm = normalize_visit_name(txt)
                            if norm:  # only keep valid normalized names
                                visit_names.append(norm)
            elif first_text.lower().startswith("study week"):
                for cell in row["children"][1:]:
                    if "children" in cell:
                        for p in cell["children"]:
                            txt = p.get("text", "").strip()
                            try:
                                study_weeks.append(int(''.join(filter(lambda x: x in '-0123456789', txt))))
                            except:
                                study_weeks.append(None)

    # Align lengths after filtering
    min_len = min(len(visit_names), len(study_weeks))
    visit_names = visit_names[:min_len]
    study_weeks = study_weeks[:min_len]

    df = pd.DataFrame({'Visit Name': visit_names, 'Study Week': study_weeks})
    return df


# ------------------- NEW FUNCTIONS FOR EVENT GROUP -------------------
def find_element_by_text(data, text_to_find):
    """Recursively search the JSON for an element containing specific text."""
    if isinstance(data, dict):
        if text_to_find.lower() in data.get('text', '').lower():
            return data
        for child in data.get('children', []):
            found = find_element_by_text(child, text_to_find)
            if found: return found
    elif isinstance(data, list):
        for item in data:
            found = find_element_by_text(item, text_to_find)
            if found: return found
    return None


def extract_extension_week(doc):
    """Finds the 'Study rationale' section and extracts the extension week number."""
    rationale_section = find_element_by_text(doc, "Study rationale")
    if rationale_section:
        full_text = json.dumps(rationale_section)
        # Look for a pattern like "64 weeks on treatment"
        match = re.search(r'(\d+)\s*weeks on treatment', full_text, re.IGNORECASE)
        if match:
            week = int(match.group(1))
            print(f"✅ Found extension start at {week} weeks.")
            return week
    print("⚠️ Warning: Could not determine extension start week from JSON. Check 'Study rationale' section.")
    return float('inf')  # Return a very large number if not found, so nothing is classed as 'Extension'


def get_event_group(row, extension_start_week):
    """Classifies a visit into an Event Group based on hardcoded rules and logic."""
    visit_name = row['Visit Name']
    study_week = row['Study Week']

    # 1. Apply hardcoded rules first
    if visit_name == 'V1': return 'Screening'
    if visit_name == 'V2': return 'Randomisation'
    if visit_name == 'V19': return 'End of Treatment'
    if visit_name == 'P20': return 'Follow up'
    if visit_name == 'V21': return 'End of Study'  # EOS

    # 2. Apply logic-based rules for remaining visits
    if study_week >= extension_start_week:
        return 'Extension'
    else:
        return 'Main Study'


# --------------------------------------------------------------------

# Main
soa_tables = find_all_soa_tables(doc)
soa_df = extract_visits_and_weeks(soa_tables)

# Keep first occurrence only (no duplicates)
soa_df = soa_df.drop_duplicates(subset=['Visit Name']).reset_index(drop=True)

# ------------------- Add Event Group Column -------------------
extension_start_week = extract_extension_week(doc)
soa_df['Event Group'] = soa_df.apply(get_event_group, axis=1, extension_start_week=extension_start_week)
# ---------------------------------------------------------------

# Offset Days & Visit Window
soa_df['Offset Days'] = soa_df['Study Week'] * 7
soa_df['Visit Window Start'] = soa_df['Offset Days'] - 3
soa_df['Visit Window End'] = soa_df['Offset Days'] + 3

# Add Offset Type
offset_types = []
for i, row in soa_df.iterrows():
    if i == 0:
        offset_types.append("Specific: V1 a")  # first visit
    else:
        offset_types.append("Previous")
soa_df['Offset Type'] = offset_types

# Reorder and rename columns for final Excel
final_df = soa_df[['Event Group', 'Visit Name', 'Study Week', 'Offset Days', 'Offset Type',
                   'Visit Window Start', 'Visit Window End']].copy()

final_df.rename(columns={
    'Visit Window Start': 'Day Range - Early',
    'Visit Window End': 'Day Range - Late'
}, inplace=True)

# ✅ Save to Excel
final_df.to_excel("/home/ibab/novohackathon/sched_grid_top/soa_visits_with_groups.xlsx", index=False)

print("\n✅ Final SOA visits with Event Group, Offset Type, and Day Ranges:")
print(final_df)
