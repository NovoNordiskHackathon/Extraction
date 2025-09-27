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


def find_visits_in_children(node: dict) -> set:
    """Recursively search through a node's children to find a set of visits."""
    visits_found = set()
    text = node.get("text", "").strip()

    if IS_ONLY_VISITS_PATTERN.match(text):
        visits_found.update(VISIT_PATTERN.findall(text))

    if "children" in node:
        for child in node["children"]:
            visits_found.update(find_visits_in_children(child))

    return visits_found


def find_form_and_visit_pairs(node: dict, mapping: dict):
    """
    Recursively traverses the JSON tree, identifies Form Headers, and aggregates
    visit information by a truly unique identifier.
    """
    if node.get("name", "").startswith("H"):
        text = node.get("text", "").strip()

        if text and text not in EXCLUDED_HEADERS and not IS_ONLY_VISITS_PATTERN.match(text):

            specific_form_name = None
            form_type = "Non-repeating form"
            visits_for_this_form = set()

            # Discover specific name, form type, and visits
            form_name_match = re.search(r'\[([^\]]+)\]', text)
            if form_name_match:
                specific_form_name = form_name_match.group(1).strip()

            if "children" in node:
                for child in node["children"]:
                    visits_for_this_form.update(find_visits_in_children(child))
                    child_text = child.get("text", "")
                    if "repeating" in child_text.lower():
                        form_type = "Repeating form"
                    if not specific_form_name:
                        child_name_match = re.search(r'\[([^\]]+)\]', child_text)
                        if child_name_match:
                            specific_form_name = child_name_match.group(1).strip()

            # --- CRITICAL LOGIC CHANGE ---
            # 1. Create a clean label for the form.
            clean_label = re.sub(r'\s*\[[^\]]+\]', '', text)
            clean_label = re.sub(r'\s*\([^\)]+\)', '', clean_label).strip()

            # 2. Determine the truly unique key for aggregation.
            #    If a specific [NAME] exists, use it.
            #    Otherwise, use the form's clean label to ensure it's unique.
            unique_key = specific_form_name if specific_form_name else clean_label

            # 3. Determine what to display in the final 'form_name' column.
            output_form_name = specific_form_name if specific_form_name else form_type

            # Use the unique_key to aggregate data correctly.
            if unique_key not in mapping:
                mapping[unique_key] = {
                    "form_name_for_output": output_form_name,
                    "form_label": clean_label,
                    "visits": visits_for_this_form
                }
                print(f"  - Discovered Form (Key: '{unique_key}'): Label='{clean_label}', Name='{output_form_name}'")
            else:
                mapping[unique_key]["visits"].update(visits_for_this_form)
                print(f"  - Updated Form (Key: '{unique_key}'): Added Visits {visits_for_this_form}")

    if "children" in node:
        for child in node["children"]:
            find_form_and_visit_pairs(child, mapping)


def create_schedule_from_json_hierarchy(json_path: str, output_excel_path: str):
    """Main function to process the hierarchical JSON and create a schedule of activities."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    form_data = {}
    print("Scanning JSON hierarchy for form-visit relationships...")
    find_form_and_visit_pairs(data, form_data)

    if not form_data:
        print("\n[Warning] No form-to-visit mappings were found.")
        return

    all_visits = set()
    for data_dict in form_data.values():
        all_visits.update(data_dict["visits"])
    sorted_visits = sorted(list(all_visits), key=natural_sort_key)

    df_records = []
    for unique_key, details in form_data.items():
        row = {
            "form_name": details["form_name_for_output"],
            "form_label": details["form_label"]
        }
        for visit in sorted_visits:
            row[visit] = 1 if visit in details["visits"] else 0
        df_records.append(row)

    df = pd.DataFrame(df_records, columns=["form_name", "form_label"] + sorted_visits)
    df.to_excel(output_excel_path, index=False)
    print(f"\n✅ Successfully created the schedule grid at '{output_excel_path}'")


# --- RUN ---
if __name__ == "__main__":
    try:
        json_file_path = "hierarchical_1234_ Technical_Design_Sample_eCRF_Req.json"
        output_file_path = "50_trial_4.xlsx"

        if Path(json_file_path).exists():
            create_schedule_from_json_hierarchy(json_file_path, output_file_path)
        else:
            print(f"Error: Input file not found at '{json_file_path}'")

    except Exception as e:
        print(f"An error occurred: {e}")