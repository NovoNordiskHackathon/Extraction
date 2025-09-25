import json
import pandas as pd

json_file = "structuring_protocol_json/texttablestructured_protocol.json"


def extract_schedule_table(json_file):
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Look for structured table data (lists of dicts), not just keywords in strings
    def find_table_structures(obj, path=""):
        tables = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key

                # Only check list structures that could be tables
                if isinstance(value, list) and len(value) > 1:
                    # Check if it's a table (list of dictionaries)
                    if all(isinstance(item, dict) for item in value if item):
                        tables.append({
                            'path': current_path,
                            'data': value,
                            'row_count': len(value)
                        })

                # Recurse into nested structures
                tables.extend(find_table_structures(value, current_path))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                current_path = f"{path}[{i}]" if path else f"[{i}]"
                tables.extend(find_table_structures(item, current_path))

        return tables

    # Find all table structures
    tables = find_table_structures(data)

    if not tables:
        print("No table structures found in JSON.")
        return None

    print(f"Found {len(tables)} potential table(s):")

    # Try to convert each table to DataFrame and pick the best one
    best_table = None
    best_score = 0

    for i, table_info in enumerate(tables):
        try:
            df = pd.DataFrame(table_info['data'])

            if df.empty:
                continue

            # Calculate schedule likelihood score
            score = 0
            columns_text = ' '.join([str(col).lower() for col in df.columns])

            # Check for schedule-related column names
            schedule_indicators = ['visit', 'week', 'procedure', 'form', 'day', 'assessment', 'activity']
            score += sum(2 for indicator in schedule_indicators if indicator in columns_text)

            # Check data content for schedule keywords
            data_text = ' '.join([str(val).lower() for val in df.values.flatten()[:100]])  # First 100 values
            content_indicators = ['screening', 'randomisation', 'treatment', 'v1', 'v2']
            score += sum(1 for indicator in content_indicators if indicator in data_text)

            # Prefer larger tables
            score += len(df) * 0.1

            print(f"{i + 1}. Path: {table_info['path']}")
            print(f"   Shape: {df.shape}")
            print(f"   Columns: {list(df.columns)[:5]}")  # Show first 5 columns
            print(f"   Score: {score:.1f}")
            print()

            if score > best_score:
                best_score = score
                best_table = df

        except Exception as e:
            print(f"{i + 1}. Path: {table_info['path']} - Error: {e}")

    if best_table is not None:
        print(f"🏆 Selected best table (score: {best_score:.1f})")
        print(f"Shape: {best_table.shape}")
        print("\n📋 Schedule of Activities DataFrame:")
        print(best_table.head(10))  # Show first 10 rows
        return best_table
    else:
        print("No suitable table found for conversion to DataFrame.")
        return None


# Extract the schedule
schedule_df = extract_schedule_table(json_file)

if schedule_df is not None:
    print(f"\n✅ SUCCESS! Extracted Schedule of Activities")
    print(f"📊 Shape: {schedule_df.shape}")
    print(f"📋 Columns: {list(schedule_df.columns)}")

    # Optional: Save to Excel
    # schedule_df.to_excel('schedule_of_activities.xlsx', index=False)
    # print("💾 Saved to schedule_of_activities.xlsx")
else:
    print("❌ Could not extract Schedule of Activities")
