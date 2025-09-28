# import pandas as pd
#
# # Ensure every column has exactly 4 rows (pad with None if fewer)
# template_data = {
#     'CTDM to fill in': [None, 'Source', 'New or Copied from Study', None],
#     'CTDM Optional, if blank CDP to propose': [None, 'Form', 'Form Label', None],
#     'Input needed from SDTM': [None, None, 'Form Name (provided by SDTM Programmer, if SDTM linked form)', None],
#     'CDAI input needed': [None, 'Item Group', 'Item Group (if only one on form, recommend same as Form Label)', None],
#     'Unnamed: 4': [None, None, 'Item group Repeating', None],
#     'Unnamed: 5': [None, None, 'Repeat Maximum, if known, else default =50', None],
#     'Unnamed: 6': [None, None, 'Display format of repeating item group (Grid, read only, form)', None],
#     'Unnamed: 7': [None, None, 'Default Data in repeating item group', None],
#     'Unnamed: 8': [None, 'Item', 'Item Order', None],
#     'Unnamed: 9': [None, None, 'Item Label', None],
#     'Unnamed: 10': [None, None, 'Item Name (provided by SDTM Programmer, if SDTM linked)', None],
#     'Unnamed: 11': [None, 'Progressive Display',None , None],
#     'Unnamed: 12': [None, None,'Progressively Displayed?', None],
#     'Unnamed: 13': [None,None ,'Controlling Item (item name if known, else item label)',None],
#     'Unnamed: 14': [None, None, 'Controlling Item Value',None],
#     'Unnamed: 15': [None, None, None, None],
#     'Unnamed: 16': [None, 'Data type', None, None],
#     'Unnamed: 17': ['Data type', 'If text or number, Field Length', None, None],
#     'Unnamed: 18': [None, 'If number, Precision (decimal places)', None, None],
#     'Unnamed: 19': [None, 'Codelist', 'Codelist - Choice Labels (If many, can use Codelist Name)', None],
#     'Unnamed: 20': [None, None, 'Codelist Name (provided by SDTM programmer)', None],
#     'Unnamed: 21': [None, None, 'Choice Code (provided by SDTM programmer)', None],
#     'Unnamed: 22': [None, None, 'Codelist: Control Type', None],
#     'Unnamed: 23': [None, 'System Queries', 'If Number, Range: Min Value - Max Value', None],
#     'Unnamed: 24': [None, None, 'If Date, Query Future Date', None],
#     'Unnamed: 25': [None, None, 'Required', None],
#     'Unnamed: 26': [None, None, 'If Required, Open Query when Intentionally Left Blank(Form, Item)', None],
#     'Unnamed: 27': [None, None, 'Notes', None]
# }
#
# # Create DataFrame with consistent lengths
# df_template = pd.DataFrame(template_data)
#
# # Save to CSV
# output_file = 'template_first4rows.csv'
# df_template.to_csv(output_file, index=False)
#
# print(f'Template CSV created as {output_file}')
# print(f'Shape: {df_template.shape}')








##################################################################################################################


import json
import csv
import re
import pandas as pd


def get_text(node):
    """Extract text from a node safely."""
    if not isinstance(node, dict):
        return ""
    return (node.get("text") or "").strip()


def deep_search_for_forms(node):
    """
    Recursively search through all descendant nodes to find form names
    (identified by bracketed text). It returns a list of dictionaries,
    each containing the form's name and a reference to its node.
    """
    if not isinstance(node, dict):
        return []

    found_forms = []
    text = get_text(node)

    # Check if the current node's text contains a form name pattern like [FORM_ID]
    form_name_match = re.search(r'\[([A-Za-z0-9_\-]+)\]', text)
    if form_name_match:
        found_forms.append({
            "Form Name": text,
            "Node": node  # Keep a reference to the node for label assignment
        })

    # Continue the search recursively in all children nodes
    for child in node.get("children", []):
        child_forms = deep_search_for_forms(child)
        found_forms.extend(child_forms)

    return found_forms


def extract_form_labels_and_names(data):
    """
    Extracts forms and their corresponding labels from the hierarchical data.
    It processes the data section by section, where each section is defined
    by an H1 heading.
    """
    results = []

    def process_h1_section(h1_node):
        """Process an H1 section to find all forms and assign them labels."""
        h1_text = get_text(h1_node)

        # Find all forms within this H1 section
        forms_in_section = deep_search_for_forms(h1_node)

        # For each found form, assign a label by looking for the nearest
        # preceding H2 heading.
        for form in forms_in_section:
            form_node = form["Node"]
            # Default the label to the H1 text if no specific H2 is found
            form_label = h1_text

            def find_label_for_node(search_node, target_node):
                """
                Traverses the tree to find the appropriate H2 label for a
                given target node.
                """
                if not isinstance(search_node, dict):
                    return None

                children = search_node.get("children", [])
                for i, child in enumerate(children):
                    if child == target_node:
                        # The target node is found. Now, look backwards from its
                        # position to find the last H2 heading.
                        for j in range(i - 1, -1, -1):
                            prev_sibling = children[j]
                            prev_name = prev_sibling.get("name", "")
                            prev_text = get_text(prev_sibling)
                            # A valid label is an H2 that does not contain a form name itself
                            if prev_name.startswith("H2") and not re.search(r'\[([A-Za-z0-9_\-]+)\]', prev_text):
                                return prev_text
                        return None  # No preceding H2 sibling found
                    else:
                        # If not found, search within the child node
                        result = find_label_for_node(child, target_node)
                        if result:
                            return result
                return None

            specific_label = find_label_for_node(h1_node, form_node)
            if specific_label:
                form_label = specific_label

            results.append({
                "Form Label": form_label,
                "Form Name": form["Form Name"],
                "H1_Text": h1_text,
                "Form_Node": form_node,
                "Parent_H1_Node": h1_node  # Keep reference to parent H1 node
            })

    def find_all_h1_sections(node):
        """Find and process all H1 sections in the data."""
        if not isinstance(node, dict):
            return

        if node.get("name", "").startswith("H1"):
            process_h1_section(node)
        else:
            # If the current node is not H1, check its children
            for child in node.get("children", []):
                find_all_h1_sections(child)

    find_all_h1_sections(data)
    return results


def find_nodes_by_name_pattern(node, pattern):
    """Find all nodes matching a name pattern"""
    if not isinstance(node, dict):
        return []

    matches = []
    name = node.get("name", "")

    if re.search(pattern, name):
        matches.append(node)

    for child in node.get("children", []):
        matches.extend(find_nodes_by_name_pattern(child, pattern))

    return matches


def search_for_text_pattern(node, pattern):
    """Search for text pattern in node and all children"""
    if not isinstance(node, dict):
        return []

    matches = []
    text = get_text(node)

    if re.search(pattern, text):
        matches.append(node)

    for child in node.get("children", []):
        matches.extend(search_for_text_pattern(child, pattern))

    return matches


def has_asterisk(node):
    """Check if node or its children contain asterisk"""
    if not isinstance(node, dict):
        return False

    text = get_text(node)
    if "*" in text:
        return True

    for child in node.get("children", []):
        if has_asterisk(child):
            return True

    return False


def get_h1_texts_with_children_only(data):
    """
    Get H1 texts only from H1 nodes that have children.
    """
    h1_texts_with_children = []

    def collect_h1_with_children(node):
        if not isinstance(node, dict):
            return

        if node.get("name", "").startswith("H1"):
            # Only include H1 nodes that have children
            if node.get("children", []):  # Check if H1 has children
                h1_texts_with_children.append(get_text(node))

        for child in node.get("children", []):
            collect_h1_with_children(child)

    collect_h1_with_children(data)
    return h1_texts_with_children


def is_number(text):
    """Check if text represents a number"""
    try:
        float(text.replace(",", ""))
        return True
    except:
        return False


def is_year_format(text):
    """Check if text matches yyyy-yyyy year format"""
    year_pattern = r'\b\d{4}-\d{4}\b'
    return bool(re.search(year_pattern, text))


def determine_data_type(form_node):
    """
    Determine data type with enhanced logic
    Priority order:
    1. If has ExtraCharSpan -> 'Codelist'
    2. If LBody text is yyyy-yyyy format -> 'Date/Time'
    3. If LBody text is numeric -> 'Number'
    4. Default -> 'Text'
    """

    # First check for ExtraCharSpan nodes (highest priority)
    extra_char_nodes = find_nodes_by_name_pattern(form_node, r'^ExtraCharSpan')
    if extra_char_nodes:
        return "Codelist"

    # Then check LBody nodes for content
    lbody_nodes = find_nodes_by_name_pattern(form_node, r'^LBody')
    if lbody_nodes:
        lbody_text = get_text(lbody_nodes[0])

        # Check if it's year format (yyyy-yyyy) - second priority
        if is_year_format(lbody_text):
            return "Date/Time"

        # Check if it's a number - third priority
        if is_number(lbody_text):
            return "Number"

    # Default to Text - lowest priority
    return "Text"


def get_all_lbody_values(form_node):
    """
    ✅ ENHANCED FUNCTION: Get all LBody node values for the current form
    and format them with bullet points on new lines as requested:
    Example output:
    • Yes
    • No, none were collected
    """
    lbody_nodes = find_nodes_by_name_pattern(form_node, r'^LBody')

    if not lbody_nodes:
        return ""

    # Collect all LBody text values
    lbody_values = []
    for lbody_node in lbody_nodes:
        text = get_text(lbody_node)
        if text:  # Only add non-empty values
            lbody_values.append(text)

    if not lbody_values:
        return ""

    # Remove duplicates while preserving order
    seen = set()
    unique_values = []
    for value in lbody_values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)

    # Format with bullet points and new lines
    formatted_values = []
    for value in unique_values:
        formatted_values.append(f"• {value}")

    return "\n".join(formatted_values)


def get_precision(text):
    """Get decimal precision from number text"""
    try:
        num_str = text.replace(",", "")
        if "." in num_str:
            return len(num_str.split(".")[1])
        return 0
    except:
        return 0


def process_clinical_forms_final_enhanced(json_file_path, template_csv_path, output_csv_path):
    """
    ✅ FINAL ENHANCED function with all improvements:
    - Enhanced data type detection
    - All LBody values in Codelist - Choice Labels with bullet points
    - Updated H1 children-only repeating logic
    """

    # Load the template CSV and the JSON data
    template_df = pd.read_csv(template_csv_path)
    print("✅ Template CSV loaded successfully")

    # Load the JSON data
    with open(json_file_path, "r", encoding="utf-8") as file:
        json_content = file.read()
        data = json.loads(json_content)
    print("✅ JSON data loaded successfully")

    # Extract the forms
    extracted_forms = extract_form_labels_and_names(data)
    print(f"✅ Found {len(extracted_forms)} forms to process")

    # Get H1 texts only from H1 nodes that have children
    h1_texts_with_children = get_h1_texts_with_children_only(data)
    print(f"✅ Found {len(h1_texts_with_children)} H1 nodes with children")

    # Process each form according to the 14 instructions with all enhancements
    form_data_rows = []

    print("\n🔄 Processing forms with ALL ENHANCEMENTS...")
    for form_idx, form in enumerate(extracted_forms):
        print(f"Processing Form {form_idx + 1}: {form['Form Name']}")

        form_row = {}
        form_node = form['Form_Node']
        parent_h1_node = form['Parent_H1_Node']
        h1_text = form['H1_Text']

        # Fill Form Label and Form Name in the correct columns
        form_row['CTDM Optional, if blank CDP to propose'] = form['Form Label']
        form_row['Input needed from SDTM'] = form['Form Name']
        form_row['CDAI input needed'] = h1_text

        # UPDATED LOGIC for "Item group Repeating": Only H1s with children
        parent_h1_has_children = bool(parent_h1_node.get("children", []))

        if parent_h1_has_children:
            h1_count_with_children = h1_texts_with_children.count(h1_text)
            form_row['Unnamed: 4'] = 'Y' if h1_count_with_children > 1 else ''
            form_row['Unnamed: 5'] = h1_count_with_children if h1_count_with_children > 1 else 50
        else:
            form_row['Unnamed: 4'] = ''
            form_row['Unnamed: 5'] = 50

        # Item Label and Item Name (instructions 4-5)
        tr_nodes = find_nodes_by_name_pattern(form_node, r'^TR')
        item_label = ""
        if tr_nodes:
            for tr in tr_nodes:
                td_nodes = [child for child in tr.get("children", []) if child.get("name", "").startswith("TD")]
                if td_nodes:
                    item_label = get_text(td_nodes[0])
                    break
        form_row['Unnamed: 9'] = item_label

        item_name = ""
        if tr_nodes:
            for tr in tr_nodes:
                td_nodes = [child for child in tr.get("children", []) if child.get("name", "").startswith("TD")]
                if len(td_nodes) > 1:
                    item_name = get_text(td_nodes[1])
                    break
        form_row['Unnamed: 10'] = item_name

        # Enhanced Data Type Detection (instruction 6)
        data_type = determine_data_type(form_node)
        form_row['Unnamed: 16'] = data_type

        # Field Length (instruction 7) - based on first LBody node
        lbody_nodes = find_nodes_by_name_pattern(form_node, r'^LBody')
        first_lbody_text = ""
        if lbody_nodes:
            first_lbody_text = get_text(lbody_nodes[0])

        form_row['Unnamed: 17'] = len(first_lbody_text) if first_lbody_text else ""

        # Precision (instruction 8)
        precision = ""
        if data_type == "Number" and first_lbody_text:
            precision = get_precision(first_lbody_text)
        form_row['Unnamed: 18'] = precision

        # ✅ ENHANCED Codelist Choice Labels (instruction 9) - ALL LBody values with bullets
        codelist_choice_labels = get_all_lbody_values(form_node)
        form_row['Unnamed: 19'] = codelist_choice_labels

        # Control Type (instruction 10)
        form_row['Unnamed: 22'] = "Radio Button-Vertical" if data_type == "Codelist" else ""

        # Range and Date Query (instructions 11-12)
        year_pattern = r'\b\d{4}-\d{4}\b'
        year_matches = search_for_text_pattern(form_node, year_pattern)
        year_range = ""
        if year_matches:
            year_range = get_text(year_matches[0])
            year_match = re.search(year_pattern, year_range)
            if year_match:
                year_range = year_match.group()
        form_row['Unnamed: 23'] = year_range
        form_row['Unnamed: 24'] = "Y" if year_range else ""

        # Required and Open Query (instructions 13-14)
        form_row['Unnamed: 25'] = "Y" if has_asterisk(form_node) else ""
        form_row['Unnamed: 26'] = "Form,Item" if has_asterisk(form_node) else ""

        form_data_rows.append(form_row)

    # Create the final CSV
    final_df = template_df.copy()

    # Add form data rows
    for form_row in form_data_rows:
        new_row = {}
        for col in final_df.columns:
            new_row[col] = form_row.get(col, "")

        new_row_df = pd.DataFrame([new_row])
        final_df = pd.concat([final_df, new_row_df], ignore_index=True)

    # Save the filled CSV
    final_df.to_csv(output_csv_path, index=False)

    print(f"\n✅ SUCCESS! Created FINAL ENHANCED CSV: {output_csv_path}")

    # Show statistics
    data_types = [row['Unnamed: 16'] for row in form_data_rows]
    from collections import Counter
    type_counts = Counter(data_types)
    print(f"\n📊 Data Type Distribution:")
    for data_type, count in type_counts.items():
        print(f"  {data_type}: {count} forms")

    # Show codelist examples
    codelist_forms = [row for row in form_data_rows if row['Unnamed: 19']]
    print(f"\n📋 Forms with Enhanced Codelist Labels: {len(codelist_forms)}")

    return final_df


# Example usage with all enhancements
if __name__ == "__main__":
    json_file = "hierarchical_output_final.json"
    template_file = "template_first4rows.csv"
    output_file = "FINAL_ENHANCED_clinical_forms.csv"

    try:
        print("=" * 80)
        print("CLINICAL FORMS PROCESSING - FINAL ENHANCED VERSION")
        print("=" * 80)

        result_df = process_clinical_forms_final_enhanced(json_file, template_file, output_file)
        print(f"\n🎯 PROCESSING COMPLETE WITH ALL ENHANCEMENTS!")
        print("✅ All enhancements applied:")
        print("   1. Enhanced data type detection (ExtraCharSpan → Date/Time → Number → Text)")
        print("   2. Enhanced codelist labels (ALL LBody values with bullet points)")
        print("   3. Updated H1 children-only repeating logic")
        print("   4. Proper Form Label and Form Name mapping")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
