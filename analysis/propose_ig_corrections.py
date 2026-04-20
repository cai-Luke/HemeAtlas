import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
from pathlib import Path

# Configuration
MATURATION_ORDER = ['MYELOCYTE', 'METAMYELOCYTE', 'BAND', 'NEUTROPHIL']

WEIGHTS = {
    'm_nuc_glcm_contrast': ('forward',  0.40),
    'm_nc_ratio':          ('inverted', 0.20),
    'm_nuc_solidity':      ('inverted', 0.20),
    'm_nuc_irregularity':  ('inverted', 0.20),
}

OUTLIER_QUANTILES = (0.10, 0.90)
NORM_PERCENTILES  = (5, 95)

# Setup paths
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = BASE_DIR / "data" / "atlas.csv"
OUTPUT_DIR = BASE_DIR / "analysis" / "ig"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def norm(x, lo, hi):
    if hi == lo:
        return 0.5
    return (x - lo) / (hi - lo)

def main():
    parser = argparse.ArgumentParser(description="Propose reclassification for KO_ immature granulocytes.")
    parser.add_argument("--cw-anchored", action="store_true", help="Use CW_ records for normalization bounds.")
    args = parser.parse_args()

    print(f"Reading {DATA_PATH}...")
    df = pd.read_csv(DATA_PATH, low_memory=False)

    # 1. Load and filter
    # Base criteria: finalized, good seg, blank correction
    base_mask = (
        (df['path_status'] == 'finalized') &
        (df['m_seg_quality'] == 'good') &
        ((df['correction_label'].isna()) | (df['correction_label'] == ''))
    )

    # Main IG set: KO_ cells in MATURATION_ORDER
    ig_mask = base_mask & (df['image_id'].str.startswith('KO_', na=False)) & (df['path_label'].isin(MATURATION_ORDER))
    ig = df[ig_mask].copy()

    # Drop rows where m_nuc_area is 0/NaN to avoid divide-by-zero
    # m_nuc_irregularity is derived from deficiency and area
    calc_cols = ['m_nuc_convex_deficiency', 'm_nuc_area'] + [k for k in WEIGHTS.keys() if k != 'm_nuc_irregularity']
    for col in calc_cols:
        ig[col] = pd.to_numeric(ig[col], errors='coerce')
    
    ig = ig.dropna(subset=['m_nuc_area'])
    ig = ig[ig['m_nuc_area'] > 0]
    
    # Compute Derived Irregularity
    ig['m_nuc_irregularity'] = ig['m_nuc_convex_deficiency'] / ig['m_nuc_area']
    
    print(f"Loaded {len(ig)} IG records for analysis.")

    # 2. Normalization bounds
    # If cw-anchored, use CW_ NEUTROPHIL and BAND as well
    if args.cw_anchored:
        anchor_mask = base_mask & (df['image_id'].str.startswith('CW_', na=False)) & (df['path_label'].isin(['NEUTROPHIL', 'BAND']))
        anchor_df = df[anchor_mask].copy()
        calc_cols = ['m_nuc_convex_deficiency', 'm_nuc_area'] + [k for k in WEIGHTS.keys() if k != 'm_nuc_irregularity']
        for col in calc_cols:
            anchor_df[col] = pd.to_numeric(anchor_df[col], errors='coerce')
        anchor_df = anchor_df.dropna(subset=['m_nuc_area'])
        anchor_df = anchor_df[anchor_df['m_nuc_area'] > 0]
        anchor_df['m_nuc_irregularity'] = anchor_df['m_nuc_convex_deficiency'] / anchor_df['m_nuc_area']
        norm_ref = pd.concat([ig, anchor_df])
        print(f"Normalization bounds anchored on KO_ + {len(anchor_df)} CW_ cells.")
    else:
        norm_ref = ig
        print("Normalization bounds anchored on KO_ cells only.")

    bounds = {}
    for feat in WEIGHTS.keys():
        lo, hi = np.percentile(norm_ref[feat].dropna(), NORM_PERCENTILES)
        bounds[feat] = (lo, hi)

    # 3. Compute maturation score
    ig['maturation_score'] = 0.0
    for feat, (direction, weight) in WEIGHTS.items():
        lo, hi = bounds[feat]
        val_norm = ig[feat].apply(lambda x: np.clip(norm(x, lo, hi), 0, 1))
        
        if direction == 'forward':
            ig['maturation_score'] += weight * val_norm
        else:
            ig['maturation_score'] += weight * (1 - val_norm)

    # 4. Per-label expected ranges (p10, p90)
    expected = ig.groupby('path_label')['maturation_score'].quantile(OUTLIER_QUANTILES).unstack()
    expected = expected.reindex(MATURATION_ORDER)
    print("\nPer-label Expected Ranges (p10 - p90):")
    print(expected)

    # 5. Flag outliers
    proposals = []
    
    # Adjacency map
    prev_map = {stage: (MATURATION_ORDER[i-1] if i > 0 else None) for i, stage in enumerate(MATURATION_ORDER)}
    next_map = {stage: (MATURATION_ORDER[i+1] if i < len(MATURATION_ORDER)-1 else None) for i, stage in enumerate(MATURATION_ORDER)}

    for idx, row in ig.iterrows():
        label = row['path_label']
        score = row['maturation_score']
        p10, p90 = expected.loc[label]
        
        prev_stage = prev_map[label]
        next_stage = next_map[label]
        
        proposed = None
        reason = ""

        # Case A: Too mature for current label
        if next_stage and score > p90:
            next_p10 = expected.loc[next_stage, 0.10]
            if score > next_p10:
                proposed = next_stage
                reason = f"score {score:.3f} > p90({label})={p90:.3f}, within p10({next_stage})={next_p10:.3f}"

        # Case B: Too immature for current label
        elif prev_stage and score < p10:
            prev_p90 = expected.loc[prev_stage, 0.90]
            if score < prev_p90:
                proposed = prev_stage
                reason = f"score {score:.3f} < p10({label})={p10:.3f}, within p90({prev_stage})={prev_p90:.3f}"
        
        if proposed:
            proposals.append({
                'image_id': row['image_id'],
                'path_label': label,
                'maturation_score': score,
                'proposed_correction_label': proposed,
                'reason': reason
            })

    # 6. Output
    proposals_df = pd.DataFrame(proposals)
    proposals_df.to_csv(OUTPUT_DIR / "proposed_corrections.csv", index=False)
    
    # Plot maturation score distribution
    plt.figure(figsize=(10, 6))
    sns.violinplot(x='path_label', y='maturation_score', data=ig, order=MATURATION_ORDER, inner='quartile')
    plt.title(f"Maturation Score Distribution (CW-Anchored: {args.cw_anchored})")
    plt.savefig(OUTPUT_DIR / "maturation_score_dist.pdf")
    plt.close()

    # Final Summary
    total = len(ig)
    flagged = len(proposals_df)
    print(f"\nTotal IG cells analyzed: {total}")
    print(f"Cells flagged: {flagged} ({100*flagged/total:.1f}%)")
    
    if flagged > 0:
        counts = proposals_df.groupby(['path_label', 'proposed_correction_label']).size().reset_index(name='count')
        for _, r in counts.iterrows():
            print(f"  {r['path_label']} -> {r['proposed_correction_label']}: {r['count']}")

    print(f"\nPhase 2 Complete. Proposal written to {OUTPUT_DIR / 'proposed_corrections.csv'}")

if __name__ == "__main__":
    main()
