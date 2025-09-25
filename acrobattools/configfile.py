import pandas as pd
from pathlib import Path

# Load extracted schedule grid mapping (CSV from previous processing)
schedule_csv = Path("schedule_grid/ecrf_formlabel_formname_visits_below.csv")
df = pd.read_csv(schedule_csv)

# Example: Filter forms that are triggered (have at least one visit with valid trigger)
def is_triggered(row):
    # Assuming visit columns are string with X (triggered) or numbers, blank means no trigger
    # This example checks if any visit column is non-empty (meaning triggered)
    visit_cols = [col for col in df.columns if col.startswith('V')]
    for col in visit_cols:
        val = row.get(col)
        if pd.notna(val) and str(val).strip() != "":
            return True
    return False

# Depending on your SoA structure, you might customize the above logic

# Filter triggered forms
triggered_forms_df = df[df.apply(is_triggered, axis=1)]

# Export or save minimal config of triggered forms
triggered_config = triggered_forms_df[["Form Name", "Form Label", "Visits"]]
triggered_config.to_csv("triggered_forms_config.csv", index=False)

print(f"✅ Triggered forms config saved: triggered_forms_config.csv")
print(triggered_config)
