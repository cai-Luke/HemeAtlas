import pandas as pd
import sys
import os
import re

def apply_curator_list(text, csv_path='data/atlas.csv'):
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return

    # Check if it is an exclusion list or reclassification list
    is_exclude = "Exclude" in text and "path_status=\"excluded\"" in text
    
    target_label = None
    if is_exclude:
        print("Target: EXCLUSION")
    else:
        # Extract target label from header: Reclassify X cells to "Label" (label_id).
        label_match = re.search(r'\(([^)]+)\)\.', text)
        if not label_match:
            print("Error: Could not find target label ID in parentheses (e.g. '(neutrophil).')")
            return
        target_label = label_match.group(1)
        print(f"Target Label: {target_label}")

    # Find the data lines (starting after the header line 'image_id,filename,current_label')
    lines = text.strip().split('\n')
    start_idx = -1
    for i, line in enumerate(lines):
        if 'image_id,filename,current_label' in line:
            start_idx = i + 1
            break
    
    if start_idx == -1 or start_idx >= len(lines):
        print("Error: Could not find data rows below header.")
        return

    # Load CSV
    df = pd.read_csv(csv_path, low_memory=False)
    
    count = 0
    for i in range(start_idx, len(lines)):
        row = lines[i].strip()
        if not row: continue
        
        parts = row.split(',')
        if len(parts) < 1: continue
        
        image_id = parts[0].strip()
        
        # Apply update
        mask = df['image_id'] == image_id
        if mask.any():
            if is_exclude:
                df.loc[mask, 'path_status'] = 'excluded'
                note = '; curator-exclude'
            else:
                # Update BOTH labels to ensure it 'moves' in the UI regardless of overrides
                df.loc[mask, 'path_label'] = target_label
                df.loc[mask, 'correction_label'] = target_label
                df.loc[mask, 'path_status'] = 'finalized'
                note = f'; curator-reclassify:{target_label}'
            
            # Add audit note
            current_note = str(df.loc[mask, 'tech_note'].values[0]) if not pd.isna(df.loc[mask, 'tech_note'].values[0]) else ''
            if note not in current_note:
                df.loc[mask, 'tech_note'] = current_note + note
            
            count += 1
        else:
            print(f"Warning: No record found for image_id {image_id}")

    df.to_csv(csv_path, index=False)
    action = "excluded" if is_exclude else f"reclassified to {target_label}"
    print(f"Successfully {action} {count} cells (updated atlas.csv)")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        input_text = sys.stdin.read()
        if input_text:
            apply_curator_list(input_text)
        else:
            print("Usage: pbpaste | python3 apply_curator_session.py")
    else:
        apply_curator_list(sys.argv[1])
