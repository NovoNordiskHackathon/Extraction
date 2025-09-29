
######################################################################################################


import json
import csv
import re
import pandas as pd


def get_text(node):
    """
    Extract text from a node safely and recursively.
    This can find text nested inside other nodes (e.g., P -> StyleSpan).
    """
    if not isinstance(node, dict):
        return ""
    text = (node.get("text") or "").strip()
    if text:
        return text
    for child in node.get("children", []):
        text = get_text(child)
        if text:
            return text
    return ""


def is_valid_form_name(text):
    """Check if text is a valid form name, allowing for numbers in the name."""
    if not text:
        return False
    form_name_pattern = re.compile(
        r'(?:'
        r'\[([A-Z0-9_\-]{3,})\]'
        r'|'
        r'.*\b(Non-)?[Rr]epeating\b.*'
        r')',
        re.IGNORECASE
    )
    match = form_name_pattern.search(text)
    if not match:
        return False
    if match.group(1):
        bracketed_content = match.group(1)
        invalid_bracketed_patterns = [r'^L\d+$', r'^[A-Z]\d+$', r'^A\d+$']
        for pattern in invalid_bracketed_patterns:
            if re.match(pattern, bracketed_content):
                return False
        return True
    elif 'repeating' in text.lower():
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
    return False


def is_valid_form_label(text):
    """Check if text is a valid form label by excluding common non-label patterns."""
    if not text or len(text) < 3:
        return False
    invalid_patterns = [
        r'^\s*V\d+[A-Z]*\s*$', r'Design\s*Notes?\s*:?$',
        r'Oracle\s*item\s*design\s*notes?\s*:?$',
        r'General\s*item\s*design\s*notes?\s*:?$',
        r'^\s*Non-Visit\s*Related\s*$', r'^Data from.*', r'^Hidden item.*',
        r'^The item.*', r'^\d+\s+', r'.*\|A\d+\|.*',
        r'^\s*(Non-)?[Rr]epeating(\s+form)?\s*$'
    ]
    for pattern in invalid_patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return False
    if len(text) > 100:
        return False
    return True


def extract_forms_cleaned(data):
    """Extract forms with improved duplicate handling and validation."""
    results = []
    seen_forms = set()

    def process_h1_section(h1_node):
        h1_text = get_text(h1_node)
        if not is_valid_form_label(h1_text): h1_text = "Unknown Section"

        def find_forms_in_node(node, current_label=None):
            if not isinstance(node, dict): return
            node_name, node_text = node.get("name", ""), get_text(node)
            if node_name.startswith("H2") and is_valid_form_label(node_text) and not is_valid_form_name(node_text):
                current_label = node_text
            if is_valid_form_name(node_text):
                form_name, form_label = node_text, current_label if current_label else h1_text
                form_key = (form_label, form_name)
                if form_key not in seen_forms:
                    results.append(
                        {"Form Label": form_label, "Form Name": form_name, "H1_Text": h1_text, "Form_Node": node,
                         "Parent_H1_Node": h1_node})
                    seen_forms.add(form_key)
            for child in node.get("children", []): find_forms_in_node(child, current_label)

        find_forms_in_node(h1_node, None)

    def find_h1_sections(node):
        if not isinstance(node, dict): return
        if node.get("name", "").startswith("H1"): process_h1_section(node)
        for child in node.get("children", []): find_h1_sections(child)

    find_h1_sections(data)
    return results


def find_nodes_by_name_pattern(node, pattern):
    """Find all nodes matching a name pattern recursively."""
    if not isinstance(node, dict): return []
    matches = []
    if re.search(pattern, node.get("name", "")): matches.append(node)
    for child in node.get("children", []): matches.extend(find_nodes_by_name_pattern(child, pattern))
    return matches


# ==============================================================================
# 🔥 CORRECTED ITEM EXTRACTION LOGIC
# ==============================================================================

def has_option_child(node):
    """Recursively check if a node contains an option-indicating child."""
    if not isinstance(node, dict): return False
    if node.get("name", "") in ["LI", "L", "ExtraCharSpan", "LBody"]: return True
    for child in node.get("children", []):
        if has_option_child(child): return True
    return False


def extract_items_from_form(form_node):
    """
    Extracts item data, now correctly handling rows with TH (question) + TD (options).
    """
    items_data = []
    table_nodes = find_nodes_by_name_pattern(form_node, r'^Table')

    for table in table_nodes:
        tr_nodes = find_nodes_by_name_pattern(table, r'^TR')
        for tr in tr_nodes:
            # 🔥 FIX: Look for BOTH TH and TD cells in a row
            cells = [child for child in tr.get("children", []) if child.get("name", "").startswith(("TH", "TD"))]

            for i, cell in enumerate(cells):
                if i > 0 and has_option_child(cell):
                    prev_cell = cells[i - 1]
                    item_name_text = ""
                    p_nodes = find_nodes_by_name_pattern(prev_cell, r'^P')
                    if p_nodes:
                        item_name_text = get_text(p_nodes[0])
                    else:
                        item_name_text = get_text(prev_cell)

                    if item_name_text:
                        items_data.append({
                            "Item Name": item_name_text,
                            "Option_TD_Node": cell
                        })

    unique_items = []
    seen_names = set()
    for item in items_data:
        if item["Item Name"] not in seen_names:
            seen_names.add(item["Item Name"])
            unique_items.append(item)
    return unique_items


def determine_data_type(option_td_node):
    """Determine data type based on the specific cell containing options."""
    if not option_td_node: return "Text"
    if find_nodes_by_name_pattern(option_td_node, r'^ExtraCharSpan'): return "Codelist"
    lbody_nodes = find_nodes_by_name_pattern(option_td_node, r'^LBody')
    if lbody_nodes:
        text = get_text(lbody_nodes[0])
        if re.search(r'\b\d{4}-\d{4}\b', text): return "Date/Time"
        try:
            float(text.replace(",", ""))
            return "Number"
        except (ValueError, AttributeError):
            pass
    return "Text"


def get_all_lbody_values(option_td_node):
    """Get all LBody values from the specific option cell."""
    if not option_td_node: return ""
    lbody_nodes = find_nodes_by_name_pattern(option_td_node, r'^LBody')
    if not lbody_nodes: return ""
    values = [get_text(node) for node in lbody_nodes if get_text(node)]
    seen = set()
    unique_values = [x for x in values if not (x in seen or seen.add(x))]
    return "\n".join(f"• {val}" for val in unique_values)


# ==============================================================================
# MAIN PROCESSING FUNCTION
# ==============================================================================

def process_clinical_forms(json_file_path, template_csv_path, output_csv_path):
    """Main function to process JSON and create the item-based CSV."""
    template_df = pd.read_csv(template_csv_path)
    print("✅ Template CSV loaded successfully")

    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    print("✅ JSON data loaded successfully")

    extracted_forms = extract_forms_cleaned(data)
    print(f"✅ Found {len(extracted_forms)} forms to process")

    all_item_rows = []
    print("\n🔄 Processing forms with corrected item-based row generation...")

    for form in extracted_forms:
        items = extract_items_from_form(form['Form_Node'])
        print(f"  > Form '{form['Form Name']}': Found {len(items)} unique items.")

        if not items:
            items.append({"Item Name": "", "Option_TD_Node": None})

        for item in items:
            item_row = {}
            option_node = item.get("Option_TD_Node")

            item_row['CTDM Optional, if blank CDP to propose'] = form['Form Label']
            item_row['Input needed from SDTM'] = form['Form Name']
            item_row['CDAI input needed'] = form['H1_Text']
            item_row['Unnamed: 4'] = ''
            item_row['Unnamed: 5'] = 50
            item_row['Unnamed: 9'] = ""
            item_row['Unnamed: 10'] = item['Item Name']

            data_type = determine_data_type(option_node)
            item_row['Unnamed: 16'] = data_type
            item_row['Unnamed: 19'] = get_all_lbody_values(option_node)
            item_row['Unnamed: 22'] = "Radio Button-Vertical" if data_type == "Codelist" else ""

            # Other fields left blank for simplicity, can be populated as needed
            item_row.update({k: "" for k in ['Unnamed: 17', 'Unnamed: 18', 'Unnamed: 23', 'Unnamed: 24', 'Unnamed: 25',
                                             'Unnamed: 26']})

            all_item_rows.append(item_row)

    final_df = pd.DataFrame(all_item_rows, columns=template_df.columns)
    final_df = pd.concat([template_df, final_df], ignore_index=True)
    final_df.to_csv(output_csv_path, index=False)
    print(f"\n✅ SUCCESS! Created item-centric CSV: {output_csv_path} with {len(all_item_rows)} item rows.")


if __name__ == "__main__":
    json_file = "hierarchical_output_final.json"
    template_file = "template_first4rows.csv"
    output_file = "FINAL_item_based_output_corrected.csv"

    try:
        print("=" * 80)
        print("CLINICAL FORMS PROCESSING - CORRECTED ITEM-BASED VERSION")
        print("=" * 80)
        process_clinical_forms(json_file, template_file, output_file)
        print("\n🎯 PROCESSING COMPLETE!")
        print("✅ Key features of this version:")
        print("   1. 🔥 FIX: Now correctly handles items in <TH> + <TD> row structures.")
        print("   2. 🔥 Data Type and Codelist values are item-specific.")
        print("   3. ✅ Item Label column is correctly left empty.")
        print("   4. ✅ Generates one row per unique item found in a form.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()