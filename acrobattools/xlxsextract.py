import pandas as pd
import glob
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def search_text_in_excel(search_term: str, file_pattern: str):
    """
    Searches for a specific text term within all Excel files matching a pattern.

    Args:
        search_term (str): The term to search for (case-insensitive).
        file_pattern (str): The file pattern to search, e.g., "*.xlsx".
    """
    found_in = []

    # Use glob to find all files matching the pattern
    excel_files = glob.glob(file_pattern)

    if not excel_files:
        logging.warning(f"No files found matching the pattern: {file_pattern}")
        return

    logging.info(f"Searching for '{search_term}' in {len(excel_files)} Excel files...")

    # Iterate through each Excel file
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
                    # Break the inner loop once found in one sheet to avoid duplicates
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
    search_term = 'Dose escalation'
    file_pattern = 'tables_ecrf/*.xlsx'  # Search all files ending with .xlsx in the current directory

    # Run the search
    search_text_in_excel(search_term, file_pattern)