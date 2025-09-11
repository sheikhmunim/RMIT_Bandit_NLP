#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import pickle
import torch
import rospy
import rospkg

from transformers import BertTokenizer
from multi_head_model import MultiHeadBERT
from symbolic_executor import execute_symbolic, init_executor
from grounding_planner import GroundingPlanner

# ========= CONFIG =========
rospack = rospkg.RosPack()
MODEL_DIR = os.path.join(rospack.get_path('nlp'), 'bert_grounded_model')

MAX_LENGTH = 32
DEBUG_TOPK = False   # set False to silence per-head top-k logs
TOPK = 3
CORRECTION_THR = 0.5
# =========================

# Safe defaults (only used if neither labels.json nor encoders.pkl exist)
DEFAULT_CLASSES = {
    "intent":    ["move", "wave", "stop"],
    "region":    ["kitchen", "living_room", "table", "bedroom", "hallway", "none", "unknown"],
    "speed":     ["slow", "fast", "none", "normal", "unknown"],
    "hand":      ["left", "right", "none", "unknown"],
    "ordering":  ["sequential", "concurrent", "contradiction", "ambiguous", "unknown"],
    "direction": ["forward", "backward", "left", "right", "turn_left", "turn_right", "none", "unknown"],
}

def _load_class_lists(model_dir):
    """
    Load class lists in this priority:
      1) labels.json  (best; written in Colab alongside weights)
      2) encoders.pkl (clean lists only; not sklearn objects)
      3) DEFAULT_CLASSES fallback
    """
    # 1) labels.json
    labels_fp = os.path.join(model_dir, "labels.json")
    if os.path.isfile(labels_fp):
        try:
            with open(labels_fp, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            C = {
                "intent":    cfg.get("INTENTS",    DEFAULT_CLASSES["intent"]),
                "region":    cfg.get("REGIONS",    DEFAULT_CLASSES["region"]),
                "speed":     cfg.get("SPEEDS",     DEFAULT_CLASSES["speed"]),
                "hand":      cfg.get("HANDS",      DEFAULT_CLASSES["hand"]),
                "ordering":  cfg.get("ORDERING",   DEFAULT_CLASSES["ordering"]),
                "direction": cfg.get("DIRECTIONS", DEFAULT_CLASSES["direction"]),
            }
            rospy.loginfo("[grounding] Loaded class lists from labels.json")
            return C
        except Exception as e:
            rospy.logwarn(f"[grounding] Failed to read labels.json ({e}); trying encoders.pkl...")

    # 2) encoders.pkl (must contain plain python lists)
    enc_fp = os.path.join(model_dir, "encoders.pkl")
    if os.path.isfile(enc_fp):
        try:
            with open(enc_fp, "rb") as f:
                enc = pickle.load(f)  # expected dict[str, list[str]]
            C = DEFAULT_CLASSES.copy()
            if isinstance(enc, dict):
                for k in ("intent", "region", "speed", "hand", "ordering", "direction"):
                    if k in enc and isinstance(enc[k], (list, tuple)) and len(enc[k]) > 0:
                        C[k] = list(enc[k])
            rospy.loginfo("[grounding] Loaded class lists from encoders.pkl")
            return C
        except Exception as e:
            rospy.logwarn(f"[grounding] Failed to read encoders.pkl ({e}); using defaults.")

    # 3) defaults
    return DEFAULT_CLASSES.copy()

def _sanity_check_shapes(model, C):
    """Ensure each head out_features equals the length of its class list."""
    problems = []
    try:
        if model.intent_head.out_features != len(C["intent"]):
            problems.append(("intent", model.intent_head.out_features, len(C["intent"])))
        if model.region_head.out_features != len(C["region"]):
            problems.append(("region", model.region_head.out_features, len(C["region"])))
        if model.speed_head.out_features != len(C["speed"]):
            problems.append(("speed", model.speed_head.out_features, len(C["speed"])))
        if model.hand_head.out_features != len(C["hand"]):
            problems.append(("hand", model.hand_head.out_features, len(C["hand"])))
        if model.ordering_head.out_features != len(C["ordering"]):
            problems.append(("ordering", model.ordering_head.out_features, len(C["ordering"])))
        if model.direction_head.out_features != len(C["direction"]):
            problems.append(("direction", model.direction_head.out_features, len(C["direction"])))
    except Exception as e:
        rospy.logwarn(f"[grounding] Shape sanity check skipped: {e}")
        return True

    if problems:
        for name, of, ln in problems:
            rospy.logerr(f"[grounding] SHAPE MISMATCH for {name}: head={of} vs classes={ln}")
        rospy.logerr("[grounding] Fix your class lists (labels.json/encoders.pkl) to match training.")
        return False
    return True

def _topk(logits, names, k=3):
    probs = torch.softmax(logits, dim=-1).squeeze(0)
    k = min(k, probs.numel())
    vals, idxs = torch.topk(probs, k=k)
    return [(names[i], float(v)) for i, v in zip(idxs.tolist(), vals.tolist())]

def load_model():
    # Tokenizer/Model
    tokenizer = BertTokenizer.from_pretrained(MODEL_DIR)  # loads saved tokenizer config
    model = MultiHeadBERT.from_pretrained(MODEL_DIR)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    try:
        model.to(device)
    except RuntimeError:
        rospy.logwarn("[grounding] CUDA move failed; using CPU.")
        device = "cpu"
        model.to(device)
    model.eval()

    # Class lists
    C = _load_class_lists(MODEL_DIR)
    if not _sanity_check_shapes(model, C):
        raise RuntimeError("Class lists do not match model head sizes. See errors above.")

    rospy.loginfo(f"[grounding] Model loaded from: {MODEL_DIR} (device={device})")
    return tokenizer, model, device, C

def inverse_map(logits_row, names):
    """Argmax → class name, safe fallback to index 0 if out of range."""
    idx = torch.argmax(logits_row, dim=-1).item()
    return names[idx] if 0 <= idx < len(names) else names[0]

def predict_command(text, tokenizer, model, device, C, verbose=True):
    """Return RAW SLOTS dict for a single input string (full text or chunk)."""
    enc = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
    )

    inputs = {
        "input_ids": enc["input_ids"].to(device),
        "attention_mask": enc["attention_mask"].to(device),
    }
    if "token_type_ids" in enc:
        try:
            inputs["token_type_ids"] = enc["token_type_ids"].to(device)
        except TypeError:
            pass

    with torch.inference_mode():
        out = model(**inputs)

    if DEBUG_TOPK:
        rospy.loginfo(f"intent top{TOPK}:   {_topk(out['intent'],   C['intent'],   TOPK)}")
        rospy.loginfo(f"region top{TOPK}:   {_topk(out['region'],   C['region'],   TOPK)}")
        rospy.loginfo(f"speed top{TOPK}:    {_topk(out['speed'],    C['speed'],    TOPK)}")
        rospy.loginfo(f"hand top{TOPK}:     {_topk(out['hand'],     C['hand'],     TOPK)}")
        rospy.loginfo(f"ordering top{TOPK}: {_topk(out['ordering'], C['ordering'], TOPK)}")
        rospy.loginfo(f"direction top{TOPK}:{_topk(out['direction'],C['direction'],TOPK)}")

    intent    = inverse_map(out["intent"],    C["intent"])
    region    = inverse_map(out["region"],    C["region"])
    speed     = inverse_map(out["speed"],     C["speed"])
    hand      = inverse_map(out["hand"],      C["hand"])
    ordering  = inverse_map(out["ordering"],  C["ordering"])
    direction = inverse_map(out["direction"], C["direction"])

    correction_score = torch.sigmoid(out["correction"]).squeeze().item()
    is_correction = correction_score >= CORRECTION_THR

    slots = {
        "intent": intent,
        "region": region,
        "speed": speed,
        "hand": hand,
        "ordering": ordering,
        "direction": direction,
        "correction": bool(is_correction),
        "correction_score": float(correction_score),
    }
    if verbose:

        rospy.loginfo(
            "[grounding] slots intent=%s, region=%s, speed=%s, hand=%s, ordering=%s, direction=%s, correction=%.3f",
            slots["intent"], slots["region"], slots["speed"], slots["hand"], slots["ordering"],
            slots["direction"], slots["correction_score"]
        )
    return slots

# ---------------------------
# MAIN NODE WITH PLANNER
# ---------------------------
def main():
    rospy.init_node("bert_grounding_node")
    init_executor()

    tokenizer, model, device, C = load_model()
    rospy.loginfo("BERT grounding node ready. Type natural language commands.")

    # ---- wrappers used by GroundingPlanner ----
    def predict_fn_chunk(chunk_text: str) -> dict:
        # per-chunk classification using the same model
        return predict_command(chunk_text, tokenizer, model, device, C, verbose=False)

    def order_predict_fn_full(full_text: str) -> dict:
        # full-text; we'll read 'ordering' from this result
        return predict_command(full_text, tokenizer, model, device, C, verbose=False)

    planner = GroundingPlanner(
        predict_fn=predict_fn_chunk,
        order_predict_fn=order_predict_fn_full,  # uses the ordering head on full text
        normalize_lr_to_turn=True,
        map_unknown_speed_to="normal",
        map_unknown_direction_to="forward",
        fallback_ordering="sequential",
    )

    while not rospy.is_shutdown():
        try:
            cmd = input(">>> ").strip()
            if not cmd:
                continue

            # Split → classify per chunk → get ordering from full text
            plan = planner.predict_steps(cmd)

            rospy.loginfo("[grounding] ordering=%s, num_steps=%d, chunks=%s",
                          plan["ordering"], plan["num_steps"], plan["chunks"])
            rospy.loginfo("[grounding] steps=%s", json.dumps(plan["steps"], ensure_ascii=False))

            # Execute each step sequentially; convert list-fields to flat slots
            for i, step in enumerate(plan["steps"], 1):
                slots = {
                    "intent":    step["intent"][0],
                    "region":    step["region"][0],
                    "speed":     step["speed"][0],
                    "hand":      step["hand"][0],
                    "ordering":  plan["ordering"],      # model-derived ordering on full command
                    "direction": step["direction"][0],
                    "correction": False,                 # simple; wire per-chunk if needed
                    "correction_score": 0.0
                }
                rospy.loginfo("[grounding] Executing step %d/%d: %s", i, plan["num_steps"], slots)
                execute_symbolic(slots)

        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as e:
            rospy.logerr(f"Error during prediction: {e}", exc_info=True)

if __name__ == "__main__":
    # ensure local imports work if run directly
    sys.path.insert(0, os.getcwd())
    main()
