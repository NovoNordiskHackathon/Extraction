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


def find_form_and_visit_pairs(node: dict, mapping: list):
    """
    Recursively traverses the JSON tree, identifies Form Headers (H1, H2, etc.),
    and searches their children for associated visits.
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

            # Extract form_name from square brackets [NAME] if present
            match = re.search(r'\[([^\]]+)\]', form_label)
            if match:
                form_name = match.group(1)
            else:
                # No square brackets: keep as Repeating/Non-repeating
                form_name = form_type

            mapping.append({
                "form_name": form_name,
                "form_label": form_label,
                "form_type": form_type,
                "visits": sorted(list(set(visits_for_this_form)), key=natural_sort_key)
            })
            print(f"  - Mapped Form: '{form_label}' ({form_type}) -> {list(set(visits_for_this_form))}")

    if "children" in node:
        for child in node["children"]:
            find_form_and_visit_pairs(child, mapping)


def create_schedule_from_json_hierarchy(json_path: str, output_excel_path: str):
    """Main function to process the hierarchical JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records = []
    print("Scanning JSON hierarchy for form-visit relationships...")
    find_form_and_visit_pairs(data, records)

    if not records:
        print("\n[Warning] No form-to-visit mappings were found.")
        return

    print("\n--- Final Mapping ---")
    for r in records:
        print(r)

    # Collect all unique visits
    all_visits = sorted({v for r in records for v in r["visits"]}, key=natural_sort_key)

    # Create DataFrame
    df = pd.DataFrame(columns=["form_name", "form_label"] + all_visits)
    for r in records:
        row = {"form_name": r["form_name"], "form_label": r["form_label"]}
        for v in all_visits:
            row[v] = 1 if v in r["visits"] else 0
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)

    # Save to Excel
    df.to_excel(output_excel_path, index=False)
    print(f"\n✅ Successfully created the schedule grid at '{output_excel_path}'")


# --- RUN ---
if __name__ == "__main__":
    try:
        json_file_path = "../hierarchical_1234_ Technical_Design_Sample_eCRF_Req.json"
        output_file_path = "50_trial_2.xlsx"

        if Path(json_file_path).exists():
            create_schedule_from_json_hierarchy(json_file_path, output_file_path)
        else:
            print(f"Error: Input file not found at '{json_file_path}'")

    except Exception as e:
        print(f"An error occurred: {e}")
