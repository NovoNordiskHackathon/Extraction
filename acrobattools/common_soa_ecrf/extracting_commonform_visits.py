import pandas as pd
from difflib import SequenceMatcher

def fuzzy_match(a, b):
    """Calculate similarity ratio between two strings."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def generate_ordered_soa_matrix(ecrf_file, schedule_file, output_file, threshold=0.5, include_unmapped=False):
    """
    Generate SoA matrix with per-visit ordering used by clinicians,
    using fuzzy matching to map eCRF forms to protocol procedures.

    Parameters:
    -----------
    ecrf_file : str
        Path to extracted_forms_final_with_source.csv
    schedule_file : str
        Path to schedule.csv
    output_file : str
        Output CSV path
    threshold : float, optional
        Fuzzy matching threshold (default: 0.5)
    include_unmapped : bool, optional
        Include unmapped forms at the end (default: False)
    """

    # Load data
    extracted = pd.read_csv(ecrf_file)
    schedule = pd.read_csv(schedule_file)

    # Procedure order from schedule
    proc_order = list(schedule['Procedure'])

    # Fuzzy mapping: Best match per form
    form_order_map = {}
    unmapped_forms = []
    for form_label in extracted['Form Label'].unique():
        best_score = 0
        best_idx = 9999  # High index for unmapped
        best_proc = None
        for idx, proc in enumerate(proc_order):
            score = fuzzy_match(proc, form_label)
            if score >= threshold and score > best_score:
                best_score = score
                best_idx = idx
                best_proc = proc
        if best_proc:
            form_order_map[form_label] = {'index': best_idx, 'procedure': best_proc}
        else:
            unmapped_forms.append(form_label)
            if include_unmapped:
                form_order_map[form_label] = {'index': 9999, 'procedure': 'Unmapped'}

    print(f"Unmapped forms: {unmapped_forms}")

    # Sort extracted forms based on mapping
    extracted['SortIndex'] = extracted['Form Label'].map(lambda x: form_order_map.get(x, {'index': 9999})['index'])
    ex_sorted = extracted.sort_values('SortIndex').reset_index(drop=True)

    # Visit order from schedule
    visits = [col for col in schedule.columns if col != 'Procedure']

    # Initialize matrix without Procedure column
    data_rows = []
    for _, row in ex_sorted.iterrows():
        visits_list = []
        if pd.notna(row['Visits']):
            # Robust parsing: strip and handle potential issues
            visits_list = [v.strip() for v in str(row['Visits']).split(',') if v.strip()]

        row_dict = {
            'Form Label': row['Form Label'],
            'Form Name': row['Form Name'],
            'Source': row.get('Source', ''),
            'Is Form Dynamic?': row.get('Dynamic Trigger', 'No'),
            'Form Dynamic Criteria': row.get('Trigger Details', '')
        }

        for visit in visits:
            row_dict[visit] = ''
        data_rows.append(row_dict)

    matrix_df = pd.DataFrame(data_rows)
    matrix_df = matrix_df.astype({v: object for v in visits})

    # Assign sequential numbers per visit
    for visit in visits:
        counter = 1
        for idx, row in matrix_df.iterrows():
            visits_list = []
            if pd.notna(ex_sorted.loc[idx, 'Visits']):
                visits_list = [v.strip() for v in str(ex_sorted.loc[idx, 'Visits']).split(',') if v.strip()]
            if visit in visits_list:
                matrix_df.at[idx, visit] = counter
                counter += 1
            else:
                matrix_df.at[idx, visit] = ''

    matrix_df.to_csv(output_file, index=False)
    print(f"SoA matrix saved to {output_file}")
    return matrix_df

if __name__ == "__main__":
    ecrf_file = '../structuring_ecrf_json/extracted_forms_final_with_source.csv'
    schedule_file = '../Schedule_of_activities/schedule.csv'
    output_file = 'Final_Complete_eCRF_Matrix.csv'
    generate_ordered_soa_matrix(ecrf_file, schedule_file, output_file)
