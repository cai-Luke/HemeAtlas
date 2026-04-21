import pandas as pd
import numpy as np
from pathlib import Path

REPO_ROOT = Path("/Users/holemini/Desktop/HemeAtlas")
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"

def classify_acevedo():
    print(f"Loading atlas from {ATLAS_CSV}...")
    df = pd.read_csv(ATLAS_CSV, low_memory=False)
    
    # Identify features
    m_cols = [c for c in df.columns if c.startswith('m_') and c != 'm_seg_quality']
    
    # Separate Training and Target sets
    # Training: Non-Acevedo, Finalized, Good segmentation
    train_mask = (~df['image_id'].str.startswith('ACE_', na=False)) & (df['path_status'] == 'finalized') & (df['m_seg_quality'] == 'good')
    # Target: All Acevedo records
    target_mask = df['image_id'].str.startswith('ACE_', na=False)
    
    train_df = df[train_mask].copy()
    target_df = df[target_mask].copy()
    
    print(f"Training on {len(train_df)} non-Acevedo records...")
    print(f"Targeting {len(target_df)} Acevedo records...")
    
    # Preprocessing
    # 1. Fill NaNs with median of train set
    medians = train_df[m_cols].median()
    X_train = train_df[m_cols].fillna(medians)
    X_target = target_df[m_cols].fillna(medians)
    
    # 2. Standardization
    mean = X_train.mean()
    std = X_train.std().replace(0, 1) # avoid div by zero
    X_train_norm = (X_train - mean) / std
    X_target_norm = (X_target - mean) / std
    
    # 3. Calculate Centroids
    labels = train_df['path_label'].unique()
    centroids = {}
    for label in labels:
        label_mask = train_df['path_label'] == label
        if label_mask.any():
            centroids[label] = X_train_norm[label_mask].mean()
            
    centroid_matrix = np.array([centroids[l] for l in labels])
    
    # 4. Predict (Nearest Centroid)
    def predict(row_norm):
        # Euclidean distance to all centroids
        dists = np.linalg.norm(centroid_matrix - row_norm.values, axis=1)
        return labels[np.argmin(dists)]
    
    print("Classifying...")
    predictions = X_target_norm.apply(predict, axis=1)
    
    # 5. Update original dataframe
    # We update image_id by image_id to be safe
    pred_map = dict(zip(target_df['image_id'], predictions))
    
    def update_row(row):
        if row['image_id'] in pred_map:
            pred = pred_map[row['image_id']]
            # Only update if correction_label is empty
            if pd.isna(row['correction_label']) or row['correction_label'] == '':
                row['correction_label'] = pred
            
            # Set status to pending_approval as requested
            row['path_status'] = 'pending_approval'
            
            # Note the prediction
            note = f"Preliminary classification: {pred}"
            if pd.isna(row['tech_note']) or row['tech_note'] == '':
                row['tech_note'] = note
            else:
                if note not in str(row['tech_note']):
                    row['tech_note'] = str(row['tech_note']) + " | " + note
        return row
    
    df = df.apply(update_row, axis=1)
    
    print(f"Saving updated atlas to {ATLAS_CSV}...")
    df.to_csv(ATLAS_CSV, index=False)
    print("Done!")

if __name__ == "__main__":
    classify_acevedo()
