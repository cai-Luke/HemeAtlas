import pandas as pd
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).parent
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"
MORPH_CSV = REPO_ROOT / "morphometry.csv"

def main():
    print(f"Merging {MORPH_CSV} into {ATLAS_CSV}...")
    
    # Load data
    atlas = pd.read_csv(ATLAS_CSV, low_memory=False)
    morph = pd.read_csv(MORPH_CSV)
    
    # Get the list of metric columns (starting with m_)
    m_cols = [c for c in morph.columns if c.startswith('m_')]
    
    # Remove existing m_ columns from atlas to avoid duplicates
    # Except image_id which we use for joining
    atlas_filtered = atlas.drop(columns=[c for c in m_cols if c in atlas.columns])
    
    # Merge
    # We use 'left' join to keep all atlas records (even those not in morph)
    updated_atlas = pd.merge(atlas_filtered, morph[['image_id'] + m_cols], on='image_id', how='left')
    
    # Ensure original column order as much as possible
    # (Optional, but helps keep the CSV clean)
    
    # Save back
    updated_atlas.to_csv(ATLAS_CSV, index=False)
    print("Merge complete.")

if __name__ == "__main__":
    main()
