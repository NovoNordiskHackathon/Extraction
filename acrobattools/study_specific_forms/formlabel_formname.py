import json
import csv
import re


def find_forms(node, forms_list):
    """
    Recursively traverses the JSON structure to find form labels and names,
    handling multiple structural patterns and ignoring intermediate "visit strings".
    """
    if not isinstance(node, dict):
        return

    # A strict regex for valid form name identifiers (uppercase letters, numbers, underscores).
    form_name_regex = re.compile(r'^\[([A-Z0-9_X]+)\]')
    # Regex to identify and ignore visit strings (e.g., "V2", "V4D-1, V5")
    visit_string_regex = re.compile(r'^(V\d+[A-Z]?(-\d+)?([, ]+)?)+$')

    children = node.get("children", [])

    # Logic: Find a valid label (H2), then search forward through its siblings for the next valid name (H2).
    for i, child in enumerate(children):
        label_text = child.get("text", "").strip()

        # Condition 1: Is this child a potential Form Label?
        # It must be an H2 and must NOT be a form name or a visit string.
        if child.get("name", "").startswith("H2") and not form_name_regex.search(
                label_text) and not visit_string_regex.search(label_text):

            # Condition 2: Now, look ahead for the Form Name
            for j in range(i + 1, len(children)):
                next_node = children[j]
                next_text = next_node.get("text", "").strip()

                # If we hit another potential label before finding a name, stop searching.
                if next_node.get("name", "").startswith("H2") and not form_name_regex.search(
                        next_text) and not visit_string_regex.search(next_text):
                    break

                # If we find a valid Form Name, we have a pair.
                if next_node.get("name", "").startswith("H2") and form_name_regex.search(next_text):
                    form_name = next_text
                    form_label = label_text
                    if not any(d['Form Name'] == form_name for d in forms_list):
                        forms_list.append({"Form Label": form_label, "Form Name": form_name})
                    break  # Stop searching once the name is found for this label.

    # --- THIS IS THE FIX: Recurse into children to search the entire tree ---
    for child in children:
        find_forms(child, forms_list)


# --- Main execution ---
try:
    input_json_path = 'hierarchical_NNXXXX-4567_eCRF_Mockup_Part A.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    extracted_forms = []
    # Start the search from the root node.
    find_forms(data, extracted_forms)

    output_csv_path = 'form_data_4567.csv'
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["Form Name", "Form Label"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for form in extracted_forms:
            writer.writerow({'Form Name': form['Form Name'], 'Form Label': form['Form Label']})

    print(f"Successfully extracted {len(extracted_forms)} forms.")
    print(f"Data has been written to {output_csv_path}")

except FileNotFoundError:
    print(
        f"Error: The file '{input_json_path}' was not found. Please ensure it is in the same directory as the script.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
