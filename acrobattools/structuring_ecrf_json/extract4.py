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

def extract_trigger_info(text):
    """Extract and clean trigger information using expanded strict patterns."""
    if not text or len(text.split()) < 4:  # Adjusted for shorter valid triggers
        return None

    # Expanded strict patterns for better coverage of your examples
    strict_trigger_patterns = [
        r'\bform\s+to\s+be\s+(dynamically\s+)?triggered\b',
        r'\b(dynamically\s+)?triggered\s+from\b',
        r'\bshould\s+trigger\b',
        r'\btrigger\s+only\s+for\b',
        r'\bform\s+should\s+trigger\b',
        r'\btrigger\s+at\s+every\s+required\s+visit\b',
        r'\bitem\s+to\s+trigger\b.*\bform\s+(to\s+appear|must\s+appear)\b',
        r'\btrigger\b.*\b(if|when|only\s+if)\b.*\b(response|marked\s+as|yes|no)\b',
        r'\bselect\s+event\s+type\s+to\s+trigger\b',
        r'\bdynamic\s+(to\s+be\s+triggered|should\s+be\s+triggered)\b',
        r'\btrigger\s+the\s+availability\b',
        r'\bdynamic\s+to\s+be\s+added\b.*\btrigger\b',
        r'\bform\s+must\s+appear\b',
        r'\brequired\s+only\s+for\b.*\bform\s+should\s+trigger\s+dynamically\b',
    ]

    # Exclusion patterns for false positives
    exclusion_patterns = [
        r'\b(not\s+trigger|does\s+not\s+trigger|no\s+trigger)\b',
        r'\b(hidden|date\s+of\s+birth|prefer\s+not\s+to)\b',
        r'\b(data\s+from|if\s+abnormal|if\s+yes\s+to)\b',
    ]

    # Check exclusions first
    for excl in exclusion_patterns:
        if re.search(excl, text, re.IGNORECASE):
            return None

    # Check for match in strict patterns
    for pattern in strict_trigger_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            trigger_text = re.sub(r'\s+', ' ', text.strip())
            if len(trigger_text) > 300:
                trigger_text = trigger_text[:297] + "..."
            return trigger_text

    return None

def is_valid_form_name(text):
    """Check if text is a valid form name using strict regex patterns."""
    if not text:
        return False

    form_name_pattern = re.compile(
        r'(?:'
        r'\[([A-Z0-9_\-]{3,})\]'  # Brackets with ALL CAPS, at least 3 chars
        r'|'
        r'.*\b(Non-)?[Rr]epeating\b.*'  # Contains repeating/non-repeating
        r')',
        re.IGNORECASE
    )

    match = form_name_pattern.search(text)
    if not match:
        return False

    if match.group(1):  # Bracketed match
        bracketed_content = match.group(1)
        if not bracketed_content.isupper():
            return False
        invalid_bracketed_patterns = [
            r'^L\d+$',  # L1, L2, etc.
            r'^[A-Z]\d+$',  # A1, B2, etc.
            r'^A\d+$',  # A200, etc.
        ]
        for pattern in invalid_bracketed_patterns:
            if re.match(pattern, bracketed_content):
                return False
        return True

    # Repeating match
    if len(text) < 10 or len(text) > 80:
        return False
    exclusion_patterns = [
        r'^(CRF|Form)\s+(Date|Time|Coordinator|Designer|Notes?).*',
        r'^\w{1,4}\s+(Date|Time|Coordinator|Designer)\b.*',
        r'^\s*(Date|Time|Coordinator|Designer)\s*-\s*(Non-)?[Rr]epeating.*',
    ]
    for pattern in exclusion_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    return True

def is_valid_form_label(text):
    """Check if text is a valid form label."""
    if not text or len(text) < 3 or len(text) > 100:
        return False
    invalid_patterns = [
        r'^\s*V\d+[A-Z]*\s*$',  # Just visit numbers
        r'Design\s*Notes?\s*:?$',
        r'Oracle\s*item\s*design\s*notes?\s*:?$',
        r'General\s*item\s*design\s*notes?\s*:?$',
        r'^\s*Non-Visit\s*Related\s*$',
        r'^Data from.*',
        r'^Hidden item.*',
        r'^The item.*',
        r'^\d+\s+',
        r'.*\|A\d+\|.*',
        r'^\s*(Non-)?[Rr]epeating(\s+form)?\s*$',
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, text, re.IGNORECASE):
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

def deep_search_triggers(node, max_depth=3, current_depth=0):
    """Recursively search for triggers with depth limit."""
    triggers = []
    if not isinstance(node, dict) or current_depth > max_depth:
        return triggers
    text = get_text(node)
    trigger_info = extract_trigger_info(text)
    if trigger_info:
        triggers.append({
            'text': trigger_info,
            'depth': current_depth
        })
    for child in node.get("children", []):
        triggers.extend(deep_search_triggers(child, max_depth, current_depth + 1))
    return triggers

def find_sibling_visits(node, siblings):
    """Find visits from sibling nodes."""
    visits = set()
    try:
        current_index = siblings.index(node)
        for i in range(max(0, current_index - 2), min(len(siblings), current_index + 3)):
            if i != current_index:
                sibling_visits = deep_search_visits(siblings[i])
                visits.update(sibling_visits)
    except ValueError:
        pass
    return visits

def find_next_h1_trigger(h1_sections, current_index):
    """Look for triggers in the next H1 section if none found."""
    if current_index + 1 >= len(h1_sections):
        return None
    next_h1 = h1_sections[current_index + 1]
    triggers = deep_search_triggers(next_h1)
    return triggers[0]['text'] if triggers else None

def extract_forms_with_recursive_triggers(data):
    """Extract forms with recursive trigger detection and strict validation."""
    results = []
    seen_forms = set()
    all_triggers = []
    h1_sections = []

    def gather_h1_sections(node):
        if not isinstance(node, dict):
            return
        if node.get('name', '').startswith('H1'):
            h1_sections.append(node)
        for child in node.get('children', []):
            gather_h1_sections(child)

    gather_h1_sections(data)

    for idx, h1_node in enumerate(h1_sections):
        h1_text = get_text(h1_node)
        if not is_valid_form_label(h1_text):
            h1_text = "Unknown Section"

        section_visits = deep_search_visits(h1_node)
        section_triggers = deep_search_triggers(h1_node)
        next_trigger = find_next_h1_trigger(h1_sections, idx)

        def find_forms_in_node(node, current_label=None, parent_siblings=None):
            if not isinstance(node, dict):
                return

            node_name = node.get("name", "")
            node_text = get_text(node)
            children = node.get("children", [])

            if node_name.startswith("H2") and is_valid_form_label(node_text) and not is_valid_form_name(node_text):
                current_label = node_text

            if is_valid_form_name(node_text):
                form_name = node_text
                form_label = current_label if current_label else h1_text
                visits_str = ", ".join(sorted(section_visits, key=lambda x: (
                    int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                    x
                )))
                form_key = (form_label, form_name, visits_str)  # Enhanced deduplication

                if form_key not in seen_forms:
                    form_visits = deep_search_visits(node)
                    if parent_siblings:
                        sibling_visits = find_sibling_visits(node, parent_siblings)
                        form_visits.update(sibling_visits)
                    if not form_visits:
                        form_visits = section_visits
                    visits_str = ", ".join(sorted(form_visits, key=lambda x: (
                        int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 9999,
                        x
                    )))

                    form_triggers = deep_search_triggers(node)
                    if parent_siblings:
                        try:
                            current_index = parent_siblings.index(node)
                            for i in range(max(0, current_index - 4), min(len(parent_siblings), current_index + 5)):
                                if i != current_index:
                                    sibling_triggers = deep_search_triggers(parent_siblings[i])
                                    form_triggers.extend(sibling_triggers)
                        except ValueError:
                            pass
                    if not form_triggers:
                        form_triggers = section_triggers
                    if not form_triggers and next_trigger:
                        form_triggers.append({'text': next_trigger, 'depth': 0})

                    # Deduplicate and validate triggers
                    unique_triggers = list(set(t['text'] for t in form_triggers if extract_trigger_info(t['text'])))
                    all_triggers.extend(unique_triggers)

                    has_trigger = len(unique_triggers) > 0
                    trigger_details = unique_triggers[0] if has_trigger else ""

                    results.append({
                        "Form Label": form_label,
                        "Form Name": form_name,
                        "Visits": visits_str,
                        "Dynamic Trigger": "Yes" if has_trigger else "No",
                        "Trigger Details": trigger_details
                    })
                    seen_forms.add(form_key)

            for child in children:
                find_forms_in_node(child, current_label, children)

        find_forms_in_node(h1_node, None, None)

    # Log total unique validated triggers
    unique_triggers = list(set(all_triggers))
    print(f"Total unique validated triggers detected: {len(unique_triggers)}")
    for t in unique_triggers:
        print(f"- {t}")

    return results

# Main execution
try:
    input_json_path = 'hierarchical_output_final3.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    extracted_forms = extract_forms_with_recursive_triggers(data)

    output_csv_path = 'extracted_forms_improved_v2.csv'
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["Form Label", "Form Name", "Visits", "Dynamic Trigger", "Trigger Details"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in extracted_forms:
            writer.writerow(row)

    print(f"Extracted {len(extracted_forms)} forms to {output_csv_path}")

    trigger_count = sum(1 for form in extracted_forms if form["Dynamic Trigger"] == "Yes")
    print(f"\nFound {trigger_count} forms with dynamic triggers:")

    for i, form in enumerate(extracted_forms):
        trigger_status = "🔄" if form["Dynamic Trigger"] == "Yes" else "📝"
        print(f"{i + 1}. {trigger_status} {form['Form Label']} | {form['Form Name']} | {form['Visits']}")
        if form["Dynamic Trigger"] == "Yes":
            print(f"   └─ Trigger: {form['Trigger Details'][:100]}...")
            print()

except Exception as e:
    print(f"Error: {e}")
