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


def deep_search_visits(node):
    """Recursively search all descendants for visit strings."""
    visits = set()
    if not isinstance(node, dict):
        return visits

    # Check current node
    text = get_text(node)
    visits.update(extract_visit_strings(text))

    # Recursively check all children and their descendants
    for child in node.get("children", []):
        visits.update(deep_search_visits(child))

    return visits


def deep_search_form_names(node, collected_forms, current_label=None):
    """Recursively search all descendants for form names (bracketed text with ALL CAPS)."""
    if not isinstance(node, dict):
        return

    name = node.get("name", "")
    text = get_text(node)

    # Check if this is a potential form label (H2 without brackets)
    if name.startswith("H2") and not re.search(r'\[([A-Z0-9_\-]+)\]', text):
        current_label = text

    # Check if this contains a form name (bracketed text with ALL CAPS requirement)
    form_name_match = re.search(r'\[([A-Z0-9_\-]+)\]', text)
    if form_name_match:
        # Additional check: ensure the content inside brackets is ALL CAPS
        bracketed_content = form_name_match.group(1)
        if bracketed_content.isupper():  # Only accept if ALL CAPS
            # Found a valid form name, collect all visits from the entire subtree
            visits = deep_search_visits(node)
            visits_str = ", ".join(sorted(visits, key=lambda x: (
                int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                x
            )))

            collected_forms.append({
                "Form Label": current_label if current_label else "",
                "Form Name": text,
                "Visits": visits_str
            })

    # Continue searching in all children
    for child in node.get("children", []):
        deep_search_form_names(child, collected_forms, current_label)


def extract_forms_exhaustively(data):
    """Extract forms with exhaustive recursive searching within each H1."""
    results = []

    def process_h1_section(h1_node):
        """Exhaustively process an H1 section to find all forms and visits."""
        h1_text = get_text(h1_node)
        section_forms = []

        # First, collect all visits from the entire H1 section
        all_h1_visits = deep_search_visits(h1_node)

        # Deep search for form names within this H1 section
        deep_search_form_names(h1_node, section_forms)

        # If no specific label was found for forms, use H1 text as fallback
        for form in section_forms:
            if not form["Form Label"]:
                form["Form Label"] = h1_text

            # If no visits found in the form's subtree, use H1 section visits
            if not form["Visits"]:
                visits_str = ", ".join(sorted(all_h1_visits, key=lambda x: (
                    int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                    x
                )))
                form["Visits"] = visits_str

        results.extend(section_forms)

    def find_h1_sections(node):
        """Find all H1 sections and process them."""
        if not isinstance(node, dict):
            return

        name = node.get("name", "")

        if name.startswith("H1"):
            process_h1_section(node)

        # Continue searching for more H1 sections
        for child in node.get("children", []):
            find_h1_sections(child)

    find_h1_sections(data)
    return results


def deep_search_with_context(node, parent_visits=None):
    """Enhanced deep search that also considers parent context for visits."""
    if not isinstance(node, dict):
        return [], set()

    if parent_visits is None:
        parent_visits = set()

    forms = []
    current_visits = set(parent_visits)

    name = node.get("name", "")
    text = get_text(node)

    # Collect visits from current node
    current_visits.update(extract_visit_strings(text))

    # Check if this is a form name (with ALL CAPS requirement)
    form_name_match = re.search(r'\[([A-Z0-9_\-]+)\]', text)
    if form_name_match:
        # Additional check: ensure the content inside brackets is ALL CAPS
        bracketed_content = form_name_match.group(1)
        if bracketed_content.isupper():  # Only accept if ALL CAPS
            # Collect all visits from this subtree
            subtree_visits = deep_search_visits(node)
            all_visits = current_visits.union(subtree_visits)

            visits_str = ", ".join(sorted(all_visits, key=lambda x: (
                int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                x
            )))

            forms.append({
                "Form Name": text,
                "Visits": visits_str,
                "Node": node  # Keep reference for label assignment
            })

    # Recursively process children
    for child in node.get("children", []):
        child_forms, child_visits = deep_search_with_context(child, current_visits)
        forms.extend(child_forms)
        current_visits.update(child_visits)

    return forms, current_visits


def extract_forms_with_full_context(data):
    """Extract forms with complete context awareness."""
    results = []

    def process_h1_with_context(h1_node):
        """Process H1 section with full context awareness."""
        h1_text = get_text(h1_node)

        # Get all forms from this H1 section with context
        forms, _ = deep_search_with_context(h1_node)

        # Assign form labels by looking for nearby H2 nodes
        for form in forms:
            form_node = form["Node"]
            form_label = h1_text  # Default to H1 text

            # Try to find a more specific label by traversing up and checking siblings
            def find_label_for_form(search_node, target_node):
                if not isinstance(search_node, dict):
                    return None

                children = search_node.get("children", [])
                for i, child in enumerate(children):
                    if child == target_node:
                        # Found the target, look backward for H2 label
                        for j in range(i - 1, -1, -1):
                            prev_child = children[j]
                            prev_name = prev_child.get("name", "")
                            prev_text = get_text(prev_child)
                            # Updated regex to only match ALL CAPS content
                            if prev_name.startswith("H2") and not re.search(r'\[([A-Z0-9_\-]+)\]', prev_text):
                                return prev_text
                        return None
                    else:
                        # Recursively search in children
                        result = find_label_for_form(child, target_node)
                        if result:
                            return result
                return None

            specific_label = find_label_for_form(h1_node, form_node)
            if specific_label:
                form_label = specific_label

            results.append({
                "Form Label": form_label,
                "Form Name": form["Form Name"],
                "Visits": form["Visits"]
            })

    def find_all_h1_sections(node):
        """Find and process all H1 sections."""
        if not isinstance(node, dict):
            return

        name = node.get("name", "")

        if name.startswith("H1"):
            process_h1_with_context(node)

        for child in node.get("children", []):
            find_all_h1_sections(child)

    find_all_h1_sections(data)
    return results


# Main execution
try:
    input_json_path = 'hierarchical_output_final3.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Use the enhanced extraction method
    extracted_forms = extract_forms_with_full_context(data)

    output_csv_path = 'extracted_forms_exhaustive3.csv'
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
