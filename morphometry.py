"""
morphometry.py — Batch cell morphometry for HemeAtlas
Outputs morphometry.csv with m_ prefixed columns, ready to merge into atlas.csv.
"""

import os
import sys
import math
import warnings
import numpy as np
import pandas as pd
from PIL import Image
from pathlib import Path
from skimage import color, filters, morphology, measure, feature
from skimage.morphology import disk, binary_opening, binary_closing, remove_small_objects
from skimage.measure import label, regionprops
from scipy import ndimage as ndi
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"
IMAGES_DIR = REPO_ROOT / "images"
OUTPUT_CSV = REPO_ROOT / "morphometry.csv"

# ---------------------------------------------------------------------------
# Column Schema
# ---------------------------------------------------------------------------
M_COLUMNS = [
    "image_id",
    "m_cell_area", "m_cell_major", "m_cell_minor", "m_cell_eccentricity",
    "m_cell_circularity", "m_cell_solidity", "m_cell_equiv_diameter",
    "m_cell_aspect_ratio", "m_cell_extent",
    "m_nuc_area", "m_nuc_major", "m_nuc_minor", "m_nuc_eccentricity",
    "m_nuc_circularity", "m_nuc_solidity", "m_nuc_lobes", "m_nuc_irregularity",
    "m_nuc_convex_deficiency", "m_nc_ratio",
    "m_nuc_mean_l", "m_nuc_mean_a", "m_nuc_mean_b", "m_nuc_intensity_std",
    "m_cyto_mean_l", "m_cyto_mean_a", "m_cyto_mean_b", "m_cyto_mean_hue",
    "m_nuc_glcm_contrast", "m_nuc_glcm_homogeneity",
    "m_nuc_glcm_energy", "m_nuc_glcm_correlation",
    "m_seg_quality",
]

# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def segment_cell(img_rgb):
    """
    Nucleus-First Segmentation Strategy.
    1. Sample background from corners.
    2. Identify nucleus (dark + purple).
    3. Grow cell mask from nucleus using connectivity (darker than background + not too yellow).
    """
    h, w = img_rgb.shape[:2]
    lab = color.rgb2lab(img_rgb)
    L = lab[:, :, 0]; a = lab[:, :, 1]; b = lab[:, :, 2]
    
    # 1. Background Sampling
    corners_l = np.concatenate([L[:5,:5], L[:5,-5:], L[-5:,:5], L[-5:,-5:]])
    corners_a = np.concatenate([a[:5,:5], a[:5,-5:], a[-5:,:5], a[-5:,-5:]])
    corners_b = np.concatenate([b[:5,:5], b[:5,-5:], b[-5:,:5], b[-5:,-5:]])
    bg_l = np.median(corners_l); bg_a = np.median(corners_a); bg_b = np.median(corners_b)
    
    # 2. Nucleus First
    nuc_mask = (L < (bg_l - 20)) & (a > (bg_a + 10))
    nuc_mask = remove_small_objects(nuc_mask, min_size=500)
    
    labeled_nuc = label(nuc_mask)
    if labeled_nuc.max() == 0:
        # Fallback to liberal nucleus
        nuc_mask = (L < (bg_l - 15)) & (a > (bg_a + 5))
        nuc_mask = remove_small_objects(nuc_mask, min_size=200)
        labeled_nuc = label(nuc_mask)
        
    if labeled_nuc.max() == 0:
        return np.zeros_like(L, dtype=bool), np.zeros_like(L, dtype=bool), np.zeros_like(L, dtype=bool), "no_nucleus"
    
    nuc_props = regionprops(labeled_nuc)
    # Take center-most component
    best_nuc = min(nuc_props, key=lambda r: math.dist(r.centroid, (h/2, w/2)))
    nuc_mask = (labeled_nuc == best_nuc.label)
    
    # 3. Cell Growth
    # Candidate mask: Anything darker than background and not too yellow
    candidate_mask = (L < (bg_l - 5)) & (b < (bg_b + 5))
    labeled_cell = label(candidate_mask)
    nuc_y, nuc_x = best_nuc.centroid
    cell_label = labeled_cell[int(nuc_y), int(nuc_x)]
    
    if cell_label == 0:
        cell_mask = nuc_mask.copy()
    else:
        cell_mask = (labeled_cell == cell_label)
        
    cell_mask = binary_closing(cell_mask, disk(5))
    cell_mask = ndi.binary_fill_holes(cell_mask)
    
    # Safety: Ensure cell mask always contains nucleus mask
    cell_mask = cell_mask | nuc_mask
    
    cyto_mask = cell_mask & ~nuc_mask
    return cell_mask, nuc_mask, cyto_mask, "good"

# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

def process_image(image_path: Path, image_id: str) -> dict:
    row = {"image_id": image_id}
    try:
        img = Image.open(image_path).convert("RGB")
        img_rgb = np.array(img, dtype=np.float64) / 255.0
        
        cell_mask, nuc_mask, cyto_mask, quality = segment_cell(img_rgb)
        row["m_seg_quality"] = quality
        
        if quality == "no_nucleus":
            for col in M_COLUMNS:
                if col not in row: row[col] = 0.0
            return row
            
        # 1. Geometry
        c_area = float(cell_mask.sum())
        n_area = float(nuc_mask.sum())
        
        labeled_cell = label(cell_mask)
        cell_props = regionprops(labeled_cell)[0]
        labeled_nuc = label(nuc_mask)
        nuc_props = regionprops(labeled_nuc)[0]
        
        row["m_cell_area"] = c_area
        row["m_cell_major"] = float(cell_props.major_axis_length)
        row["m_cell_minor"] = float(cell_props.minor_axis_length)
        row["m_cell_eccentricity"] = float(cell_props.eccentricity)
        row["m_cell_circularity"] = 4 * np.pi * c_area / (cell_props.perimeter**2) if cell_props.perimeter > 0 else 0
        row["m_cell_solidity"] = float(cell_props.solidity)
        row["m_cell_equiv_diameter"] = float(cell_props.equivalent_diameter)
        row["m_cell_aspect_ratio"] = row["m_cell_major"] / row["m_cell_minor"] if row["m_cell_minor"] > 0 else 1
        row["m_cell_extent"] = float(cell_props.extent)
        
        row["m_nuc_area"] = n_area
        row["m_nuc_major"] = float(nuc_props.major_axis_length)
        row["m_nuc_minor"] = float(nuc_props.minor_axis_length)
        row["m_nuc_eccentricity"] = float(nuc_props.eccentricity)
        row["m_nuc_circularity"] = 4 * np.pi * n_area / (nuc_props.perimeter**2) if nuc_props.perimeter > 0 else 0
        row["m_nuc_solidity"] = float(nuc_props.solidity)
        
        # Lobes: morphological erosion
        row["m_nuc_lobes"] = 1.0
        if n_area > 1000:
            smoothed = ndi.gaussian_filter(nuc_mask.astype(float), sigma=4.0) > 0.5
            eroded = morphology.binary_erosion(smoothed, disk(8))
            eroded = remove_small_objects(eroded, min_size=150)
            row["m_nuc_lobes"] = float(label(eroded).max())
            
        # Irregularity: (hull - area) / hull
        try:
            from skimage.morphology import convex_hull_image
            hull = convex_hull_image(nuc_mask)
            ha = float(hull.sum())
            row["m_nuc_irregularity"] = (ha - n_area) / ha if ha > 0 else 0
            row["m_nuc_convex_deficiency"] = ha - n_area
        except:
            row["m_nuc_irregularity"] = 0.0
            row["m_nuc_convex_deficiency"] = 0.0
            
        row["m_nc_ratio"] = n_area / c_area if c_area > 0 else 0
        
        # 2. Color (Lab)
        lab = color.rgb2lab(img_rgb)
        L = lab[:, :, 0]; a = lab[:, :, 1]; b = lab[:, :, 2]
        
        row["m_nuc_mean_l"] = float(L[nuc_mask].mean())
        row["m_nuc_mean_a"] = float(a[nuc_mask].mean())
        row["m_nuc_mean_b"] = float(b[nuc_mask].mean())
        row["m_nuc_intensity_std"] = float(L[nuc_mask].std())
        
        row["m_cyto_mean_l"] = float(L[cyto_mask].mean()) if cyto_mask.any() else 0
        row["m_cyto_mean_a"] = float(a[cyto_mask].mean()) if cyto_mask.any() else 0
        row["m_cyto_mean_b"] = float(b[cyto_mask].mean()) if cyto_mask.any() else 0
        
        hsv = color.rgb2hsv(img_rgb)
        row["m_cyto_mean_hue"] = float(hsv[cyto_mask, 0].mean()) if cyto_mask.any() else 0
        
        # Texture (GLCM)
        gray = color.rgb2gray(img_rgb)
        gray_uint = (gray * 255).astype(np.uint8)
        minr, minc, maxr, maxc = nuc_props.bbox
        nuc_crop = gray_uint[minr:maxr, minc:maxc]
        mask_crop = nuc_mask[minr:maxr, minc:maxc]
        nuc_crop[~mask_crop] = 0
        
        try:
            glcm = feature.graycomatrix(nuc_crop, [2], [0, np.pi/4, np.pi/2, 3*np.pi/4], 256, symmetric=True, normed=True)
            row["m_nuc_glcm_contrast"] = float(feature.graycoprops(glcm, 'contrast').mean())
            row["m_nuc_glcm_homogeneity"] = float(feature.graycoprops(glcm, 'homogeneity').mean())
            row["m_nuc_glcm_energy"] = float(feature.graycoprops(glcm, 'energy').mean())
            row["m_nuc_glcm_correlation"] = float(feature.graycoprops(glcm, 'correlation').mean())
        except:
            row["m_nuc_glcm_contrast"] = 0.0
            row["m_nuc_glcm_homogeneity"] = 0.0
            row["m_nuc_glcm_energy"] = 0.0
            row["m_nuc_glcm_correlation"] = 0.0
            
        return row
    except Exception as e:
        row["m_seg_quality"] = "error"
        for col in M_COLUMNS:
            if col not in row: row[col] = 0.0
        return row

def wrapper(args):
    return process_image(*args)

def main():
    print(f"Reading {ATLAS_CSV} ...")
    atlas = pd.read_csv(ATLAS_CSV, low_memory=False)
    
    # Process all images that exist
    tasks = []
    for _, row in atlas.iterrows():
        img_id = row["image_id"]
        filename = row["filename"]
        path = IMAGES_DIR / filename
        if path.exists():
            tasks.append((path, img_id))
            
    total = len(tasks)
    print(f"Processing {total} images...")
    
    num_workers = multiprocessing.cpu_count()
    results = []
    
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        results = list(executor.map(wrapper, tasks))
        
    df = pd.DataFrame(results)
    df = df[M_COLUMNS] # ensure column order
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nDone! Saved to {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
