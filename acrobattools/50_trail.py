# import json
# import re
# from pathlib import Path
# import pandas as pd
#
#
# def natural_sort_key(s: str):
#     """Creates a key for sorting strings in a natural, human-friendly order."""
#     return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
#
#
# # --- Regex patterns and excluded headers for filtering ---
# VISIT_PATTERN = re.compile(r'V\d+[A-Z]?\b|Screening|Main Study|Extension|End of Treatment|V-EOS')
# IS_ONLY_VISITS_PATTERN = re.compile(
#     r'^\s*((V\d+[A-Z]?\b|P\d+|Screening|Main Study|Extension|End of Treatment|V-EOS)[,\s]*)+\s*$')
#
# EXCLUDED_HEADERS = {
#     "Design Notes",
#     "Oracle item design notes:",
#     "General item design notes:",
#     "Key:",
#     "Integration:",
#     "Exclusion Criteria",
#     "Inclusion Criteria"
# }
#
#
# def find_visits_in_children(node: dict) -> list:
#     """Recursively search through a node's children to find a list of visits."""
#     visits_found = []
#     text = node.get("text", "").strip()
#
#     if IS_ONLY_VISITS_PATTERN.match(text):
#         visits_found.extend(VISIT_PATTERN.findall(text))
#
#     if "children" in node:
#         for child in node["children"]:
#             visits_found.extend(find_visits_in_children(child))
#
#     return list(set(visits_found))  # Return unique visits
#
#
# def find_form_and_visit_pairs(node: dict, mapping: list):
#     """
#     Recursively traverses the JSON tree, identifies Form Headers (H1, H2, etc.),
#     and searches their children for associated visits.
#     """
#     if node.get("name", "").startswith("H"):
#         text = node.get("text", "").strip()
#
#         if text and text not in EXCLUDED_HEADERS and not IS_ONLY_VISITS_PATTERN.match(text):
#             visits_for_this_form = []
#             form_type = "Non-repeating form"  # default
#
#             if "children" in node:
#                 for child in node["children"]:
#                     visits_for_this_form.extend(find_visits_in_children(child))
#
#                     # Detect repeating forms from child text
#                     child_text = child.get("text", "").lower()
#                     if "repeating" in child_text:
#                         form_type = "Repeating form"
#
#             # --- Always add the form, even if no visits ---
#             form_label = re.sub(r'\s*\(.*\)', '', text).strip()  # Clean label
#             form_name = form_label.replace(" ", "_").lower()      # Simple derived form_name
#
#             mapping.append({
#                 "form_name": form_name,
#                 "form_label": form_label,
#                 "form_type": form_type,
#                 "visits": sorted(list(set(visits_for_this_form)), key=natural_sort_key)  # may be empty
#             })
#             print(f"  - Mapped Form: '{form_label}' ({form_type}) -> {list(set(visits_for_this_form))}")
#
#     if "children" in node:
#         for child in node["children"]:
#             find_form_and_visit_pairs(child, mapping)
#
#
# def create_schedule_from_json_hierarchy(json_path: str, output_excel_path: str):
#     """Main function to process the hierarchical JSON."""
#     with open(json_path, 'r', encoding='utf-8') as f:
#         data = json.load(f)
#
#     records = []
#     print("Scanning JSON hierarchy for form-visit relationships...")
#     find_form_and_visit_pairs(data, records)
#
#     if not records:
#         print("\n[Warning] No form-to-visit mappings were found.")
#         return
#
#     print("\n--- Final Mapping ---")
#     for r in records:
#         print(r)
#
#     # Collect all unique visits
#     all_visits = sorted({v for r in records for v in r["visits"]}, key=natural_sort_key)
#
#     # Create DataFrame
#     df = pd.DataFrame(index=[r["form_label"] for r in records], columns=all_visits)
#     for r in records:
#         if r["visits"]:  # only set 1 for visits that exist
#             df.loc[r["form_label"], r["visits"]] = 1
#     df = df.fillna(0)
#
#     # Add extra columns for form_name and form_type
#     df.insert(0, "form_name", [r["form_name"] for r in records])
#     df.insert(1, "form_type", [r["form_type"] for r in records])
#
#     # Save to Excel
#     df.to_excel(output_excel_path, index=False)
#     print(f"\n✅ Successfully created the schedule grid at '{output_excel_path}'")
#
#
# # --- RUN ---
# if __name__ == "__main__":
#     try:
#         json_file_path = "hierarchical_1234_ Technical_Design_Sample_eCRF_Req.json"
#         output_file_path = "50_trial.xlsx"
#
#         if Path(json_file_path).exists():
#             create_schedule_from_json_hierarchy(json_file_path, output_file_path)
#         else:
#             print(f"Error: Input file not found at '{json_file_path}'")
#
#     except Exception as e:
#         print(f"An error occurred: {e}")
import json
import re
from pathlib import Path
import pandas as pd


def natural_sort_key(s: str):
    """Creates a key for sorting strings in a natural, human-friendly order."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


# --- Regex patterns and excluded headers for filtering ---
VISIT_PATTERN = re.compile(r'V\d+[A-Z]?\b|Screening|Main Study|Extension|End of Treatment|V-EOS')
IS_ONLY_VISITS_PATTERN = re.compile(
    r'^\s*((V\d+[A-Z]?\b|P\d+|Screening|Main Study|Extension|End of Treatment|V-EOS)[,\s]*)+\s*$')

EXCLUDED_HEADERS = {
    "Design Notes",
    "Oracle item design notes:",
    "General item design notes:",
    "Key:",
    "Integration:",
    "Exclusion Criteria",
    "Inclusion Criteria"
}


def find_visits_in_children(node: dict) -> list:
    """Recursively search through a node's children to find a list of visits."""
    visits_found = []
    text = node.get("text", "").strip()

    if IS_ONLY_VISITS_PATTERN.match(text):
        visits_found.extend(VISIT_PATTERN.findall(text))

    if "children" in node:
        for child in node["children"]:
            visits_found.extend(find_visits_in_children(child))

    return list(set(visits_found))  # Return unique visits


def find_form_and_visit_pairs(node: dict, mapping: list, seen_forms: set):
    """
    Recursively traverses the JSON tree, identifies Form Headers (H1, H2, etc.),
    and searches their children for associated visits. Avoids duplicates.
    """
    if node.get("name", "").startswith("H"):
        text = node.get("text", "").strip()

        if text and text not in EXCLUDED_HEADERS and not IS_ONLY_VISITS_PATTERN.match(text):
            visits_for_this_form = []
            form_type = "Non-repeating form"  # default

            if "children" in node:
                for child in node["children"]:
                    visits_for_this_form.extend(find_visits_in_children(child))
                    child_text = child.get("text", "").lower()
                    if "repeating" in child_text:
                        form_type = "Repeating form"

            form_label = re.sub(r'\s*\(.*\)', '', text).strip()
            form_name = form_label.replace(" ", "_").lower()

            # --- Only add if not already seen ---
            if form_name not in seen_forms:
                mapping.append({
                    "form_name": form_name,
                    "form_label": form_label,
                    "form_type": form_type,
                    "visits": sorted(list(set(visits_for_this_form)), key=natural_sort_key)
                })
                seen_forms.add(form_name)
                print(f"  - Mapped Form: '{form_label}' ({form_type}) -> {list(set(visits_for_this_form))}")

    if "children" in node:
        for child in node["children"]:
            find_form_and_visit_pairs(child, mapping, seen_forms)


def create_schedule_from_json_hierarchy(json_path: str, output_excel_path: str):
    """Main function to process the hierarchical JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    seen_forms = set()  # Track duplicates
    print("Scanning JSON hierarchy for form-visit relationships...")
    find_form_and_visit_pairs(data, records, seen_forms)

    if not records:
        print("\n[Warning] No form-to-visit mappings were found.")
        return

    print("\n--- Final Mapping ---")
    for r in records:
        print(r)

    # Collect all unique visits
    all_visits = sorted({v for r in records for v in r["visits"]}, key=natural_sort_key)

    # Create DataFrame
    df = pd.DataFrame(index=[r["form_label"] for r in records], columns=all_visits)
    for r in records:
        if r["visits"]:
            df.loc[r["form_label"], r["visits"]] = 1
    df = df.fillna(0)

    # Add extra columns for form_name and form_type
    df.insert(0, "form_name", [r["form_name"] for r in records])
    df.insert(1, "form_type", [r["form_type"] for r in records])

    # Save to Excel
    df.to_excel(output_excel_path, index=False)
    print(f"\n✅ Successfully created the schedule grid at '{output_excel_path}'")


# --- RUN ---
if __name__ == "__main__":
    try:
        json_file_path = "hierarchical_1234_ Technical_Design_Sample_eCRF_Req.json"
        output_file_path = "50_trial.xlsx"

        if Path(json_file_path).exists():
            create_schedule_from_json_hierarchy(json_file_path, output_file_path)
        else:
            print(f"Error: Input file not found at '{json_file_path}'")

    except Exception as e:
        print(f"An error occurred: {e}")
