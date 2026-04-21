import os
import pandas as pd
from pathlib import Path

REPO_ROOT = Path("/Users/holemini/Desktop/HemeAtlas")
IMAGES_DIR = REPO_ROOT / "images"
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"

def ingest():
    df = pd.read_csv(ATLAS_CSV, low_memory=False)
    
    new_records = []
    
    # Mapping for prefixes
    mappings = {
        "images_temp_bne": {"prefix": "BNE_", "label": "BAND"},
        "images_temp_ig": [
            {"prefix": "PMY_", "label": "PROMYELOCYTE"},
            {"prefix": "MY_", "label": "MYELOCYTE"},
            {"prefix": "MMY_", "label": "METAMYELOCYTE"},
            {"prefix": "IG_", "label": "IG_UNCLASSIFIED"}
        ]
    }
    
    for folder, config in mappings.items():
        folder_path = REPO_ROOT / folder
        if not folder_path.exists(): continue
        
        for f in os.listdir(folder_path):
            if not f.endswith(".jpg"): continue
            
            original_label = "OTHER"
            new_filename = f"ACE_UNKNOWN_{f}"
            
            if isinstance(config, dict):
                original_label = config["label"]
                new_filename = f.replace(config["prefix"], f"ACE_{original_label}_")
            else:
                for sub in config:
                    if f.startswith(sub["prefix"]):
                        original_label = sub["label"]
                        new_filename = f.replace(sub["prefix"], f"ACE_{original_label}_")
                        break
            
            # Move and Rename
            src = folder_path / f
            dest = IMAGES_DIR / new_filename
            os.rename(src, dest)
            
            # Create Record
            img_id = new_filename.replace(".jpg", "")
            new_records.append({
                "image_id": img_id,
                "filename": new_filename,
                "path_label": original_label,
                "case_tag": "acevedo",
                "path_status": "finalized",
                "tech_note": f"Ingested from Acevedo dataset. Original label: {original_label}"
            })

    if new_records:
        new_df = pd.DataFrame(new_records)
        updated_df = pd.concat([df, new_df], ignore_index=True)
        updated_df.to_csv(ATLAS_CSV, index=False)
        print(f"Ingested {len(new_records)} cells from Acevedo.")
    else:
        print("No records to ingest.")

if __name__ == "__main__":
    ingest()
