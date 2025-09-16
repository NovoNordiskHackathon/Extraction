import os
import pandas as pd
import glob

def load_all_excels_from_folder(folder_path):
    """Load all Excel files from a specified folder"""
    excel_files = glob.glob(os.path.join(folder_path, "*.xlsx"))
    
    loaded_files = {}
    for file_path in excel_files:
        try:
            df = pd.read_excel(file_path)
            filename = os.path.basename(file_path)
            loaded_files[filename] = df
            print(f"Loaded: {filename} ({len(df)} rows)")
        except Exception as e:
            print(f"Failed to load {file_path}: {e}")
    
    return loaded_files

def identify_file_types(loaded_files):
    """Identify which files contain protocol vs mock CRF data based on column names"""
    protocol_files = []
    mock_crf_files = []
    
    # Common column patterns to identify file types
    protocol_patterns = ['visit', 'event', 'schedule', 'window', 'week', 'day']
    crf_patterns = ['form', 'item', 'field', 'label', 'data_type', 'codelist']
    
    for filename, df in loaded_files.items():
        columns_lower = [col.lower() for col in df.columns if isinstance(col, str)]
        column_text = ' '.join(columns_lower)
        
        protocol_score = sum(1 for pattern in protocol_patterns if pattern in column_text)
        crf_score = sum(1 for pattern in crf_patterns if pattern in column_text)
        
        if protocol_score > crf_score:
            protocol_files.append((filename, df))
            print(f"Identified as Protocol: {filename}")
        else:
            mock_crf_files.append((filename, df))
            print(f"Identified as Mock CRF: {filename}")
    
    return protocol_files, mock_crf_files

def generate_event_mapping(visit_labels):
    """Generate automated event name mapping"""
    import re
    mapping = {}
    
    for label in visit_labels:
        label_lower = label.lower().strip()
        
        if 'screening' in label_lower:
            mapping[label] = 'SCR'
        elif 'randomization' in label_lower or 'randomisation' in label_lower:
            mapping[label] = 'RAND'
        elif 'end of treatment' in label_lower or 'eot' in label_lower:
            mapping[label] = 'EOT'
        elif 'end of study' in label_lower or 'eos' in label_lower:
            mapping[label] = 'EOS'
        elif 'follow' in label_lower:
            mapping[label] = 'FU'
        elif 'unscheduled' in label_lower:
            mapping[label] = 'UNSCH'
        elif 'baseline' in label_lower:
            mapping[label] = 'BL'
        elif 'visit' in label_lower:
            match = re.search(r'\d+', label)
            if match:
                mapping[label] = f"V{match.group(0)}"
            else:
                mapping[label] = 'V'
        elif 'week' in label_lower:
            match = re.search(r'\d+', label)
            if match:
                mapping[label] = f"W{match.group(0)}"
            else:
                mapping[label] = 'W'
        elif 'day' in label_lower:
            match = re.search(r'\d+', label)
            if match:
                mapping[label] = f"D{match.group(0)}"
            else:
                mapping[label] = 'D'
        else:
            clean_label = ''.join([c.upper() for c in label if c.isalpha()])
            mapping[label] = clean_label[:4] if len(clean_label) >= 4 else clean_label[:3]
    
    return mapping

def create_automated_schedule_grid_from_folder(folder_path):
    """Complete automated workflow processing all Excel files in a folder"""
    
    print(f"Processing Excel files from folder: {folder_path}")
    
    # Load all Excel files
    loaded_files = load_all_excels_from_folder(folder_path)
    
    if not loaded_files:
        print("No Excel files found in the folder!")
        return None, None, None
    
    # Identify file types
    protocol_files, mock_crf_files = identify_file_types(loaded_files)
    
    # Combine all protocol data
    all_protocol_data = []
    for filename, df in protocol_files:
        all_protocol_data.append(df)
    
    if all_protocol_data:
        protocol_df = pd.concat(all_protocol_data, ignore_index=True)
    else:
        print("No protocol files identified!")
        return None, None, None
    
    # Combine all Mock CRF data
    all_crf_data = []
    for filename, df in mock_crf_files:
        all_crf_data.append(df)
    
    if all_crf_data:
        mock_crf_df = pd.concat(all_crf_data, ignore_index=True)
    else:
        print("No Mock CRF files identified!")
        return None, None, None
    
    # Find visit label column (flexible column name matching)
    visit_col = None
    for col in protocol_df.columns:
        if any(keyword in col.lower() for keyword in ['visit', 'event', 'label']):
            visit_col = col
            break
    
    if not visit_col:
        print("Could not find visit label column in protocol data!")
        return None, None, None
    
    # Extract visit labels and generate automated mapping
    visit_labels = protocol_df[visit_col].dropna().unique().tolist()
    event_mapping = generate_event_mapping(visit_labels)
    
    # Create event mapping DataFrame
    event_mapping_df = pd.DataFrame(
        list(event_mapping.items()), 
        columns=[visit_col, 'Event_Name']
    )
    
    # Apply mapping to protocol data
    protocol_with_events = pd.merge(protocol_df, event_mapping_df, on=visit_col, how='left')
    
    # Extract form information from Mock CRF (flexible column matching)
    form_cols = {}
    for col in mock_crf_df.columns:
        if 'form' in col.lower() and 'name' in col.lower():
            form_cols['Form_Name'] = col
        elif 'form' in col.lower() and 'label' in col.lower():
            form_cols['Form_Label'] = col
    
    if form_cols:
        forms_df = mock_crf_df[list(form_cols.values())].drop_duplicates()
        forms_df.columns = list(form_cols.keys())
    else:
        print("Could not find form name/label columns in Mock CRF data!")
        forms_df = pd.DataFrame()
    
    # Create final schedule grid structure
    available_cols = []
    col_mapping = {}
    
    for col in protocol_with_events.columns:
        if 'group' in col.lower():
            available_cols.append(col)
            col_mapping[col] = 'Event_Group'
        elif 'window' in col.lower():
            available_cols.append(col)
            col_mapping[col] = 'Visit_Window'
    
    # Always include these columns
    required_cols = [visit_col, 'Event_Name']
    schedule_grid_cols = required_cols + available_cols
    
    schedule_grid = protocol_with_events[schedule_grid_cols].copy()
    
    # Rename columns for standard format
    rename_dict = {visit_col: 'Event_Label'}
    rename_dict.update(col_mapping)
    schedule_grid.rename(columns=rename_dict, inplace=True)
    
    return schedule_grid, forms_df, event_mapping

# Usage Example
folder_path = "path/to/your/excel/files"  # Replace with your actual folder path

schedule_grid, forms, mapping = create_automated_schedule_grid_from_folder(folder_path)

if schedule_grid is not None:
    print("\nAutomatically Generated Event Mapping:")
    for visit, event in mapping.items():
        print(f"{visit} -> {event}")
    
    print(f"\nSchedule Grid Shape: {schedule_grid.shape}")
    print(f"Forms DataFrame Shape: {forms.shape}")
    
    # Export results
    with pd.ExcelWriter('Generated_PTD_Schedule_Grid.xlsx') as writer:
        schedule_grid.to_excel(writer, sheet_name='Schedule Grid', index=False)
        forms.to_excel(writer, sheet_name='Study Specific Form', index=False)
    
    print("\nPTD file generated: Generated_PTD_Schedule_Grid.xlsx")
else:
    print("Failed to process files. Check your folder path and file contents.")
