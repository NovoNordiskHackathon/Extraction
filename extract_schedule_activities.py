import pandas as pd
import os

folder_path = "./tables_protocol"
search_headers = [
    "procedure", "protocol section", "screening", "treatment", "dose escalation",
    "randomisation", "dose maintenance", "visit short name", "study week"
]

for file in os.listdir(folder_path):
    if file.endswith(".xlsx"):
        file_path = os.path.join(folder_path, file)
        try:
            xls = pd.ExcelFile(file_path)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name, header=None, dtype=str)
                df_flat = df.fillna("").map(lambda x: str(x).strip().lower())

                keyword_hits = []
                for h in search_headers:
                    hit = df_flat.map(lambda x: h in x).any().any()
                    keyword_hits.append(hit)

                if all(keyword_hits):  # All keywords found
                    print(f"Likely contains schedule table in file: {file}, sheet: {sheet_name}")
        except Exception as e:
            print(f"Could not read {file}: {e}")
