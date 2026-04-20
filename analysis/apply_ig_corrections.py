import pandas as pd
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).parent.parent
ATLAS_PATH = BASE_DIR / "data" / "atlas.csv"
CORRECTIONS_PATH = BASE_DIR / "analysis" / "ig" / "proposed_corrections.csv"

def main():
    print(f"Reading {ATLAS_PATH}...")
    # Read as string to preserve all formatting and avoid type inference issues
    atlas = pd.read_csv(ATLAS_PATH, dtype=str, keep_default_na=False)
    
    print(f"Reading {CORRECTIONS_PATH}...")
    corrections = pd.read_csv(CORRECTIONS_PATH, dtype=str)
    
    print(f"Applying {len(corrections)} corrections...")
    
    applied_count = 0
    for _, corr in corrections.iterrows():
        img_id = corr['image_id']
        new_label = corr['proposed_correction_label']
        
        # Match by image_id where correction_label is currently empty
        mask = (atlas['image_id'] == img_id) & ((atlas['correction_label'] == '') | (atlas['correction_label'].isna()))
        
        if mask.any():
            atlas.loc[mask, 'correction_label'] = new_label
            # Update tech_note for traceability
            current_note = atlas.loc[mask, 'tech_note'].values[0]
            note_append = "morphometry-reclassification-ig-v1"
            if current_note:
                atlas.loc[mask, 'tech_note'] = f"{current_note}; {note_append}"
            else:
                atlas.loc[mask, 'tech_note'] = note_append
            applied_count += 1

    if applied_count > 0:
        atlas.to_csv(ATLAS_PATH, index=False)
        print(f"Successfully applied {applied_count} corrections to atlas.csv.")
    else:
        print("No new corrections to apply.")

if __name__ == "__main__":
    main()
