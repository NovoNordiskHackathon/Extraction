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


def is_valid_form_name(text):
    """Check if the bracketed text is a valid form name."""
    # Extract bracketed content
    form_name_match = re.search(r'\[([A-Z0-9_\-]+)\]', text)
    if not form_name_match:
        return False

    bracketed_content = form_name_match.group(1)

    # Must be all caps
    if not bracketed_content.isupper():
        return False

    # Exclude invalid patterns
    invalid_patterns = [
        r'^L\d+$',  # L1, L2, L3, etc.
        r'^[A-Z]\d+$',  # Single letter followed by numbers
        r'^AGI$',  # Short abbreviations that aren't form names
        r'^A\d+$',  # A200, etc.
    ]

    for pattern in invalid_patterns:
        if re.match(pattern, bracketed_content):
            return False

    # Must have meaningful length (at least 3 characters)
    if len(bracketed_content) < 3:
        return False

    # Should contain underscores or be reasonably long for form names
    if '_' not in bracketed_content and len(bracketed_content) < 4:
        return False

    return True


def is_valid_form_label(text):
    """Check if text is a valid form label."""
    if not text or len(text) < 3:
        return False

    # Exclude patterns that are not form labels
    invalid_patterns = [
        r'^\s*V\d+[A-Z]*\s*$',  # Just visit numbers
        r'Design\s*Notes?\s*:?$',
        r'Oracle\s*item\s*design\s*notes?\s*:?$',
        r'General\s*item\s*design\s*notes?\s*:?$',
        r'^\s*Non-Visit\s*Related\s*$',
        r'^Data from.*',  # Long descriptive text starting with "Data from"
        r'^Hidden item.*',  # Instructions starting with "Hidden item"
        r'^The item.*',  # Instructions starting with "The item"
        r'^\d+\s+',  # Text starting with numbers (eligibility criteria)
        r'.*\|A\d+\|.*',  # Text containing codes like |A200|
    ]

    for pattern in invalid_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False

    # Exclude very long text (likely instructions, not labels)
    if len(text) > 100:
        return False

    return True


def deep_search_visits(node):
    """Recursively search all descendants for visit strings."""
    visits = set()
    if not isinstance(node, dict):
        return visits

    text = get_text(node)
    visits.update(extract_visit_strings(text))

    for child in node.get("children", []):
        visits.update(deep_search_visits(child))

    return visits


def extract_forms_cleaned(data):
    """Extract forms with improved duplicate handling and validation."""
    results = []
    seen_forms = set()  # Track (form_label, form_name) pairs to avoid duplicates

    def process_h1_section(h1_node):
        """Process an H1 section to find valid forms."""
        h1_text = get_text(h1_node)
        if not is_valid_form_label(h1_text):
            h1_text = "Unknown Section"

        # Collect all visits from H1 section
        section_visits = deep_search_visits(h1_node)

        def find_forms_in_node(node, current_label=None):
            """Recursively find forms in a node."""
            if not isinstance(node, dict):
                return

            node_name = node.get("name", "")
            node_text = get_text(node)

            # Update current label if this is a valid H2 label
            if node_name.startswith("H2") and is_valid_form_label(node_text) and not is_valid_form_name(node_text):
                current_label = node_text

            # Check if this node contains a valid form name
            if is_valid_form_name(node_text):
                form_name = node_text
                form_label = current_label if current_label else h1_text

                # Create unique key for deduplication
                form_key = (form_label, form_name)

                if form_key not in seen_forms:
                    # Collect visits from form node and nearby context
                    form_visits = deep_search_visits(node)

                    # If no visits in form, use section visits
                    if not form_visits:
                        form_visits = section_visits

                    visits_str = ", ".join(sorted(form_visits, key=lambda x: (
                        int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                        x
                    )))

                    results.append({
                        "Form Label": form_label,
                        "Form Name": form_name,
                        "Visits": visits_str
                    })
                    seen_forms.add(form_key)

            # Recursively process children
            for child in node.get("children", []):
                find_forms_in_node(child, current_label)

        find_forms_in_node(h1_node)

    def find_h1_sections(node):
        """Find and process all H1 sections."""
        if not isinstance(node, dict):
            return

        name = node.get("name", "")

        if name.startswith("H1"):
            process_h1_section(node)

        for child in node.get("children", []):
            find_h1_sections(child)

    find_h1_sections(data)
    return results


# Main execution
try:
    input_json_path = 'hierarchical_output_final3.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Use the cleaned extraction method
    extracted_forms = extract_forms_cleaned(data)

    output_csv_path = 'extracted_forms_cleaned.csv'
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
