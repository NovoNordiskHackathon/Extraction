##WORKING CODE-BASE
# import json
# import pandas as pd
#
# # Load JSON
# with open("/home/ibab/novohackathon/Extraction/acrobattools/structuring_protocol_json/hierarchical_output_final.json", "r") as f:
#     doc = json.load(f)
#
# def find_all_soa_tables(node, soa_tables=None):
#     """Recursively find all SOA tables containing 'Procedure' in first row"""
#     if soa_tables is None:
#         soa_tables = []
#
#     if isinstance(node, dict):
#         if node.get("name", "").startswith("Table") and "children" in node:
#             for row in node["children"]:
#                 if "children" not in row or not row["children"]:
#                     continue
#                 first_cell = row["children"][0]
#                 if "children" in first_cell and first_cell["children"]:
#                     for p in first_cell["children"]:
#                         if p.get("text") and "Procedure" in p["text"]:
#                             soa_tables.append(node)
#                             break
#         # Recurse into children
#         for child in node.get("children", []):
#             find_all_soa_tables(child, soa_tables)
#     elif isinstance(node, list):
#         for item in node:
#             find_all_soa_tables(item, soa_tables)
#     return soa_tables
#
# def extract_visits_and_weeks(tables):
#     """Extract visit names and study weeks in protocol order"""
#     visit_names = []
#     study_weeks = []
#
#     for table in tables:
#         rows = table.get("children", [])
#         for i, row in enumerate(rows):
#             if "children" not in row:
#                 continue
#             first_cell = row["children"][0]
#             if not first_cell or "children" not in first_cell:
#                 continue
#             first_text = first_cell["children"][0].get("text", "").strip() if first_cell["children"] else ""
#
#             if first_text.lower().startswith("visit short name"):
#                 for cell in row["children"][1:]:
#                     if "children" in cell:
#                         for p in cell["children"]:
#                             txt = p.get("text", "").strip()
#                             if txt and txt not in visit_names:
#                                 visit_names.append(txt)
#             elif first_text.lower().startswith("study week"):
#                 for cell in row["children"][1:]:
#                     if "children" in cell:
#                         for p in cell["children"]:
#                             txt = p.get("text", "").strip()
#                             if txt:
#                                 study_weeks.append(txt)
#
#     # Ensure lengths match
#     min_len = min(len(visit_names), len(study_weeks))
#     visit_names = visit_names[:min_len]
#     study_weeks = study_weeks[:min_len]
#
#     # Convert Study Week to numeric
#     study_weeks_numeric = []
#     for w in study_weeks:
#         try:
#             study_weeks_numeric.append(int(''.join(filter(lambda x: x in '-0123456789', w))))
#         except:
#             study_weeks_numeric.append(None)
#
#     # Remove any None rows
#     clean_data = [(v, w) for v, w in zip(visit_names, study_weeks_numeric) if w is not None]
#
#     df = pd.DataFrame(clean_data, columns=['Visit Name', 'Study Week'])
#     return df
#
# # Step 1: Find all SOA tables
# soa_tables = find_all_soa_tables(doc)
# if not soa_tables:
#     raise Exception("❌ No SOA tables found (no row starting with 'Procedure')")
#
# print(f"✅ Found {len(soa_tables)} SOA table(s)")
#
# # Step 2: Extract visits and study weeks in protocol order
# soa_df = extract_visits_and_weeks(soa_tables)
# print("✅ Visits extracted in protocol order:")
# print(soa_df)
#
# # Step 3: Remove duplicates (keep first occurrence)
# soa_df = soa_df.drop_duplicates(subset=['Visit Name', 'Study Week']).reset_index(drop=True)
#
# # Step 4: Calculate Offset Days (Study Week * 7)
# soa_df['Offset Days'] = soa_df['Study Week'] * 7
#
# # Step 5: Apply ±3 days Visit Window
# soa_df['Visit Window Start'] = soa_df['Offset Days'] - 3
# soa_df['Visit Window End'] = soa_df['Offset Days'] + 3
#
# # Step 6: Reorder columns
# final_df = soa_df[['Visit Name', 'Study Week', 'Offset Days', 'Visit Window Start', 'Visit Window End']]
#
# # ✅ Optional: save to Excel
# final_df.to_excel("/home/ibab/novohackathon/Extraction/soa_visits.xlsx", index=False)
#
# print("✅ Final SOA visits with offsets and windows:")
# print(final_df)

#FINAL WORKING CODE
import json
import pandas as pd
import re

# Load JSON
with open("/home/ibab/novohackathon/Extraction/acrobattools/structuring_protocol_json/hierarchical_output_final.json", "r") as f:
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
        return None
    base, suffix = m.groups()
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

# Main
soa_tables = find_all_soa_tables(doc)
soa_df = extract_visits_and_weeks(soa_tables)

# Keep first occurrence only (no duplicates)
soa_df = soa_df.drop_duplicates(subset=['Visit Name']).reset_index(drop=True)


# Offset Days & Visit Window
soa_df['Offset Days'] = soa_df['Study Week'] * 7
soa_df['Visit Window Start'] = soa_df['Offset Days'] - 3
soa_df['Visit Window End'] = soa_df['Offset Days'] + 3

# ------------------- Add Offset Type -------------------
offset_types = []
for i, row in soa_df.iterrows():
    if i == 0:
        offset_types.append("Specific: V1 a")  # first visit
    else:
        offset_types.append("Previous")

soa_df['Offset Type'] = offset_types
# --------------------------------------------------------

# Reorder and rename columns for final Excel
final_df = soa_df[['Visit Name', 'Study Week', 'Offset Days', 'Offset Type',
                   'Visit Window Start', 'Visit Window End']].copy()

final_df.rename(columns={
    'Visit Window Start': 'Day Range - Early',
    'Visit Window End': 'Day Range - Late'
}, inplace=True)

# ✅ Save to Excel
final_df.to_excel("/home/ibab/novohackathon/sched_grid_top/soa_visits.xlsx", index=False)

print("✅ Final SOA visits with Offset Type and Day Ranges:")
print(final_df)
