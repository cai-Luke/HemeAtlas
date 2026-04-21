import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import time

# Add parent to path to import morphometry
sys.path.append(str(Path(__file__).parent.parent))
from morphometry import process_image, M_COLUMNS

REPO_ROOT = Path(__file__).parent.parent
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"
IMAGES_DIR = REPO_ROOT / "images"

def run_sweep_step(tasks, threshold):
    print(f"  Testing threshold {threshold:.2f} ... ", end="", flush=True)
    t0 = time.time()
    
    # Update threshold in tasks
    step_tasks = [(p, i, threshold) for p, i, _ in tasks]
    
    num_workers = multiprocessing.cpu_count()
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(wrapper, step_tasks))
    
    df = pd.DataFrame(results)
    dt = time.time() - t0
    print(f"done in {dt:.1f}s")
    return df

def wrapper(args):
    return process_image(*args)

def evaluate_separation(df_morph, df_atlas):
    merged = df_morph.merge(df_atlas[["image_id", "path_label"]], on="image_id")
    
    # Focus on MYELOCYTE and METAMYELOCYTE separation using Max Indent
    group1 = merged[merged["path_label"] == "MYELOCYTE"]["m_nuc_max_indent"]
    group2 = merged[merged["path_label"] == "METAMYELOCYTE"]["m_nuc_max_indent"]
    
    if group1.empty or group2.empty:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    
    m1 = group1.mean()
    m2 = group2.mean()
    s1 = group1.std()
    s2 = group2.std()
    
    pooled_std = np.sqrt((s1**2 + s2**2) / 2)
    score = (m2 - m1) / pooled_std if pooled_std > 0 else 0
    
    return score, m1, m2, s1, s2

def main():
    print(f"Loading atlas from {ATLAS_CSV}...")
    atlas = pd.read_csv(ATLAS_CSV)
    
    # Select subset: 500 Myelocytes and 500 Metamyelocytes
    myelos = atlas[atlas["path_label"] == "MYELOCYTE"].sample(n=min(500, len(atlas[atlas["path_label"] == "MYELOCYTE"])), random_state=42)
    metas = atlas[atlas["path_label"] == "METAMYELOCYTE"].sample(n=min(500, len(atlas[atlas["path_label"] == "METAMYELOCYTE"])), random_state=42)
    subset = pd.concat([myelos, metas])
    
    tasks = []
    for _, row in subset.iterrows():
        path = IMAGES_DIR / row["filename"]
        if path.exists():
            tasks.append((path, row["image_id"], 4.0)) # threshold placeholder
            
    print(f"Running sweep on {len(tasks)} images (MYELO/META subset)...")
    
    thresholds = np.arange(30.0, 46.0, 2.0)
    results_summary = []
    
    for t in thresholds:
        df_morph = run_sweep_step(tasks, t)
        score, m1, m2, s1, s2 = evaluate_separation(df_morph, subset)
        
        results_summary.append({
            "threshold": t,
            "separation_score": score,
            "myelo_indent_mean": m1,
            "meta_indent_mean": m2,
            "myelo_indent_std": s1,
            "meta_indent_std": s2
        })
    
    summary_df = pd.DataFrame(results_summary)
    print("\n--- Sweep Results ---")
    print(summary_df.to_string(index=False, formatters={
        'threshold': '{:,.1f}'.format,
        'separation_score': '{:,.3f}'.format,
        'myelo_indent_mean': '{:,.3f}'.format,
        'meta_indent_mean': '{:,.3f}'.format
    }))
    
    best = summary_df.loc[summary_df["separation_score"].idxmax()]
    print(f"\nBest Threshold: {best['threshold']:.1f} (Score: {best['separation_score']:.3f})")
    print(f"Myelo Indent Mean: {best['myelo_indent_mean']:.3f}, Meta Indent Mean: {best['meta_indent_mean']:.3f}")

if __name__ == "__main__":
    main()
