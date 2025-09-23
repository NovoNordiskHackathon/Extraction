import json
import re
import pandas as pd
from pathlib import Path

# Correct path to the JSON
ecrf_file = Path("/home/ibab/Desktop/Novo_Nordisk/Extraction/acrobattools/texttablestructured_ecrf.json")
with open(ecrf_file, "r", encoding="utf-8") as f:
    ecrf = json.load(f)

elements = ecrf.get("elements", [])
forms = []

for idx, el in enumerate(elements):
    txt = el.get("Text", "").strip()

    # Find visit list line
    visit_matches = re.findall(r"\bV\d+[A-Z]?\b", txt)
    if visit_matches:
        # Look below visits line (forward scan) for Form Label
        label = ""
        for offset in range(1, 5):
            next_idx = idx + offset
            if next_idx < len(elements):
                next_txt = elements[next_idx].get("Text", "").strip()
                if next_txt and not re.match(r"\[.*\]", next_txt.lower()) and "key:" not in next_txt.lower() and len(next_txt) > 5:
                    label = next_txt
                    break

        # Look below visits line (forward scan) for Form Name
        form_name = ""
        for offset in range(1, 6):
            next_idx = idx + offset
            if next_idx < len(elements):
                next_txt = elements[next_idx].get("Text", "").strip()
                if re.match(r"\[.*\]", next_txt):
                    form_name = next_txt
                    break

        if label and form_name:
            forms.append({
                "Form Label": label,
                "Form Name": form_name,
                "Visits": ", ".join(visit_matches)
            })

# Convert to dataframe, clean, and save
forms_df = pd.DataFrame(forms)
forms_df = forms_df.drop_duplicates(subset=["Form Label", "Form Name"])
forms_df = forms_df[forms_df["Form Label"].str.len() > 5]

forms_df.to_csv("ecrf_formlabel_formname_visits_below.csv", index=False)
print(forms_df)
