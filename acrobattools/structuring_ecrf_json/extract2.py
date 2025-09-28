import json
import csv
import re


def get_text(node):
    """Extract text from a node safely."""
    if not isinstance(node, dict):
        return ""
    return (node.get("text") or "").strip()


def extract_visit_strings(text):
    """Extract visit patterns like V1, V2, V19A, etc. from text."""
    visit_pattern = re.compile(r'V\d+[A-Z]*(?:-\d+)?')
    return visit_pattern.findall(text)


def clean_form_name(text):
    """Clean form name by removing repeating artifacts."""
    text = re.sub(r'(\s*-\s*Non-repeating(\s+form)?)+', ' - Non-repeating form', text, flags=re.IGNORECASE)
    text = re.sub(r'(\s*-\s*Repeating)+', ' - Repeating', text, flags=re.IGNORECASE)
    text = re.sub(r'\s+', ' ', text)  # Remove extra whitespace
    return text.strip()


def is_form_name(text):
    """Check if text contains a bracketed form name or specific form patterns."""
    # Look for bracketed names or specific patterns
    return bool(re.search(r'\[([A-Za-z0-9_\-]+)\]', text)) or \
        bool(re.search(r'(Non-repeating|Repeating)\s+(form)', text, re.IGNORECASE)) or \
        bool(re.search(r'^\s*[A-Z_]+\s*-\s*(Non-)?[Rr]epeating', text))


def is_form_label(text):
    """Check if text is a potential form label."""
    if not text or len(text) < 3:
        return False
    exclude_patterns = [
        r'^\s*V\d+[A-Z]*\s*$',  # Just visit numbers
        r'Design\s*Notes?\s*:?$',
        r'Oracle\s*item\s*design\s*notes?\s*:?$',
        r'General\s*item\s*design\s*notes?\s*:?$',
        r'^\s*Non-Visit\s*Related\s*$',
        r'^\s*(Non-)?[Rr]epeating(\s+form)?\s*$'
    ]
    for pattern in exclude_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    return True


def extract_forms_universal(data):
    """Universal form extraction that handles multiple JSON structures."""
    results = []

    def collect_visits_recursive(node):
        """Recursively collect all visit strings from a node."""
        visits = set()
        if isinstance(node, dict):
            text = get_text(node)
            visits.update(extract_visit_strings(text))
            for child in node.get("children", []):
                visits.update(collect_visits_recursive(child))
        return visits

    def process_any_section(section_node, section_label=None):
        """Process any section (H1, H2, etc.) to find forms."""
        section_text = get_text(section_node)
        if not section_label:
            section_label = section_text

        section_children = section_node.get("children", [])
        section_visits = collect_visits_recursive(section_node)

        # Look for form patterns in children
        i = 0
        current_form_label = section_label

        while i < len(section_children):
            child = section_children[i]
            child_name = child.get("name", "")
            child_text = get_text(child)

            # Check if this is a header that could be a form label or contain form info
            if child_name.startswith(("H", "Aside")):  # Include "Aside" nodes as they may contain visit info
                if is_form_name(child_text):
                    # This is a form name
                    form_name = clean_form_name(child_text)
                    form_label = current_form_label

                    # Collect visits from this form and nearby context
                    form_visits = collect_visits_recursive(child)

                    # Also check nearby siblings for visit info
                    for k in range(max(0, i - 2), min(len(section_children), i + 3)):
                        if k != i:
                            sibling = section_children[k]
                            sibling_visits = collect_visits_recursive(sibling)
                            form_visits.update(sibling_visits)

                    # If still no visits, use section visits
                    if not form_visits:
                        form_visits = section_visits

                    visits_str = ", ".join(sorted(form_visits, key=lambda x: (
                        int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999, x
                    )))

                    # Avoid duplicates
                    if not any(f["Form Name"] == form_name and f["Form Label"] == form_label for f in results):
                        results.append({
                            "Form Label": form_label,
                            "Form Name": form_name,
                            "Visits": visits_str
                        })

                elif is_form_label(child_text) and not is_form_name(child_text):
                    # This could be a new form label
                    current_form_label = child_text

                # Recursively process this child as well
                process_any_section(child, current_form_label)

            i += 1

    def find_all_sections(node):
        """Find and process all sections recursively."""
        if not isinstance(node, dict):
            return

        name = node.get("name", "")

        # Process any header node as a potential section
        if name.startswith(("H1", "H2", "H3")):
            process_any_section(node)

        # Continue searching for more sections
        for child in node.get("children", []):
            find_all_sections(child)

    find_all_sections(data)
    return results


# Main execution
try:
    input_json_path = 'hierarchical_output_final3.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    extracted_forms = extract_forms_universal(data)

    output_csv_path = 'extracted_forms_final_universal3.csv'
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["Form Label", "Form Name", "Visits"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in extracted_forms:
            writer.writerow(row)

    print(f"Extracted {len(extracted_forms)} forms to {output_csv_path}")

    # Display results
    for i, form in enumerate(extracted_forms):
        print(f"{i + 1}. {form['Form Label']} | {form['Form Name']} | {form['Visits']}")

except Exception as e:
    print(f"Error: {e}")
