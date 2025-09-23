#!/usr/bin/env python3
"""
Automate PTD (Protocol-to-Data) document generation
from Protocol and CRF extracted JSONs.
"""

import json
import re
import pandas as pd
from pathlib import Path
from collections import OrderedDict

# ---------- Input Files ----------
protocol_file = Path("texttablestructured_protocol.json")
crf_file = Path("texttablestructured_ecrf.json")

# ---------- Output Files ----------
out_json = Path("ptd_schema.json")
out_csv = Path("ptd_schema.csv")

# ---------- Helpers ----------
def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def gather_texts(data):
    res = []
    for el in data.get("elements", []):
        txt = el.get("Text")
        path = el.get("Path", "")
        if txt and isinstance(txt, str) and txt.strip():
            res.append((path, txt.strip()))
    return res

def extract_headings(texts):
    return [txt for path, txt in texts if re.search(r'/H\d|/Title|/TOC', path, re.IGNORECASE)]

def extract_visit_ids(texts):
    visits = set()
    for _, txt in texts:
        for m in re.findall(r'\b(V(?:isit)?\d+[A-Z]?)\b', txt, flags=re.IGNORECASE):
            v = m.upper().replace("VISIT", "V")
            visits.add(v)
    return sorted(visits, key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)

def extract_forms_and_fields(texts):
    forms = OrderedDict()
    current_form = None
    for _, txt in texts:
        if re.search(r'(Form|Collection|Sample|Lab|CRF|\[LAB_|\bPRO\b|\bQuestionnaire\b)', txt, re.IGNORECASE):
            current_form = txt
            if current_form not in forms:
                forms[current_form] = []
            continue
        if current_form and (txt.endswith("?") or re.search(r'(Date|Time|Collected|Fasting|Status|Assessment|Result|Value)', txt, re.IGNORECASE)):
            forms[current_form].append(txt)
    return forms

def link_forms_to_protocol(forms, protocol_texts):
    proto_text = " ".join(t for _, t in protocol_texts).lower()
    mapping = []
    for form, fields in forms.items():
        linked = []
        if "schedule" in proto_text:
            linked.append("Schedule of Activities")
        if "endpoint" in proto_text or "estimand" in proto_text:
            linked.append("Endpoints/Estimands")
        if "inclusion" in proto_text or "exclusion" in proto_text:
            linked.append("Study Population")
        if "safety" in proto_text or "adverse" in proto_text:
            linked.append("Safety Reporting")
        mapping.append({"Form": form, "Fields": fields, "LinkedSections": linked})
    return mapping

# ---------- Load Data ----------
protocol_data = load_json(protocol_file)
crf_data = load_json(crf_file)

protocol_texts = gather_texts(protocol_data)
crf_texts = gather_texts(crf_data)

visits = extract_visit_ids(crf_texts)
forms = extract_forms_and_fields(crf_texts)
form_mapping = link_forms_to_protocol(forms, protocol_texts)

# ---------- Build Unified Schema ----------
schema = {
    "StudyMetadata": {
        "StudyTitle": next((txt for txt in extract_headings(protocol_texts) if "protocol" in txt.lower()), "Unknown"),
        "Objectives": {
            "Primary": next((txt for _, txt in protocol_texts if "primary" in txt.lower()), "Not found"),
            "Secondary": next((txt for _, txt in protocol_texts if "secondary" in txt.lower()), "Not found")
        },
        "Endpoints": [txt for _, txt in protocol_texts if "endpoint" in txt.lower()]
    },
    "Visits": [{"VisitID": v, "Procedures": []} for v in visits],
    "Forms": []
}

for fm in form_mapping:
    schema["Forms"].append({
        "FormName": fm["Form"],
        "LinkedProtocolSection": fm["LinkedSections"],
        "Fields": [{"FieldName": f, "DataType": "string"} for f in fm["Fields"]]
    })

# ---------- Write JSON ----------
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(schema, f, indent=2)

# ---------- Write CSV ----------
rows = []
for visit in schema["Visits"]:
    for form in schema["Forms"]:
        for field in form["Fields"]:
            rows.append({
                "VisitID": visit["VisitID"],
                "FormName": form["FormName"],
                "FieldName": field["FieldName"],
                "DataType": field["DataType"],
                "LinkedProtocolSection": ";".join(form["LinkedProtocolSection"])
            })
df = pd.DataFrame(rows)
df.to_csv(out_csv, index=False)

print("✅ PTD schema generated:")
print(" - JSON:", out_json)
print(" - CSV:", out_csv)
