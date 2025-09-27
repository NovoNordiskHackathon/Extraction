import json
import re
from pathlib import Path
import pandas as pd


def natural_sort_key(s: str):
    """Creates a key for sorting strings in a natural, human-friendly order."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


# --- Excluded headers for filtering ---
EXCLUDED_HEADERS = {
    "Design Notes",
    "Oracle item design notes:",
    "General item design notes:",
    "Key:",
    "Integration:",
    "Exclusion Criteria",
    "Inclusion Criteria"
}


def find_form_pairs(node: dict, mapping: dict):
    """
    Recursively traverses the JSON tree and identifies Form Headers.
    """
    if node.get("name", "").startswith("H"):
        text = node.get("text", "").strip()
        if text and text not in EXCLUDED_HEADERS:
            specific_form_name = None
            form_type = "Non-repeating form"  # Default

            # Look for bracketed text in main node
            form_name_match = re.search(r'\[([^\]]+)\]', text)
            if form_name_match:
                specific_form_name = form_name_match.group(1).strip()

            # FIXED: Check for complete phrases instead of just "repeating"
            if "non-repeating form" in text.lower():
                form_type = "Non-repeating form"
            elif "repeating form" in text.lower():
                form_type = "Repeating form"

            # Check children for additional information
            if "children" in node:
                for child in node["children"]:
                    child_text = child.get("text", "")

                    # FIXED: Check for complete phrases in children too
                    if "non-repeating form" in child_text.lower():
                        form_type = "Non-repeating form"
                    elif "repeating form" in child_text.lower():
                        form_type = "Repeating form"

                    # Only look in children for bracketed names if not found in parent
                    if not specific_form_name:
                        child_name_match = re.search(r'\[([^\]]+)\]', child_text)
                        if child_name_match:
                            specific_form_name = child_name_match.group(1).strip()

            # Create a clean label for the form
            clean_label = re.sub(r'\s*\[[^\]]+\]', '', text)
            clean_label = re.sub(r'\s*\([^\)]+\)', '', clean_label).strip()

            # Combine bracketed name with form type if bracket exists
            if specific_form_name:
                output_form_name = f"{specific_form_name} - {form_type}"
                unique_key = specific_form_name
            else:
                output_form_name = form_type
                unique_key = clean_label

            # Store form data
            if unique_key not in mapping:
                mapping[unique_key] = {
                    "form_name_for_output": output_form_name,
                    "form_label": clean_label
                }
                print(f"  - Discovered Form (Key: '{unique_key}'): Label='{clean_label}', Name='{output_form_name}'")

    if "children" in node:
        for child in node["children"]:
            find_form_pairs(child, mapping)


def create_forms_list_from_json_hierarchy(json_path: str, output_excel_path: str):
    """Main function to process the hierarchical JSON and create a forms list."""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    form_data = {}
    print("Scanning JSON hierarchy for forms...")
    find_form_pairs(data, form_data)

    if not form_data:
        print("\n[Warning] No forms were found.")
        return

    # Create DataFrame with just form information
    df_records = []
    for unique_key, details in form_data.items():
        row = {
            "form_name": details["form_name_for_output"],
            "form_label": details["form_label"]
        }
        df_records.append(row)

    df = pd.DataFrame(df_records, columns=["form_name", "form_label"])
    df.to_excel(output_excel_path, index=False)
    print(f"\n✅ Successfully created the forms list at '{output_excel_path}'")


# --- RUN ---
if __name__ == "__main__":
    try:
        json_file_path = "hierarchical_output_final.json"
        output_file_path = "forms_list1.xlsx"

        if Path(json_file_path).exists():
            create_forms_list_from_json_hierarchy(json_path=json_file_path, output_excel_path=output_file_path)
        else:
            print(f"Error: Input file not found at '{json_file_path}'")
    except Exception as e:
        print(f"An error occurred: {e}")
