#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Occlusion-reasoning evaluation (final version)
Supports <points x y>object name</points> outputs.
Maps coordinates → object IDs via instance masks ('instances_objects'),
then computes SR / OR / MP-NED and detailed hit statistics.
"""

import json, re, os
import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
import editdistance

# ============================================================
# Regex template
# ============================================================

# Format in <answer>: <points x y>object name</points>
ANSWER_POINTS_RE = re.compile(
    r"<points\s+([\d\.]+)\s+([\d\.]+)>(.*?)</points>", re.IGNORECASE
)
ANSWER_TAG_RE = re.compile(r"<answer>(.*?)</answer>", re.IGNORECASE | re.DOTALL)

# Format in <think>: (x, y)
THINK_RE = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)
THINK_COORD_RE = re.compile(r"\(([\d\.]+),\s*([\d\.]+)\)", re.IGNORECASE)


# ============================================================
# Parsing Tools
# ============================================================
def extract_points_from_answer(text):
    """Extract <points x y>object name</points> from <answer> tag"""
    m = ANSWER_TAG_RE.search(text or "")
    if not m:
        return []
    pts = ANSWER_POINTS_RE.findall(m.group(1))
    # Here it is (x, y)
    return [(float(x), float(y), name.strip()) for x, y, name in pts]


def extract_scene_view_from_path(img_path):
    m = re.search(r"scene(\d+)_(\d+)\.png", img_path)
    if not m:
        return None, None
    return f"scene{m.group(1)}", m.group(2)


# def coords_to_object_ids(scene_id, view_id, coords_list, npz_root):
#     """Return object IDs and count hits / misses (no crop offset)."""
#     # synthetic format: data_ifl_0_scene0_view31.npy
#     npz_path = os.path.join(npz_root, f"scene{scene_id.replace('/', '_')}_view{view_id}.npy")

#     if not os.path.exists(npz_path):
#         print(f"[WARN] NPZ not found: {npz_path}")
#         return [0 for _ in coords_list], 0, len(coords_list)

#     mask = np.load(npz_path).astype(int)
#     H, W = mask.shape

#     ids, hits, misses = [], 0, 0
#     for (x, y, _) in coords_list:
#         x_int, y_int = int(round(x)), int(round(y))
#         if 0 <= x_int < W and 0 <= y_int < H:
#             obj_id = int(mask[y_int, x_int])
#         else:
#             obj_id = 0
#         if obj_id > 0:
#             hits += 1
#         else:
#             misses += 1
#         ids.append(obj_id)
#     return ids, hits, misses
# @@@@@@@@@@@@@@@
# def coords_to_object_ids(scene_id, view_id, coords_list, npz_root):
#     """Return object IDs and count hits / misses."""
#     npz_path = os.path.join(npz_root, f"scene{scene_id}_view{view_id}.npy")

#     if not os.path.exists(npz_path):
#         print(f"[WARN] NPZ not found: {npz_path}")
#         return [0 for _ in coords_list], 0, len(coords_list)

#     mask = np.load(npz_path).astype(int)
#     H, W = mask.shape

#     # ===== Crop offset compensation =====
#     CROP_W, CROP_H = 1200, 1200
#     ORI_W, ORI_H = 1944, 1200
#     offset_x = (ORI_W - CROP_W) / 2  # → 372
#     offset_y = (ORI_H - CROP_H) / 2  # → 0

#     ids, hits, misses = [], 0, 0
#     for (x, y, _) in coords_list:
#         # Translate coordinates from cropped image (1200x1200) to original image coordinate system
#         x_full = x + offset_x
#         y_full = y + offset_y


#         x_int, y_int = int(round(x_full)), int(round(y_full))
#         if 0 <= x_int < W and 0 <= y_int < H:
#             obj_id = int(mask[y_int, x_int])
#         else:
#             obj_id = 0
#         if obj_id > 0:
#             hits += 1
#         else:
#             misses += 1
#         ids.append(obj_id)
#     return ids, hits, misses
def coords_to_object_ids(scene_id, view_id, coords_list, npz_root):
    """Return object IDs and count hits / misses."""

    # ===== Automatically determine dataset type =====
    npz_root_lower = npz_root.lower()
    is_real = "real" in npz_root_lower

    npz_path = os.path.join(npz_root, f"scene{scene_id}_view{view_id}.npy")

    if not os.path.exists(npz_path):
        print(f"[WARN] NPZ not found: {npz_path}")
        return [0 for _ in coords_list], 0, len(coords_list)

    mask = np.load(npz_path).astype(int)
    H, W = mask.shape

    ids, hits, misses = [], 0, 0

    for x, y, _ in coords_list:

        # ===== Real dataset needs crop offset =====
        if is_real:
            CROP_W, CROP_H = 1200, 1200
            ORI_W, ORI_H = 1944, 1200
            offset_x = (ORI_W - CROP_W) / 2
            offset_y = (ORI_H - CROP_H) / 2

            x += offset_x
            y += offset_y

        x_int, y_int = int(round(x)), int(round(y))

        if 0 <= x_int < W and 0 <= y_int < H:
            obj_id = int(mask[y_int, x_int])
        else:
            obj_id = 0

        if obj_id > 0:
            hits += 1
        else:
            misses += 1

        ids.append(obj_id)

    return ids, hits, misses


def extract_answer_object_ids(model_output, scene_id, view_id, npz_root):
    coords = extract_points_from_answer(model_output)
    if not coords:
        return [], 0, 0
    ids, hits, misses = coords_to_object_ids(scene_id, view_id, coords, npz_root)
    return [i for i in ids if i > 0], hits, misses


def parse_think_paths_with_coords(model_output, scene_id, view_id, npz_root):
    """
    Extract 'A at (x, y) is occluded by B at (x, y)' structure from <think>,
    convert to object_id path list ordered by occlusion relationship (occluder -> occluded).
    Build paths using "concatenate + reverse" logic.
    """
    m = THINK_RE.search(model_output or "")
    if not m:
        return [], 0, 0
    think_text = m.group(1).strip()
    if not think_text:
        return [], 0, 0

    # parts = re.split(r"Path\d*:", think)
    # paths = []

    # Split into sentences (multiple paths)
    parts = re.split(r"Path\d*:", think_text)
    # parts = re.split(r"[.;\n]", think_text)
    all_paths = []
    total_hits = total_misses = 0

    for p in parts:
        p = p.strip()
        if not p:
            continue

        # Match relationship sentence: "A at (x, y) is occluded by B at (x, y)"
        rels = re.findall(
            r"(.+?)\s+at\s+\(([\d\.]+),\s*([\d\.]+)\)\s+is occluded by\s+(.+?)\s+at\s+\(([\d\.]+),\s*([\d\.]+)\)",
            p,
            re.IGNORECASE,
        )

        if rels:
            coords_list = []
            for child_name, x1, y1, parent_name, x2, y2 in rels:
                # child is occluded by parent
                coords_list.append((float(x1), float(y1), child_name.strip()))
                coords_list.append((float(x2), float(y2), parent_name.strip()))

            # Coordinate -> object_id mapping
            ids, hits, misses = coords_to_object_ids(
                scene_id, view_id, coords_list, npz_root
            )
            total_hits += hits
            total_misses += misses

            # === ✅ New logic: concatenate + reverse ===
            # ids format: [child1, parent1, child2, parent2, ...]
            # We want to get parent→child order chain
            if len(ids) >= 2:
                # Take the first child->parent pair
                tmp_list = [ids[0], ids[1]]
                # Append the parent of each subsequent relationship
                # tmp_list += [ids[i + 1] for i in range(2, len(ids) - 1, 2)]
                tmp_list += ids[3::2]
                tmp_list = [x for x in tmp_list if x is not None]
                tmp_list.reverse()  # Reverse direction: occluder -> occluded
                tmp_list = [int(x) for x in tmp_list if isinstance(x, (int, float))]
                #  if len(ids)>=4:
                #      if ids[1:-1:2]!=ids[2::2]:
                #          tmp_list=[]

                if tmp_list:
                    all_paths.append(
                        list(dict.fromkeys(tmp_list))
                    )  # Remove duplicates while preserving order

        else:
            # No occlusion relationship, but there might be single object coordinates
            m_single = re.search(r"at\s+\(([\d\.]+),\s*([\d\.]+)\)", p)
            if m_single:
                x, y = float(m_single.group(1)), float(m_single.group(2))
                ids, hits, misses = coords_to_object_ids(
                    scene_id, view_id, [(x, y, "")], npz_root
                )
                total_hits += hits
                total_misses += misses
                if ids and ids[0] > 0:
                    all_paths.append([ids[0]])

    return all_paths, total_hits, total_misses


# ============================================================
# Metric Functions
# ============================================================
def ned(seq1, seq2):

    return editdistance.eval(seq1, seq2) / max(len(seq1), len(seq2))


def mp_ned(pred_paths, gt_paths, alpha=1.0, beta=1.0):
    m, n = len(pred_paths), len(gt_paths)
    size = max(m, n)
    if size == 0:
        return 0.0
    C = np.zeros((size, size))
    for i in range(m):
        for j in range(n):
            C[i, j] = ned(pred_paths[i], gt_paths[j])
    if m < n:
        for i in range(m, size):
            C[i, :n] = alpha
    elif m > n:
        for j in range(n, size):
            C[:m, j] = beta
    row_ind, col_ind = linear_sum_assignment(C)
    return C[row_ind, col_ind].sum() / size


def paths_to_triplets(paths):
    triplets = set()
    for p in paths:
        for i in range(len(p) - 1):
            triplets.add((p[i], p[i + 1]))
    return triplets


def compute_prf(pred, gt):
    tp = len(gt & pred)
    fp = len(pred - gt)
    fn = len(gt - pred)
    p = tp / (tp + fp + 1e-8)
    r = tp / (tp + fn + 1e-8)
    f1 = 2 * p * r / (p + r + 1e-8)
    return p, r, f1


# ============================================================
# Main Evaluation Pipeline
# ============================================================
def evaluate(pred_path, gt_path, npz_root):
    preds = {}
    total_hits = total_misses = total_points = 0

    # ---------- Parse Predictions ----------
    with open(pred_path, "r", encoding="utf-8") as f:
        for line in f:
            it = json.loads(line)
            # scene_id, view_id = extract_scene_view_from_path(it["image"])
            scene_id, view_id = it.get("scene_id"), str(it.get("view_id"))
            if not scene_id:
                continue

            ans_ids, h1, m1 = extract_answer_object_ids(
                it["model_output"], scene_id, view_id, npz_root
            )
            think_paths, h2, m2 = parse_think_paths_with_coords(
                it["model_output"], scene_id, view_id, npz_root
            )
            total_hits += h1 + h2
            total_misses += m1 + m2
            total_points += h1 + h2 + m1 + m2
            tgt = it.get("target_object", -1)
            preds[(scene_id, view_id, tgt)] = {"answer": ans_ids, "paths": think_paths}

    # ---------- Load GT ----------
    gts = {}
    with open(gt_path, "r", encoding="utf-8") as f:
        arr = json.load(f)
        for it in arr:
            scene_id = it["scene_id"].split("/")[-1]
            view_id = str(it["view_id"])
            tgt = int(it["target_object"])
            paths = it.get("occlusion_paths", []) or [[tgt]]
            diff = (
                "No-Occ"
                if all(len(p) == 1 for p in paths)
                else it.get("new_difficulty", "Easy")
            )
            gts[(scene_id, view_id, tgt)] = {
                "paths": paths,
                "tops": [p[0] for p in paths],
                "difficulty": diff,
            }

    # ---------- Compute Metrics ----------
    res = defaultdict(
        lambda: {
            "SR-P": [],
            "SR-R": [],
            "SR-F1": [],
            "OP": [],
            "OR": [],
            "F1": [],
            "MP_NED": [],
        }
    )
    for key, gt in gts.items():
        if key not in preds:
            continue
        pred = preds[key]
        gt_top = set(gt["tops"])
        pred_ans = set(pred["answer"])
        p, r, f1 = compute_prf(pred_ans, gt_top)
        res[gt["difficulty"]]["SR-P"].append(p)
        res[gt["difficulty"]]["SR-R"].append(r)
        res[gt["difficulty"]]["SR-F1"].append(f1)

        gt_trip = paths_to_triplets(gt["paths"])
        pred_trip = paths_to_triplets(pred["paths"])
        op, orr, f1t = compute_prf(pred_trip, gt_trip)
        res[gt["difficulty"]]["OP"].append(op)
        res[gt["difficulty"]]["OR"].append(orr)
        res[gt["difficulty"]]["F1"].append(f1t)
        res[gt["difficulty"]]["MP_NED"].append(mp_ned(pred["paths"], gt["paths"]))
    return res


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":

    # # Real
    pred_file = "predictions.jsonl"
    gt_file = "test_GT.json"
    npz_root = "annotations"

    # Synthetic
    # pred_file = "/leonardo_work/IscrC_4grasp/UnoGrasp/outputs/nlp_syn/predictions.jsonl"
    # gt_file = "/leonardo_work/IscrC_4grasp/UnoBench/UnoBenchSyn/test_GT.json"
    # npz_root = "/leonardo_work/IscrC_4grasp/UnoBench/UnoBenchSyn/annotations"
    evaluate(pred_file, gt_file, npz_root)
