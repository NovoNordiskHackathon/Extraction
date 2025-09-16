import pandas as pd
import glob
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def search_text_in_excel(search_term: str, directory: str):
    """
    Searches for a specific text term within all Excel files in a directory.

    Args:
        search_term (str): The term to search for (case-insensitive).
        directory (str): The directory containing the Excel files.
    """
    found_in = []
    file_pattern = os.path.join(directory, "*.xlsx")
    excel_files = glob.glob(file_pattern)

    if not excel_files:
        logging.warning(f"No files found matching the pattern: {file_pattern}")
        return

    logging.info(f"Searching for '{search_term}' in {len(excel_files)} Excel files...")

    for file_path in excel_files:
        try:
            # Read all sheets from the Excel file
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)

                # Check for the search term in the entire DataFrame (case-insensitive)
                # Convert the DataFrame to a string to search all cells
                if df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any().any():
                    found_in.append(f"{file_path} (Sheet: {sheet_name})")
                    # Break the inner loop once found in one sheet
                    break
        except Exception as e:
            logging.error(f"Could not process file {file_path}: {e}")

    # Print the results
    if found_in:
        logging.info("Search term found in the following locations:")
        for location in found_in:
            print(f"- {location}")
    else:
        logging.info(f"Search term '{search_term}' not found in any of the files.")


if __name__ == "__main__":
    # Define the directory where your Excel files are located
    mock_crf_dir = '/home/ibab/PycharmProjects/DL-Lab/acrobattools/tables_ecrf'
    protocol_dir = '/home/ibab/PycharmProjects/DL-Lab/acrobattools/tables_protocol'

    # Example usage: Search for "Dose escalation" in the Protocol directory
    search_term = 'Dose escalation'
    print(f"--- Searching in Protocol Directory: {protocol_dir} ---")
    search_text_in_excel(search_term, protocol_dir)

    print("\n" + "=" * 50 + "\n")

    # Example usage: Search for "Form Label" in the Mock CRF directory
    search_term = 'Form Label'
    print(f"--- Searching in Mock CRF Directory: {mock_crf_dir} ---")
    search_text_in_excel(search_term, mock_crf_dir)