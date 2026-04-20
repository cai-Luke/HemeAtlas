"""
morphometry.py — Batch cell morphometry for HemeAtlas
Outputs morphometry.csv with m_ prefixed columns, ready to merge into atlas.csv.

Usage:
    python morphometry.py

Dependencies: scikit-image, numpy, pandas, Pillow
"""

import os
import sys
import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from skimage import color, filters, morphology, measure, feature
from skimage.morphology import disk, binary_opening, binary_closing, remove_small_objects
from skimage.measure import label, regionprops

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent
ATLAS_CSV = REPO_ROOT / "data" / "atlas.csv"
IMAGES_DIR = REPO_ROOT / "images"
OUTPUT_CSV = REPO_ROOT / "morphometry.csv"

# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

def segment_cell(img_rgb: np.ndarray):
    """
    Segment image into cell_mask, nucleus_mask, cytoplasm_mask.

    Returns:
        cell_mask      — bool array, True = cell (nucleus + cytoplasm)
        nucleus_mask   — bool array, True = nucleus
        cyto_mask      — bool array, True = cytoplasm
        quality        — str: 'good' | 'no_nucleus' | 'no_cytoplasm' | 'no_cell' | 'tiny_cell'
    """
    h, w = img_rgb.shape[:2]
    total_px = h * w

    lab = color.rgb2lab(img_rgb)
    L = lab[:, :, 0]   # 0–100
    a = lab[:, :, 1]   # negative=green, positive=red/magenta

    # --- Cell mask: background has high L* (white/light pink) ---
    try:
        thresh_L = filters.threshold_otsu(L)
    except Exception:
        thresh_L = 80.0
    cell_mask = L < thresh_L

    # Morphological cleanup
    cell_mask = binary_closing(cell_mask, disk(4))
    cell_mask = binary_opening(cell_mask, disk(2))
    from scipy.ndimage import binary_fill_holes
    cell_mask = binary_fill_holes(cell_mask)
    cell_mask = remove_small_objects(cell_mask, min_size=64)

    # --- NEW: OBJECT ISOLATION ---
    # Keep only the largest connected component (the actual cell)
    labeled_cell = label(cell_mask)
    props_cell = regionprops(labeled_cell)
    if props_cell:
        largest_cell = max(props_cell, key=lambda r: r.area)
        cell_mask = labeled_cell == largest_cell.label
    else:
        return cell_mask, np.zeros_like(cell_mask), np.zeros_like(cell_mask), "no_cell"

    # --- Nucleus mask: combined Color-Luminance Score ---
    # Nuclei are high a* (purple) and low L* (dark).
    # Combined score: a* - L* (shifts purple-dark pixels to very high values)
    score = a.copy() - L.copy()
    score_in_cell = score[cell_mask]
    
    if len(score_in_cell) > 0:
        try:
            # Otsu on the combined score
            thresh_score = filters.threshold_otsu(score_in_cell)
            
            # Sanity check: Ensure we don't pick a threshold that is too restrictive
            # Typical nuclear score is > -20 (e.g. a=20, L=40 -> 20-40 = -20)
            # If Otsu picks something very high, it's likely over-splitting a solid nucleus.
            thresh_score = min(thresh_score, -10.0) 
        except Exception:
            thresh_score = -20.0
    else:
        thresh_score = -20.0

    nucleus_mask = (score > thresh_score) & cell_mask

    # Morphological cleanup
    nucleus_mask = binary_opening(nucleus_mask, disk(2))
    nucleus_mask = binary_closing(nucleus_mask, disk(3))
    nucleus_mask = binary_fill_holes(nucleus_mask)
    nucleus_mask = remove_small_objects(nucleus_mask, min_size=32)

    # --- Cytoplasm ---
    cyto_mask = cell_mask & ~nucleus_mask

    # --- Quality flags ---
    cell_area = cell_mask.sum()
    nuc_area = nucleus_mask.sum()
    cyto_area = cyto_mask.sum()

    if cell_area == 0:
        return cell_mask, nucleus_mask, cyto_mask, "no_cell"

    if cell_area < 0.05 * total_px:
        quality = "tiny_cell"
    elif nuc_area == 0:
        quality = "no_nucleus"
    elif cyto_area == 0:
        quality = "no_cytoplasm"
    else:
        quality = "good"

    return cell_mask, nucleus_mask, cyto_mask, quality


# ---------------------------------------------------------------------------
# Morphometry
# ---------------------------------------------------------------------------

def _largest_region(mask: np.ndarray):
    """Return regionprops of the largest connected component in mask, or None."""
    labeled = label(mask)
    props = regionprops(labeled)
    if not props:
        return None
    return max(props, key=lambda r: r.area)


def _circularity(area, perimeter):
    if perimeter == 0:
        return np.nan
    return (4 * math.pi * area) / (perimeter ** 2)


def compute_morphometry(img_rgb: np.ndarray, cell_mask, nuc_mask, cyto_mask) -> dict:
    """Compute all m_ morphometry columns. Returns dict of values."""
    row = {}

    lab = color.rgb2lab(img_rgb)
    gray = color.rgb2gray(img_rgb)

    # -----------------------------------------------------------------------
    # Cell geometry
    # -----------------------------------------------------------------------
    cell_props = _largest_region(cell_mask)
    if cell_props is not None:
        cp = cell_props
        # Use sum of mask for area to be consistent with N:C ratio
        row["m_cell_area"] = float(cell_mask.sum())
        row["m_cell_major"] = cp.major_axis_length
        row["m_cell_minor"] = cp.minor_axis_length
        row["m_cell_eccentricity"] = cp.eccentricity
        row["m_cell_circularity"] = _circularity(float(cell_mask.sum()), cp.perimeter)
        row["m_cell_solidity"] = cp.solidity
        row["m_cell_equiv_diameter"] = cp.equivalent_diameter_area
        row["m_cell_aspect_ratio"] = (
            cp.major_axis_length / cp.minor_axis_length
            if cp.minor_axis_length > 0 else np.nan
        )
        row["m_cell_extent"] = cp.extent
    else:
        for k in ["m_cell_area", "m_cell_major", "m_cell_minor", "m_cell_eccentricity",
                  "m_cell_circularity", "m_cell_solidity", "m_cell_equiv_diameter",
                  "m_cell_aspect_ratio", "m_cell_extent"]:
            row[k] = np.nan

    # -----------------------------------------------------------------------
    # Nucleus geometry — largest component
    # -----------------------------------------------------------------------
    nuc_props = _largest_region(nuc_mask)
    if nuc_props is not None:
        np_ = nuc_props
        # Use sum of mask for area (vital for multi-lobed neutrophils)
        row["m_nuc_area"] = float(nuc_mask.sum())
        row["m_nuc_major"] = np_.major_axis_length
        row["m_nuc_minor"] = np_.minor_axis_length
        row["m_nuc_eccentricity"] = np_.eccentricity
        row["m_nuc_circularity"] = _circularity(float(nuc_mask.sum()), np_.perimeter)
        row["m_nuc_solidity"] = np_.solidity
        # Convex deficiency from full nucleus mask (all components)
        from skimage.morphology import convex_hull_image
        try:
            hull = convex_hull_image(nuc_mask)
            hull_area = hull.sum()
        except Exception:
            hull_area = np_.convex_image.sum() if np_.convex_image is not None else np_.area
        row["m_nuc_convex_deficiency"] = float(hull_area) - float(nuc_mask.sum())
    else:
        for k in ["m_nuc_area", "m_nuc_major", "m_nuc_minor", "m_nuc_eccentricity",
                  "m_nuc_circularity", "m_nuc_solidity", "m_nuc_convex_deficiency"]:
            row[k] = np.nan

    # Lobe count: Distance Transform + Peak Detection
    # Aggressive smoothing and distance constraints to count biological lobes.
    try:
        from scipy import ndimage as ndi
        from skimage.feature import peak_local_max
        
        # 1. Fill holes and apply strong Gaussian smoothing to the mask
        # This removes internal texture/fragmentation and smooths the boundary.
        nuc_clean = ndi.binary_fill_holes(nuc_mask)
        smoothed = ndi.gaussian_filter(nuc_clean.astype(float), sigma=5.0)
        nuc_clean = smoothed > 0.5
        
        # 2. Distance transform
        distance = ndi.distance_transform_edt(nuc_clean)
        
        # 3. Find peaks: centers of lobes
        # min_distance=45 is tuned for ~350x350 images to separate lobes while ignoring bumps.
        peaks = peak_local_max(distance, min_distance=45, threshold_rel=0.2, labels=nuc_clean)
        
        row["m_nuc_lobes"] = float(len(peaks)) if len(peaks) > 0 else (1.0 if nuc_mask.any() else 0.0)
    except Exception:
        row["m_nuc_lobes"] = np.nan

    # -----------------------------------------------------------------------
    # N:C ratio
    # -----------------------------------------------------------------------
    nuc_area = nuc_mask.sum()
    cell_area = cell_mask.sum()
    row["m_nc_ratio"] = float(nuc_area) / float(cell_area) if cell_area > 0 else np.nan

    # -----------------------------------------------------------------------
    # Color / Intensity — nucleus
    # -----------------------------------------------------------------------
    if nuc_area > 0:
        row["m_nuc_mean_l"] = float(lab[:, :, 0][nuc_mask].mean())
        row["m_nuc_mean_a"] = float(lab[:, :, 1][nuc_mask].mean())
        row["m_nuc_mean_b"] = float(lab[:, :, 2][nuc_mask].mean())
        row["m_nuc_intensity_std"] = float(gray[nuc_mask].std())
    else:
        row["m_nuc_mean_l"] = np.nan
        row["m_nuc_mean_a"] = np.nan
        row["m_nuc_mean_b"] = np.nan
        row["m_nuc_intensity_std"] = np.nan

    # Color / Intensity — cytoplasm
    cyto_area = cyto_mask.sum()
    if cyto_area > 0:
        row["m_cyto_mean_l"] = float(lab[:, :, 0][cyto_mask].mean())
        row["m_cyto_mean_a"] = float(lab[:, :, 1][cyto_mask].mean())
        row["m_cyto_mean_b"] = float(lab[:, :, 2][cyto_mask].mean())

        # Mean hue in HSV
        hsv = color.rgb2hsv(img_rgb)
        row["m_cyto_mean_hue"] = float(hsv[:, :, 0][cyto_mask].mean())
    else:
        row["m_cyto_mean_l"] = np.nan
        row["m_cyto_mean_a"] = np.nan
        row["m_cyto_mean_b"] = np.nan
        row["m_cyto_mean_hue"] = np.nan

    # -----------------------------------------------------------------------
    # GLCM texture — nucleus region
    # -----------------------------------------------------------------------
    if nuc_area >= 4:
        try:
            # Extract bounding box of nucleus mask, quantize to 64 levels
            rows_idx, cols_idx = np.where(nuc_mask)
            r0, r1 = rows_idx.min(), rows_idx.max() + 1
            c0, c1 = cols_idx.min(), cols_idx.max() + 1
            gray_patch = gray[r0:r1, c0:c1]
            mask_patch = nuc_mask[r0:r1, c0:c1]

            # Zero out non-nucleus pixels so they don't contribute
            gray_patch = gray_patch.copy()
            gray_patch[~mask_patch] = 0.0

            # Quantize to 0–63
            gray_int = (gray_patch * 63).astype(np.uint8)

            glcm = feature.graycomatrix(
                gray_int, distances=[1], angles=[0],
                levels=64, symmetric=True, normed=True
            )
            row["m_nuc_glcm_contrast"] = float(feature.graycoprops(glcm, "contrast")[0, 0])
            row["m_nuc_glcm_homogeneity"] = float(feature.graycoprops(glcm, "homogeneity")[0, 0])
            row["m_nuc_glcm_energy"] = float(feature.graycoprops(glcm, "energy")[0, 0])
            row["m_nuc_glcm_correlation"] = float(feature.graycoprops(glcm, "correlation")[0, 0])
        except Exception:
            row["m_nuc_glcm_contrast"] = np.nan
            row["m_nuc_glcm_homogeneity"] = np.nan
            row["m_nuc_glcm_energy"] = np.nan
            row["m_nuc_glcm_correlation"] = np.nan
    else:
        row["m_nuc_glcm_contrast"] = np.nan
        row["m_nuc_glcm_homogeneity"] = np.nan
        row["m_nuc_glcm_energy"] = np.nan
        row["m_nuc_glcm_correlation"] = np.nan

    return row


# ---------------------------------------------------------------------------
# Per-image processing
# ---------------------------------------------------------------------------

def process_image(image_path: Path, image_id: str) -> dict:
    """Load image, segment, compute morphometry. Returns a row dict."""
    base = {"image_id": image_id}

    try:
        pil_img = Image.open(image_path).convert("RGB")
        img_rgb = np.array(pil_img, dtype=np.float64) / 255.0
    except Exception as e:
        base["m_seg_quality"] = "error"
        return base

    try:
        cell_mask, nuc_mask, cyto_mask, quality = segment_cell(img_rgb)
    except Exception as e:
        base["m_seg_quality"] = "error"
        return base

    base["m_seg_quality"] = quality

    try:
        morph = compute_morphometry(img_rgb, cell_mask, nuc_mask, cyto_mask)
        base.update(morph)
    except Exception as e:
        # Quality flag already set; morphometry failed — leave columns absent (will be NaN)
        pass

    return base


# ---------------------------------------------------------------------------
# Column order
# ---------------------------------------------------------------------------

M_COLUMNS = [
    "image_id",
    "m_cell_area", "m_cell_major", "m_cell_minor", "m_cell_eccentricity",
    "m_cell_circularity", "m_cell_solidity", "m_cell_equiv_diameter",
    "m_cell_aspect_ratio", "m_cell_extent",
    "m_nuc_area", "m_nuc_major", "m_nuc_minor", "m_nuc_eccentricity",
    "m_nuc_circularity", "m_nuc_solidity", "m_nuc_lobes", "m_nuc_convex_deficiency",
    "m_nc_ratio",
    "m_nuc_mean_l", "m_nuc_mean_a", "m_nuc_mean_b", "m_nuc_intensity_std",
    "m_cyto_mean_l", "m_cyto_mean_a", "m_cyto_mean_b", "m_cyto_mean_hue",
    "m_nuc_glcm_contrast", "m_nuc_glcm_homogeneity",
    "m_nuc_glcm_energy", "m_nuc_glcm_correlation",
    "m_seg_quality",
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Reading {ATLAS_CSV} ...")
    atlas = pd.read_csv(ATLAS_CSV, dtype=str)

    # Only finalized records
    finalized = atlas[atlas["path_status"] == "finalized"][["image_id", "filename"]].copy()
    finalized = finalized.dropna(subset=["image_id", "filename"])
    total = len(finalized)
    print(f"Found {total} finalized records to process.")
    print(f"Output → {OUTPUT_CSV}\n")

    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing
    num_workers = multiprocessing.cpu_count()
    print(f"Using {num_workers} workers...")

    results = []
    quality_counts = {}
    error_ids = []

    # Prepare tasks
    tasks = []
    for _, row in finalized.iterrows():
        tasks.append((IMAGES_DIR / row["filename"], row["image_id"]))

    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        futures = [executor.submit(process_image, path, eid) for path, eid in tasks]
        
        for i, future in enumerate(futures, 1):
            try:
                result = future.result()
                results.append(result)
                
                q = result.get("m_seg_quality", "error")
                quality_counts[q] = quality_counts.get(q, 0) + 1
                if q == "error":
                    error_ids.append(result.get("image_id", "unknown"))

                if i % 100 == 0 or i == total:
                    print(f"[{i}/{total}] Completed — {q}")
            except Exception as e:
                print(f"Worker error: {e}")

    # Build DataFrame with consistent column order
    df = pd.DataFrame(results)
    for col in M_COLUMNS:
        if col not in df.columns:
            df[col] = np.nan
    df = df[M_COLUMNS]

    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\n{'='*60}")
    print(f"Done. {total} images processed → {OUTPUT_CSV}")
    print(f"\nQuality flag summary:")
    for flag, count in sorted(quality_counts.items()):
        print(f"  {flag:20s} {count:6d}")
    if error_ids:
        print(f"\nErrors ({len(error_ids)}):")
        for eid in error_ids[:20]:
            print(f"  {eid}")
        if len(error_ids) > 20:
            print(f"  ... and {len(error_ids) - 20} more")
    print("="*60)


if __name__ == "__main__":
    main()
