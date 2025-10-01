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


def determine_form_source(form_name, form_text="", context_text="", document_context=""):
    """
    Determine the source of a form based on naming patterns, context, and document analysis.
    Returns: "Library", "New", or "Ref. Study"
    """
    # Clean the form name by removing brackets and extracting the core name
    clean_name = re.sub(r'[\[\]()]', '', form_name).strip()
    clean_name = re.sub(r'\s*–.*', '', clean_name)  # Remove descriptions after dash
    clean_name = re.sub(r'\s*-\s*(Non-)?[Rr]epeating.*', '', clean_name)  # Remove repeating indicators
    # Extract the base form name (before any numbers or suffixes)
    base_form_match = re.match(r'([A-Z][A-Z_]*?)(?:_\d+|_[A-Z]+|\d+)?(?:\s|$)', clean_name.upper())
    base_form_name = base_form_match.group(1) if base_form_match else clean_name.upper()
    # Combine all text for comprehensive analysis
    all_text = f"{form_name} {form_text} {context_text} {document_context}".lower()
    # === REFERENCE STUDY INDICATORS ===
    ref_study_patterns = [
        r'\bref\.?\s+study\b', r'\breference\s+study\b', r'\bborrowed\s+from\b',
        r'\badapted\s+from\b', r'\bprevious\s+study\b', r'\bderived\s+from\b'
    ]
    if any(re.search(pattern, all_text) for pattern in ref_study_patterns):
        return "Ref. Study"
    # === NEW FORM INDICATORS ===
    new_form_patterns = [r'_\d+$', r'\d+$', r'_[A-Z]+\d+$', r'_V\d+$']
    if any(re.search(pattern, clean_name.upper()) for pattern in new_form_patterns):
        return "New"
    new_context_patterns = [
        r'\bstudy[- ]specific\b', r'\bcustom\b', r'\bmodified\b', r'\btailored\b',
        r'\bprotocol[- ]specific\b', r'\bthis\s+study\s+only\b', r'\bspecial\s+requirements?\b'
    ]
    if any(re.search(pattern, all_text) for pattern in new_context_patterns):
        return "New"
    # === LIBRARY FORM INDICATORS ===
    library_context_patterns = [
        r'\bstandard\s+crf\b', r'\bnon[- ]?repeating\s+form\b', r'\brepeating\s+form\b',
        r'\bstandard\s+form\b', r'\bcommon\s+form\b', r'\bbaseline\b',
        r'\bfollow[- ]up\b', r'\bstandardized\b', r'\btemplate\b'
    ]
    if any(re.search(pattern, all_text) for pattern in library_context_patterns):
        return "Library"
    # === COMPREHENSIVE STANDARD FORM DATABASE ===
    standard_domains = {
        'DEMOGRAPHY', 'DEMO', 'INCLUSION', 'EXCLUSION', 'ELIGIBILITY', 'INFORMED_CONSENT', 'ICF',
        'MEDICAL_HISTORY', 'MEDHIST', 'PHYSICAL_EXAM', 'PE', 'VITAL_SIGNS', 'VITALS', 'VS',
        'LAB', 'LABORATORY', 'ECG', 'EKG', 'AE', 'ADVERSE_EVENT', 'SAE', 'CONMED', 'PRIOR_MED',
        'DOSE', 'PROCEDURE', 'PHQ', 'CSSRS', 'C_SSRS', 'PREGNANCY', 'TOBACCO', 'ALCOHOL',
        'SAMPLE', 'RANDOMIZATION', 'VISIT', 'SCHEDULE', 'WITHDRAWAL', 'END_OF_STUDY',
        'PK', 'PD', 'DEVICE', 'MRI', 'CT', 'ASSESSMENT', 'EVALUATION', 'QUESTIONNAIRE'
    }
    if base_form_name in standard_domains:
        return "Library"
    if any(domain in base_form_name or base_form_name in domain for domain in standard_domains):
        return "New" if re.search(r'_\d+$', clean_name.upper()) else "Library"
    # === DEFAULT CLASSIFICATION LOGIC ===
    if re.match(r'^[A-Z][A-Z0-9_]*$', clean_name.upper()):
        return "Library" if len(base_form_name) <= 15 else "New"
    if re.search(r'[a-z]', clean_name) or re.search(r'[^A-Z0-9_]', clean_name):
        return "New"
    return "Library"


def extract_trigger_info(text):
    """Extract and clean trigger information using comprehensive strict patterns."""
    if not text or len(text.split()) < 4:
        return None
    strict_trigger_patterns = [
        r'\bform\s+to\s+be\s+(dynamically\s+)?triggered\b', r'\b(dynamically\s+)?triggered\s+from\b',
        r'\bshould\s+trigger\b', r'\btrigger\s+only\s+for\b', r'\bform\s+should\s+trigger\b',
        r'\bitem\s+to\s+trigger\b.*\bform\s+(to\s+appear|must\s+appear)\b', r'\bform\s+must\s+appear\b',
        r'\btrigger\b.*\b(if|when|only\s+if)\b.*\b(response|marked\s+as|yes|no)\b',
        r'\bdynamic\s+(to\s+be\s+triggered|should\s+be\s+triggered)\b',
        r'\bsupporting\s+text\b.*\btrigger\s+dynamically\b'
    ]
    exclusion_patterns = [
        r'\b(not\s+trigger|does\s+not\s+trigger|no\s+trigger)\b', r'\b(hidden|date\s+of\s+birth)\b',
        r'\bif\s+medication\s+is\s+taken\b',
    ]
    if any(re.search(excl, text, re.IGNORECASE) for excl in exclusion_patterns):
        return None
    for pattern in strict_trigger_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            trigger_text = re.sub(r'\s+', ' ', text.strip())
            return trigger_text[:297] + "..." if len(trigger_text) > 300 else trigger_text
    return None


def is_valid_form_name(text):
    """Check if text is a valid form name using strict regex patterns."""
    if not text:
        return False
    form_name_pattern = re.compile(
        r'(?:\[([A-Z0-9_\-]{3,})\]|.*\b(Non-)?[Rr]epeating\b.*)', re.IGNORECASE
    )
    match = form_name_pattern.search(text)
    if not match:
        return False
    if match.group(1):  # Bracketed match
        if not match.group(1).isupper() or re.match(r'^[A-Z]?\d+$', match.group(1)):
            return False
        return True
    if len(text) < 10 or len(text) > 80:
        return False
    exclusion_patterns = [r'^(CRF|Form|Date|Time|Coordinator|Designer).*']
    if any(re.match(p, text, re.IGNORECASE) for p in exclusion_patterns):
        return False
    return True


def is_valid_form_label(text):
    """Check if text is a valid form label."""
    if not text or len(text) < 3 or len(text) > 100:
        return False
    invalid_patterns = [
        r'^\s*V\d+[A-Z]*\s*$', r'Design\s*Notes?\s*:?$', r'Oracle\s*item\s*design\s*notes?\s*:?$',
        r'General\s*item\s*design\s*notes?\s*:?$', r'^\s*Non-Visit\s*Related\s*$', r'^Data from.*',
        r'^Hidden item.*', r'^\s*(Non-)?[Rr]epeating(\s+form)?\s*$'
    ]
    if any(re.match(p, text, re.IGNORECASE) for p in invalid_patterns):
        return False
    return True


def deep_search_visits(node):
    """Recursively search all descendants for visit strings."""
    visits = set()
    if not isinstance(node, dict): return visits
    visits.update(extract_visit_strings(get_text(node)))
    for child in node.get("children", []):
        visits.update(deep_search_visits(child))
    return visits


def deep_search_triggers(node, max_depth=5):
    """Recursively search for triggers."""
    triggers = []
    if not isinstance(node, dict): return triggers

    def search(sub_node, depth):
        if depth > max_depth: return
        trigger_info = extract_trigger_info(get_text(sub_node))
        if trigger_info:
            triggers.append({'text': trigger_info, 'depth': depth})
        for child in sub_node.get("children", []):
            search(child, depth + 1)

    search(node, 0)
    return triggers


def deep_search_required(node):
    """
    CORRECTED: Recursively search for the 'Item is required' pattern ONLY in the
    descendants of a given node. This is a localized search.
    """
    if not isinstance(node, dict):
        return False
    text = get_text(node)
    required_pattern = re.compile(r'Key\s*:\s*\[\*\]\s*=\s*Item\s+is\s+required', re.IGNORECASE)
    if required_pattern.search(text):
        return True
    for child in node.get("children", []):
        if deep_search_required(child):
            return True
    return False


def consolidate_duplicates(results):
    """Consolidate duplicate forms by merging similar entries."""
    consolidated = {}
    for form in results:
        base_form_name = re.sub(r'\s*\(.*?\)\s*|\s*–.*', '', form["Form Name"]).strip()
        key = (form["Form Label"], base_form_name, form["Visits"])
        if key not in consolidated or (
                form["Dynamic Trigger"] == "Yes" and consolidated[key]["Dynamic Trigger"] == "No"):
            consolidated[key] = form
    return list(consolidated.values())


def extract_forms_with_final_corrections(data):
    """Extract forms with corrected traversal logic and localized 'Required' detection."""
    results = []
    seen_forms = set()
    h1_sections = []

    def gather_h1_sections(node):
        if not isinstance(node, dict): return
        if node.get('name', '').startswith('H1'):
            h1_sections.append(node)
        for child in node.get('children', []):
            gather_h1_sections(child)

    gather_h1_sections(data)

    document_context = get_text(data)[:2000]  # Get overall context

    for h1_node in h1_sections:
        h1_text = get_text(h1_node) if is_valid_form_label(get_text(h1_node)) else "Unknown Section"

        def find_forms_in_node(node, current_label):
            if not isinstance(node, dict): return

            node_name = node.get("name", "")
            node_text = get_text(node)
            children = node.get("children", [])

            # Update label if we find a more specific H2 that isn't also a form name itself
            if node_name.startswith("H2") and is_valid_form_label(node_text) and not is_valid_form_name(node_text):
                current_label = node_text

            if is_valid_form_name(node_text):
                form_name = node_text
                form_label = current_label

                form_visits = deep_search_visits(node)
                visits_str = ", ".join(sorted(list(form_visits)))

                form_key = (form_label, form_name, visits_str)
                if form_key not in seen_forms:
                    form_triggers = deep_search_triggers(node)
                    unique_triggers = list(set(t['text'] for t in form_triggers))
                    has_trigger = len(unique_triggers) > 0

                    source = determine_form_source(form_name, node_text, form_label, document_context)

                    # *** LOCALIZED REQUIRED DETECTION ***
                    # This is the corrected logic. It checks within the current form's node only.
                    is_form_required = deep_search_required(node)
                    required_flag = "Yes" if is_form_required else "No"

                    results.append({
                        "Form Label": form_label,
                        "Form Name": form_name,
                        "Source": source,
                        "Visits": visits_str,
                        "Dynamic Trigger": "Yes" if has_trigger else "No",
                        "Trigger Details": unique_triggers[0] if has_trigger else "",
                        "Required": required_flag
                    })
                    seen_forms.add(form_key)

            for child in children:
                find_forms_in_node(child, current_label)

        find_forms_in_node(h1_node, h1_text)

    return consolidate_duplicates(results)


# Main execution block
if __name__ == "__main__":
    try:
        input_json_path = 'hierarchical_output_final.json'
        output_csv_path = 'extracted_forms_final_corrected.csv'

        with open(input_json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        extracted_forms = extract_forms_with_final_corrections(json_data)

        with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            fieldnames = ["Form Label", "Form Name", "Source", "Visits", "Dynamic Trigger", "Trigger Details",
                          "Required"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(extracted_forms)

        print(f"\n✅ Successfully extracted {len(extracted_forms)} forms to {output_csv_path}")

        trigger_count = sum(1 for form in extracted_forms if form["Dynamic Trigger"] == "Yes")
        required_count = sum(1 for form in extracted_forms if form["Required"] == "Yes")
        print(f"   - Found {trigger_count} forms with dynamic triggers.")
        print(f"   - Found {required_count} forms marked as required.")

    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_json_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")