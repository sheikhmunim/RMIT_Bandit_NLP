#!/usr/bin/env python3

# -*- coding: utf-8 -*-


# import rospy
# from std_msgs.msg import String
# import torch
# from transformers import BertTokenizer, BertForSequenceClassification
# import os
# import rospkg
# from symbolic_executor import execute_symbolic, init_executor

# LABELS = ["GO_KITCHEN", "GO_LIVING_ROOM", "GO_TABLE", "GO_SLOW", "GO_FAST", "STOP",
#           "WAVE_LEFT", "WAVE_RIGHT", "CORRECTION", "SEQUENCE", "CONCURRENT"]

# def load_model():
#     rospack = rospkg.RosPack()
#     model_dir = os.path.join(rospack.get_path('nlp'), 'bert_grounded_model')
#     tokenizer = BertTokenizer.from_pretrained(model_dir)
#     model = BertForSequenceClassification.from_pretrained(model_dir)
#     model.eval()
#     return tokenizer, model

# def predict_command(tokenizer, model, text):
#     inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
#     with torch.no_grad():
#         outputs = model(**inputs)
#         logits = outputs.logits
#         probs = torch.sigmoid(logits)[0]

#     threshold = 0.3
#     predicted = [LABELS[i] for i, p in enumerate(probs) if p > threshold]
#     return predicted

# def main():
#     rospy.init_node('bert_grounding_node')
#     tokenizer, model = load_model()
#     init_executor()

#     rospy.loginfo("BERT grounding node ready. Type natural language commands:")

#     while not rospy.is_shutdown():
#         try:
#             text = input(">>> ")
#             labels = predict_command(tokenizer, model, text)
#             rospy.loginfo(f"Predicted Labels: {labels}")
#             execute_symbolic(labels)
#         except (KeyboardInterrupt, EOFError):
#             print("\nExiting...")
#             break

# if __name__ == "__main__":
#     main()






# #!/usr/bin/env python3
# import rospy
# from std_msgs.msg import String

# import torch
# import os
# import pickle
# import numpy as np

# from transformers import BertTokenizer
# from multi_head_model import MultiHeadBERT  # make sure this is implemented
# from sklearn.preprocessing import LabelEncoder, MultiLabelBinarizer

# from symbolic_executor import execute_symbolic, init_executor

# # Fallback vocab values
# INTENTS_FALLBACK = []
# REGIONS_FALLBACK = []
# SPEEDS_FALLBACK = []
# HANDS_FALLBACK = []
# ORDERING_FALLBACK = []
# DIRECTIONS_FALLBACK = []

# MAX_LENGTH = 32

# def load_model():
#     model_dir = "/Bandit_in_person_tutorial/bandit_nlp/src/nlp/bert_grounded_model" # ✅ Update this!

#     # Load tokenizer and model
#     tokenizer = BertTokenizer.from_pretrained(model_dir)
#     model = MultiHeadBERT.from_pretrained(model_dir)
#     device = "cuda" if torch.cuda.is_available() else "cpu"
#     model.to(device)
#     model.eval()

#     # Load cleaned encoders
#     with open(os.path.join(model_dir, "encoders.pkl"), "rb") as f:
#         enc_clean = pickle.load(f)

#     encoders = {}
#     for k, class_list in enc_clean.items():
#         le = LabelEncoder()
#         le.classes_ = np.array(class_list)
#         encoders[k] = le

#     # Load MultiLabelBinarizer for intent
#     with open(os.path.join(model_dir, "mlb_intent.pkl"), "rb") as f:
#         mlb_classes = pickle.load(f)
#         mlb_intent = MultiLabelBinarizer()
#         mlb_intent.fit(mlb_classes)

#     # Expose vocab from model class if defined
#     intents    = getattr(model, "intents",    INTENTS_FALLBACK)
#     regions    = getattr(model, "regions",    REGIONS_FALLBACK)
#     speeds     = getattr(model, "speeds",     SPEEDS_FALLBACK)
#     hands      = getattr(model, "hands",      HANDS_FALLBACK)
#     ordering   = getattr(model, "ordering",   ORDERING_FALLBACK)
#     directions = getattr(model, "directions", DIRECTIONS_FALLBACK)

#     rospy.loginfo(f"[grounding] Model loaded from: {model_dir} (device={device})")
#     return tokenizer, model, device, encoders, mlb_intent, intents, regions, speeds, hands, ordering, directions

# def predict_command(text, tokenizer, model, device, encoders, mlb_intent):
#     enc = tokenizer(text, return_tensors="pt", padding="max_length",
#                     truncation=True, max_length=MAX_LENGTH)

#     enc = {k: v.to(device) for k, v in enc.items() if k != "token_type_ids"}

#     with torch.no_grad():
#         out = model(**enc)

#     # Decode predictions
#     pred = {}
#     for head, logits in out.items():
#         if head == "correction":
#             pred[head] = torch.sigmoid(logits).item()
#         elif head == "intent":
#             idx = torch.argmax(logits, dim=1).item()
#             pred[head] = encoders["intent"].inverse_transform([idx])[0]
#         else:
#             idx = torch.argmax(logits, dim=1).item()
#             pred[head] = encoders[head].inverse_transform([idx])[0]
#     return pred

# def handle_input(msg, pub, tokenizer, model, device, encoders, mlb_intent):
#     command = msg.data.strip()
#     rospy.loginfo(f">>> {command}")
#     try:
#         labels = predict_command(command, tokenizer, model, device, encoders, mlb_intent)
#         rospy.loginfo(f"Predicted Labels: {labels}")
#         pub.publish(str(labels))
#     except Exception as e:
#         rospy.logwarn(f"[grounding] Exception: {e}")





# def main():
#     tokenizer, model, device, encoders, mlb_intent, *_ = load_model()
#     rospy.loginfo("✅ BERT grounding node ready. Type natural language commands.")

#     while True:
#         try:
#             command = input(">>> ")
#             if command.strip() == "":
#                 continue

#             outputs = predict_command(command, tokenizer, model, device, encoders, mlb_intent)

#             rospy.loginfo(f"🧠 Predicted labels:\n{outputs}")

#         except KeyboardInterrupt:
#             rospy.loginfo("🛑 Interrupted. Exiting...")
#             break
#         except Exception as e:
#             rospy.logerr(f"🔥 Error during prediction: {e}")

# if __name__ == "__main__":
#     main()







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

# ========= CONFIG =========
# MODEL_DIR = "/Bandit_in_person_tutorial/bandit_nlp/src/nlp/bert_grounded_model"



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

# Map slots -> executor labels
EXEC_LABELS = {
    "kitchen": "GO_KITCHEN",
    "living_room": "GO_LIVING_ROOM",
    "table": "GO_TABLE",
    "slow": "GO_SLOW",
    "fast": "GO_FAST",
    "stop": "STOP",
    "left": "WAVE_LEFT",
    "right": "WAVE_RIGHT",
    "sequential": "SEQUENCE",
    "concurrent": "CONCURRENT",
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
    tokenizer = BertTokenizer.from_pretrained(MODEL_DIR)  # loads your saved tokenizer config
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
    idx = torch.argmax(logits_row, dim=-1).item()
    return names[idx] if 0 <= idx < len(names) else names[0]

def predict_command(text, tokenizer, model, device, C):
    # Encode EXACTLY like training
    enc = tokenizer(
        text,
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=MAX_LENGTH,
    )

    # Build inputs explicitly; pass token_type_ids if your model forward accepts it
    inputs = {
        "input_ids": enc["input_ids"].to(device),
        "attention_mask": enc["attention_mask"].to(device),
    }
    if "token_type_ids" in enc:
        try:
            # Your MultiHeadBERT.forward should accept token_type_ids=None safely
            inputs["token_type_ids"] = enc["token_type_ids"].to(device)
        except TypeError:
            pass

    with torch.inference_mode():
        out = model(**inputs)

    # Optional: debug top-k to confirm mapping
    if DEBUG_TOPK:
        rospy.loginfo(f"intent top{TOPK}:   {_topk(out['intent'],   C['intent'],   TOPK)}")
        rospy.loginfo(f"region top{TOPK}:   {_topk(out['region'],   C['region'],   TOPK)}")
        rospy.loginfo(f"speed top{TOPK}:    {_topk(out['speed'],    C['speed'],    TOPK)}")
        rospy.loginfo(f"hand top{TOPK}:     {_topk(out['hand'],     C['hand'],     TOPK)}")
        rospy.loginfo(f"ordering top{TOPK}: {_topk(out['ordering'], C['ordering'], TOPK)}")
        # rospy.loginfo(f"direction top{TOPK}:{_topk(out['direction'],C['direction'],TOPK)}")

    # Decode each head via argmax over logits (multiclass)
    intent    = inverse_map(out["intent"],    C["intent"])
    region    = inverse_map(out["region"],    C["region"])
    speed     = inverse_map(out["speed"],     C["speed"])
    hand      = inverse_map(out["hand"],      C["hand"])
    ordering  = inverse_map(out["ordering"],  C["ordering"])
    # direction = inverse_map(out["direction"], C["direction"])  # not mapped yet

    # Correction is a raw logit in your model → sigmoid then threshold
    correction_score = torch.sigmoid(out["correction"]).squeeze().item()
    is_correction = correction_score >= CORRECTION_THR

    # Build flat executor labels
    labels = []
    if intent == "move":
        if region in ("kitchen", "living_room", "table"):
            labels.append(EXEC_LABELS[region])
        elif region in ("bedroom", "hallway"):
            rospy.logwarn(f"[grounding] Region '{region}' has no executor label; ignoring.")
        if speed in ("slow", "fast"):
            labels.append(EXEC_LABELS[speed])

    elif intent == "stop":
        labels.append(EXEC_LABELS["stop"])

    elif intent == "wave":
        if hand in ("left", "right"):
            labels.append(EXEC_LABELS[hand])
        else:
            rospy.logwarn(f"[grounding] 'wave' predicted but hand='{hand}'; no wave-side label emitted.")

    if ordering in ("sequential", "concurrent"):
        labels.append(EXEC_LABELS[ordering])
    elif ordering in ("contradiction", "ambiguous", "unknown"):
        rospy.logwarn(f"[grounding] ordering='{ordering}' not mapped; ignoring.")

    if is_correction:
        labels.append("CORRECTION")

    rospy.loginfo(
        f"[grounding] intent={intent}, region={region}, speed={speed}, hand={hand}, "
        f"ordering={ordering}, correction={correction_score:.3f} -> {labels}"
    )
    return labels

def main():
    rospy.init_node("bert_grounding_node")
    init_executor()

    tokenizer, model, device, C = load_model()
    rospy.loginfo("✅ BERT grounding node ready. Type natural language commands.")

    while not rospy.is_shutdown():
        try:
            cmd = input(">>> ").strip()
            if not cmd:
                continue
            labels = predict_command(cmd, tokenizer, model, device, C)
            rospy.loginfo(f"Predicted Labels: {labels}")
            execute_symbolic(labels)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break
        except Exception as e:
            rospy.logerr(f"🔥 Error during prediction: {e}", exc_info=True)

if __name__ == "__main__":
    # ensure local imports work if run directly
    sys.path.insert(0, os.getcwd())
    main()
