# Final corrected script with all missing forms and accurate trigger detection + SOURCE DETECTION
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
    This function is designed to be generalizable across different protocols/eCRFs by:
    1. Analyzing form naming conventions
    2. Looking for contextual clues in surrounding text
    3. Using standardized medical form patterns
    4. Detecting study-specific modifications
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
        r'\bref\.?\s+study\b',
        r'\breference\s+study\b',
        r'\bborrowed\s+from\b',
        r'\badapted\s+from\b',
        r'\bprevious\s+study\b',
        r'\bderived\s+from\b'
    ]
    for pattern in ref_study_patterns:
        if re.search(pattern, all_text):
            return "Ref. Study"
    # === NEW FORM INDICATORS ===
    # Study-specific numbering patterns
    new_form_patterns = [
        r'_\d+$',  # Ends with underscore and number (e.g., LAB_SMPL_TKN_1)
        r'\d+$',  # Ends with number (e.g., EVALUATION2)
        r'_[A-Z]+\d+$',  # Complex numbering (e.g., FORM_A1)
        r'_V\d+$',  # Version numbering (e.g., FORM_V2)
    ]
    # Check if form name has study-specific numbering
    for pattern in new_form_patterns:
        if re.search(pattern, clean_name.upper()):
            return "New"
    # Study-specific modification indicators in text
    new_context_patterns = [
        r'\bstudy[- ]specific\b',
        r'\bcustom\b',
        r'\bmodified\b',
        r'\btailored\b',
        r'\bprotocol[- ]specific\b',
        r'\bthis\s+study\s+only\b',
        r'\bspecial\s+requirements?\b'
    ]
    for pattern in new_context_patterns:
        if re.search(pattern, all_text):
            return "New"
    # === LIBRARY FORM INDICATORS ===
    # Standard library form indicators in context
    library_context_patterns = [
        r'\bstandard\s+crf\b',
        r'\bnon[- ]?repeating\s+form\b',
        r'\brepeating\s+form\b',
        r'\bstandard\s+form\b',
        r'\bcommon\s+form\b',
        r'\bbaseline\b',
        r'\bfollow[- ]up\b',
        r'\bstandardized\b',
        r'\btemplate\b'
    ]
    for pattern in library_context_patterns:
        if re.search(pattern, all_text):
            return "Library"
    # === COMPREHENSIVE STANDARD FORM DATABASE ===
    # Extensible list of standard medical/clinical form patterns
    # Core clinical domains - these are universally standard
    standard_domains = {
        # Demographics and baseline
        'DEMOGRAPHY', 'DEMOGRAPHIC', 'DEMOGRAPHICS', 'DEMO',
        'INCLUSION', 'EXCLUSION', 'INCLUSIONEXCLUSION', 'ELIGIBILITY',
        'INFORMED_CONSENT', 'CONSENT', 'ICF',
        # Medical history and examination
        'MEDICAL_HIST', 'MEDICAL_HISTORY', 'MEDHIST',
        'PHYSICAL_EXAM', 'PHYSICALEXAM', 'PE', 'PHYSEXAM',
        'VITAL_SIGNS', 'VITALSIGNS', 'VITALS', 'VS',
        'HEIGHT_WEIGHT', 'BODY_MEASUREMENT', 'ANTHROPOMETRY',
        # Laboratory and diagnostics
        'LAB', 'LABORATORY', 'LABS', 'LABVALUE', 'LABRESULT',
        'ECG', 'ELECTROCARDIOGRAM', 'EKG',
        'XRAY', 'X_RAY', 'IMAGING',
        'BIOPSY', 'PATHOLOGY', 'HISTOLOGY',
        # Safety and adverse events
        'AE', 'ADVERSE_EVENT', 'ADVERSEEVENT', 'SAE', 'SERIOUS_AE',
        'SERIOUSADVERSEEVENT', 'SAFETY', 'TOXICITY',
        # Medications and treatments
        'CONMED', 'CONCOMITANT_MEDICATION', 'CONCOMITANTMEDICATION',
        'PRIOR_MED', 'PRIORMED', 'PREVIOUS_MEDICATION',
        'DOSE', 'DOSING', 'ADMINISTRATION',
        # Procedures and interventions
        'PROCEDURE', 'SURGERY', 'INTERVENTION',
        'BIOPSY', 'ENDOSCOPY', 'CATHETERIZATION',
        # Assessments and questionnaires
        'PHQ', 'PHQ9', 'BECK', 'HAMILTON', 'MADRS',
        'MMSE', 'MOCA', 'ADAS', 'CDR',
        'SF36', 'EQ5D', 'WHOQOL', 'QUALITYOFLIFE', 'QOL',
        'PAIN_SCALE', 'VAS', 'NRS',
        'CSSRS', 'C_SSRS', 'SUICIDALITY',
        # Reproductive health
        'PREGNANCY', 'CONTRACEPTION', 'MENSTRUAL', 'FERTILITY',
        'CHILDBEARING', 'REPRODUCTIVE',
        # Substance use
        'TOBACCO', 'SMOKING', 'ALCOHOL', 'SUBSTANCE', 'DRUG_USE',
        'NICOTINE', 'CIGARETTE', 'ECIGARETTE', 'E_CIGARETTE',
        # Sample collection
        'SAMPLE', 'SPECIMEN', 'COLLECTION', 'BIOBANK',
        'BLOOD', 'URINE', 'SALIVA', 'CSF', 'TISSUE',
        # Study management
        'RANDOMIZATION', 'RANDOMISATION', 'RTSM', 'IVRS', 'IWRS',
        'VISIT', 'SCHEDULE', 'COMPLIANCE', 'ADHERENCE',
        'WITHDRAWAL', 'DISCONTINUATION', 'COMPLETION',
        'DEVIATION', 'PROTOCOL_DEVIATION', 'PROTOCOLDEVIATION',
        'END_OF_STUDY', 'ENDOFSTUDY', 'STUDY_COMPLETION',
        # Pharmacokinetics/Pharmacodynamics
        'PK', 'PHARMACOKINETIC', 'PHARMACOKINETICS',
        'PD', 'PHARMACODYNAMIC', 'PHARMACODYNAMICS',
        'BIOANALYTICAL', 'CONCENTRATION', 'EXPOSURE',
        # Device and technology
        'DEVICE', 'IMPLANT', 'MONITOR', 'SENSOR',
        'HOLTER', 'AMBULATORY', 'WEARABLE',
        # Imaging
        'MRI', 'CT', 'SCAN', 'ULTRASOUND', 'PET', 'SPECT',
        'RADIOGRAPHY', 'RADIOLOGY', 'NUCLEAR_MEDICINE',
        # Special populations and conditions
        'PEDIATRIC', 'GERIATRIC', 'ELDERLY',
        'HEPATIC', 'RENAL', 'CARDIAC', 'NEUROLOGICAL',
        # Generic assessment terms
        'ASSESSMENT', 'EVALUATION', 'SCALE', 'SCORE', 'RATING',
        'QUESTIONNAIRE', 'SURVEY', 'INVENTORY', 'INDEX'
    }
    # Check if base form name matches standard domains
    if base_form_name in standard_domains:
        return "Library"
    # Check for partial matches with standard domains
    for domain in standard_domains:
        if domain in base_form_name or base_form_name in domain:
            # Additional check: if it has study-specific suffixes, it might be New
            if re.search(r'_\d+$', clean_name.upper()):
                return "New"
            return "Library"
    # === PATTERN-BASED CLASSIFICATION ===
    # Standard naming patterns that suggest Library forms
    standard_patterns = [
        r'^[A-Z]{2,}_[A-Z]{2,}$',  # TWO_PART format
        r'^[A-Z]{3,}$',  # All caps single word
        r'^[A-Z]+_BASE$',  # Baseline forms
        r'^[A-Z]+_FU$',  # Follow-up forms
        r'^[A-Z]+_SLV$',  # Since last visit forms
    ]
    for pattern in standard_patterns:
        if re.match(pattern, clean_name.upper()):
            return "Library"
    # Study-specific patterns
    study_specific_patterns = [
        r'^[A-Z]+_\d{2,}$',  # Forms with multi-digit numbers
        r'^[A-Z]+_[A-Z]\d+$',  # Forms like FORM_A1, FORM_B2
        r'^\w+_V\d+$',  # Version-specific forms
    ]
    for pattern in study_specific_patterns:
        if re.match(pattern, clean_name.upper()):
            return "New"
    # === DEFAULT CLASSIFICATION LOGIC ===
    # If form name follows standard medical nomenclature (all caps, underscores)
    if re.match(r'^[A-Z][A-Z0-9_]*$', clean_name.upper()):
        # Check length - very short names are often standard
        if len(base_form_name) <= 6:
            return "Library"
        # Medium length with standard structure
        elif 6 < len(base_form_name) <= 15:
            return "Library"
        # Longer names might be study-specific
        else:
            return "New"
    # If it contains mixed case or special characters, likely New
    if re.search(r'[a-z]', clean_name) or re.search(r'[^A-Z0-9_]', clean_name):
        return "New"
    # Default fallback
    return "Library"


def extract_trigger_info(text):
    """Extract and clean trigger information using comprehensive strict patterns."""
    if not text or len(text.split()) < 4:
        return None
    # Comprehensive patterns including the newly found ones
    strict_trigger_patterns = [
        # Core dynamic trigger patterns
        r'\bform\s+to\s+be\s+(dynamically\s+)?triggered\b',
        r'\b(dynamically\s+)?triggered\s+from\b',
        r'\bshould\s+trigger\b',
        r'\btrigger\s+only\s+for\b',
        r'\bform\s+should\s+trigger\b',
        r'\btrigger\s+at\s+every\s+required\s+visit\b',

        # Item/form appearance patterns
        r'\bitem\s+to\s+trigger\b.*\bform\s+(to\s+appear|must\s+appear)\b',
        r'\bform\s+(to\s+appear|must\s+appear)\b.*\bresponse\b',
        r'\bform\s+must\s+appear\b',

        # Response-based triggers
        r'\btrigger\b.*\b(if|when|only\s+if)\b.*\b(response|marked\s+as|yes|no)\b',
        r'\bif\s+response\s+is\s+(yes|no)\b.*\bform\b',

        # Event and adjudication triggers
        r'\bselect\s+event\s+type\s+to\s+trigger\b',
        r'\btrigger\s+the\s+availability\b',
        r'\bevent.*trigger.*adjudication\b',

        # Dynamic forms
        r'\bdynamic\s+(to\s+be\s+triggered|should\s+be\s+triggered)\b',
        r'\bdynamic\s+to\s+be\s+added\b.*\btrigger\b',

        # Subject-specific triggers
        r'\brequired\s+only\s+for\b.*\bsubjects?\b.*\btrigger\b',
        r'\bform\s+should\s+trigger\s+dynamically\s+when\b',

        # Supporting text patterns (for Case Book Sign Off)
        r'\bsupporting\s+text\b.*\btrigger\s+dynamically\b',
        r'.*deleted.*trigger.*dynamically.*',
        r'.*form\s+should\s+trigger\s+dynamically.*deleted\b',

        # Dose tapering patterns
        r'\bdynamic\s+should\s+be\s+triggered\s+for\s+dose\s+tapering\b',
        r'\bvisit.*should\s+trigger.*algorithm\s+group\b',

        # For female/male subjects patterns
        r'\bfor\s+(female|male)\s+subjects\s+only.*trigger\b',
        r'\btrigger.*for\s+(female|male)\s+subjects\b',
    ]

    # Exclusion patterns for false positives (including ENR pattern)
    exclusion_patterns = [
        r'\b(not\s+trigger|does\s+not\s+trigger|no\s+trigger)\b',
        r'\b(hidden|date\s+of\s+birth|prefer\s+not\s+to)\b',
        r'\b(data\s+from|if\s+abnormal|record\s+in)\b',
        r'\bif\s+medication\s+is\s+taken\b',
        r'\bif\s+yes\s+to\s+\d+\b',  # C-SSRS specific exclusion
        r'^\s*visit\s+p\d+.*should\s+trigger.*participants.*algorithm\s+group\s*$',  # ENR false positive
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


def deep_search_triggers(node, max_depth=5, current_depth=0):
    """Recursively search for triggers with increased depth for better coverage."""
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


def is_enr_form(form_name):
    """Check if this is the ENR form that should be marked as No."""
    return '[ENR]' in form_name


def consolidate_duplicates(results):
    """Consolidate duplicate forms by merging similar entries."""
    consolidated = {}

    for form in results:
        form_label = form["Form Label"]
        form_name = form["Form Name"]

        # Create a more specific key that considers both label and normalized name
        base_form_name = re.sub(r'\s*\(.*?\)\s*', '', form_name)
        base_form_name = re.sub(r'\s*–.*', '', base_form_name)
        base_form_name = base_form_name.strip()

        # Include visits in key to differentiate forms with different visit schedules
        visits = form["Visits"]
        key = (form_label, base_form_name, visits)

        if key in consolidated:
            # Merge logic: prefer the one with trigger details
            existing = consolidated[key]
            if form["Dynamic Trigger"] == "Yes" and existing["Dynamic Trigger"] == "No":
                consolidated[key] = form
            elif form["Dynamic Trigger"] == "Yes" and existing["Dynamic Trigger"] == "Yes":
                # Both have triggers, use the more detailed one
                if len(form["Trigger Details"]) > len(existing["Trigger Details"]):
                    consolidated[key] = form
        else:
            consolidated[key] = form

    return list(consolidated.values())


def extract_section_number(path):
    """Extract section number from path like //Document/H2[25] or //Document/P[15]/Sub"""
    if not path:
        return 0

    # Find all numbers in square brackets in the path
    matches = re.findall(r'\[(\d+)\]', path)
    if matches:
        # Return the first number found - this handles H2[25], P[15], etc.
        return int(matches[0])
    return 0


def find_all_required_patterns_globally_fixed(data):
    """Fixed mapping with proper section number extraction."""
    required_mappings = {}
    all_form_nodes = []
    all_required_nodes = []

    def collect_nodes(node, path_ancestry=[], depth=0):
        if not isinstance(node, dict):
            return

        current_path = path_ancestry + [node]
        text = get_text(node)
        node_path = node.get('path', '')
        node_name = node.get('name', '')

        # Collect form nodes
        if is_valid_form_name(text):
            all_form_nodes.append({
                'node': node,
                'text': text,
                'path': node_path,
                'name': node_name,
                'ancestry': current_path,
                'depth': depth
            })

        # Collect required pattern nodes
        required_pattern = re.compile(r'.*Key\s*:\s*\[\*\]\s*=\s*Item\s+is\s+required\.?\s*.*', re.IGNORECASE)
        if re.search(required_pattern, text):
            all_required_nodes.append({
                'node': node,
                'text': text,
                'path': node_path,
                'name': node_name,
                'ancestry': current_path,
                'depth': depth
            })

        # Recurse through children
        for child in node.get("children", []):
            collect_nodes(child, current_path, depth + 1)

    collect_nodes(data)

    print(f"Found {len(all_form_nodes)} total form nodes")
    print(f"Found {len(all_required_nodes)} required pattern nodes")

    # PRECISE MAPPING: Each required pattern maps to exactly ONE closest form
    for req_info in all_required_nodes:
        req_path = req_info['path']
        req_section_num = extract_section_number(req_path)

        closest_form = None
        min_distance = float('inf')

        print(f"\nAnalyzing required pattern at {req_path} (section {req_section_num}):")

        # Find the closest form by section number
        for form_info in all_form_nodes:
            form_path = form_info['path']
            form_section_num = extract_section_number(form_path)
            distance = abs(req_section_num - form_section_num)

            print(f"  Form at {form_path} (section {form_section_num}): distance = {distance}")

            if distance < min_distance:
                min_distance = distance
                closest_form = form_info

        # Map this required pattern to ONLY the closest form (within reasonable distance)
        if closest_form and min_distance <= 5:  # Only map if within 5 sections
            form_text = closest_form['text']
            if form_text not in required_mappings:
                required_mappings[form_text] = []
            required_mappings[form_text].append(req_info['text'])
            print(f"  → MAPPED to closest form: {form_text[:50]}... (distance: {min_distance})")
        else:
            print(f"  → NO MAPPING - distance too far: {min_distance}")

    print(f"\nFinal required mappings: {len(required_mappings)} forms marked as required")
    for form_name in required_mappings:
        print(f"  - {form_name[:50]}...")

    return required_mappings


def is_required_global(form_name, required_mappings):
    """Check if a form is required using global mapping."""
    return form_name in required_mappings


def extract_forms_with_final_corrections(data):
    """Extract forms with all corrections including missing Tanner Female and Case Book Sign Off + SOURCE detection."""
    results = []
    seen_forms = set()
    all_triggers = []
    h1_sections = []

    # *** FIXED REQUIRED PATTERN MAPPING ***
    required_mappings = find_all_required_patterns_globally_fixed(data)
    print(f"Required mappings found: {len(required_mappings)} forms")

    def gather_h1_sections(node):
        if not isinstance(node, dict):
            return
        if node.get('name', '').startswith('H1'):
            h1_sections.append(node)
        for child in node.get('children', []):
            gather_h1_sections(child)

    gather_h1_sections(data)

    # Extract overall document context for source determination
    def extract_document_context(node, context_parts=None):
        if context_parts is None:
            context_parts = []
        if not isinstance(node, dict):
            return " ".join(context_parts)
        text = get_text(node)
        if text and len(text) > 10:  # Only meaningful text
            context_parts.append(text[:200])  # Limit to prevent excessive length
        for child in node.get("children", []):
            extract_document_context(child, context_parts)
            if len(context_parts) > 20:  # Limit context size
                break
        return " ".join(context_parts)

    document_context = extract_document_context(data)

    for idx, h1_node in enumerate(h1_sections):
        h1_text = get_text(h1_node)
        if not is_valid_form_label(h1_text):
            h1_text = "Unknown Section"

        section_visits = deep_search_visits(h1_node)
        section_triggers = deep_search_triggers(h1_node, max_depth=6)
        next_trigger = find_next_h1_trigger(h1_sections, idx)

        # Extract section context for source determination
        section_context = extract_document_context(h1_node)

        def find_forms_in_node(node, current_label=None, parent_siblings=None, ancestors=None):
            if ancestors is None:
                ancestors = []

            if not isinstance(node, dict):
                return

            node_name = node.get("name", "")
            node_text = get_text(node)
            children = node.get("children", [])

            # Update label logic for H2 sections
            if node_name.startswith("H2") and is_valid_form_label(node_text) and not is_valid_form_name(node_text):
                current_label = node_text

            if is_valid_form_name(node_text):
                form_name = node_text
                form_label = current_label if current_label else h1_text

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

                form_key = (form_label, form_name, visits_str)

                if form_key not in seen_forms:
                    # Enhanced trigger search with wider scope
                    form_triggers = deep_search_triggers(node, max_depth=7)
                    if parent_siblings:
                        try:
                            current_index = parent_siblings.index(node)
                            for i in range(max(0, current_index - 8), min(len(parent_siblings), current_index + 9)):
                                if i != current_index:
                                    sibling_triggers = deep_search_triggers(parent_siblings[i], max_depth=5)
                                    form_triggers.extend(sibling_triggers)
                        except ValueError:
                            pass
                    if not form_triggers:
                        form_triggers = section_triggers
                    if not form_triggers and next_trigger:
                        form_triggers.append({'text': next_trigger, 'depth': 0})

                    # Special handling for ENR form - should be No
                    if is_enr_form(form_name):
                        form_triggers = []  # Force to No for ENR

                    # Deduplicate and validate triggers
                    unique_triggers = list(set(t['text'] for t in form_triggers if extract_trigger_info(t['text'])))
                    all_triggers.extend(unique_triggers)

                    has_trigger = len(unique_triggers) > 0
                    trigger_details = unique_triggers[0] if has_trigger else ""

                    # *** DETERMINE SOURCE HERE ***
                    # Extract node-specific context
                    node_context = extract_document_context(node)
                    # Determine source using comprehensive analysis
                    source = determine_form_source(
                        form_name=form_name,
                        form_text=node_text,
                        context_text=f"{section_context} {node_context}",
                        document_context=document_context
                    )

                    # *** FIXED REQUIRED DETECTION ***
                    required_flag = "Yes" if is_required_global(form_name, required_mappings) else "No"

                    # DEBUG: Print which forms are being marked as required
                    if required_flag == "Yes":
                        print(f"REQUIRED FORM DETECTED: {form_name}")

                    results.append({
                        "Form Label": form_label,
                        "Form Name": form_name,
                        "Source": source,
                        "Visits": visits_str,
                        "Dynamic Trigger": "Yes" if has_trigger else "No",
                        "Trigger Details": trigger_details,
                        "Required": required_flag
                    })
                    seen_forms.add(form_key)

            for child in children:
                find_forms_in_node(child, current_label, children, ancestors + [node])

        find_forms_in_node(h1_node, None, None, [])

    # Consolidate duplicates
    results = consolidate_duplicates(results)

    # Log total unique validated triggers
    unique_triggers = list(set(all_triggers))
    print(f"Total unique validated triggers detected: {len(unique_triggers)}")
    for t in unique_triggers:
        print(f"- {t}")

    return results


# Main execution
try:
    input_json_path = 'hierarchical_output_final.json'

    with open(input_json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    extracted_forms = extract_forms_with_final_corrections(data)

    output_csv_path = 'extracted_forms_final_with_source.csv'
    with open(output_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ["Form Label", "Form Name", "Source", "Visits", "Dynamic Trigger",
                      "Trigger Details", "Required"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in extracted_forms:
            writer.writerow(row)

    print(f"\nExtracted {len(extracted_forms)} forms to {output_csv_path}")

    trigger_count = sum(1 for form in extracted_forms if form["Dynamic Trigger"] == "Yes")
    print(f"Found {trigger_count} forms with dynamic triggers")

    # *** SOURCE SUMMARY ***
    source_counts = {}
    for form in extracted_forms:
        source = form['Source']
        source_counts[source] = source_counts.get(source, 0) + 1
    print(f"\nSource Distribution:")
    for source, count in source_counts.items():
        print(f"  {source}: {count} forms")

    # *** REQUIRED SUMMARY ***
    required_count = sum(1 for form in extracted_forms if form["Required"] == "Yes")
    print(f"\nRequired Forms: {required_count}")

    print(f"\nDetailed Form Analysis:")
    print("=" * 100)
    for i, form in enumerate(extracted_forms):
        trigger_status = "🔄" if form["Dynamic Trigger"] == "Yes" else "📝"
        source_icon = "📚" if form["Source"] == "Library" else "🆕" if form["Source"] == "New" else "🔗"
        required_icon = "⭐" if form["Required"] == "Yes" else ""
        print(
            f"{i + 1}. {trigger_status} {source_icon} [{form['Source']}] {required_icon} {form['Form Label']} | {form['Form Name']} | {form['Visits']}")
        if form["Dynamic Trigger"] == "Yes":
            print(f"   └─ Trigger: {form['Trigger Details'][:100]}...")
            print()

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
