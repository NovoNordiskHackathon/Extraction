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
# Add any other generic headers you want to ignore to this set
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


def find_form_and_visit_pairs(node: dict, mapping: dict):
    """
    Recursively traverses the JSON tree, identifies Form Headers (H1, H2, etc.),
    and searches their children for associated visits.
    """
    # --- GENERALIZED LOGIC ---
    # 1. Check if the element is a Heading
    if node.get("name", "").startswith("H"):
        text = node.get("text", "").strip()

        # 2. Check if the heading is a plausible form label
        if text and text not in EXCLUDED_HEADERS and not IS_ONLY_VISITS_PATTERN.match(text):

            # 3. If it is, search ALL its children for a list of visits
            if "children" in node:
                visits_for_this_form = []
                for child in node["children"]:
                    visits_for_this_form.extend(find_visits_in_children(child))

                if visits_for_this_form:
                    # 4. If visits were found, we have a valid mapping
                    form_label = re.sub(r'\s*\(.*\)', '', text).strip()  # Clean the label

                    if form_label not in mapping:
                        mapping[form_label] = []
                    mapping[form_label].extend(visits_for_this_form)
                    print(f"  - Mapped Form: '{form_label}' -> With Visits: {list(set(visits_for_this_form))}")

    # Continue the search deeper into the tree
    if "children" in node:
        for child in node["children"]:
            find_form_and_visit_pairs(child, mapping)


def create_schedule_from_json_hierarchy(json_path: str, output_excel_path: str):
    """Main function to process the hierarchical JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    form_to_visits_map = {}
    print("Scanning JSON hierarchy for form-visit relationships...")
    find_form_and_visit_pairs(data, form_to_visits_map)

    if not form_to_visits_map:
        print("\n[Warning] No form-to-visit mappings were found. Check the EXCLUDED_HEADERS set.")
        return

    print("\n--- Final Mapping ---")
    final_map = {}
    all_visits = set()
    for form, visits in form_to_visits_map.items():
        clean_form = form.replace('.', '').strip()
        unique_visits = sorted(list(set(visits)), key=natural_sort_key)
        final_map[clean_form] = unique_visits
        all_visits.update(unique_visits)

    print(final_map)

    # --- Create and save the Excel file ---
    sorted_forms = sorted(final_map.keys())
    sorted_visits = sorted(list(all_visits), key=natural_sort_key)

    df = pd.DataFrame(index=sorted_forms, columns=sorted_visits)

    for form, visits in final_map.items():
        if form in df.index:
            df.loc[form, visits] = 1

    df = df.fillna(0)

    df.to_excel(output_excel_path)
    print(f"\nSuccessfully created the schedule grid at '{output_excel_path}'")


# --- RUN THE SCRIPT ---
if __name__ == "__main__":
    try:
        json_file_path = ("../structuring_ecrf_json/hierarchical_output_final2.json")  # Change this to your actual filename
        output_file_path = "protocol_schedule_improved_final.xlsx"

        if Path(json_file_path).exists():
            create_schedule_from_json_hierarchy(json_file_path, output_file_path)
        else:
            print(f"Error: Input file not found at '{json_file_path}'")

    except Exception as e:
        print(f"An error occurred: {e}")