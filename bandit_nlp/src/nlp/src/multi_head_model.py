# multi_head_model.py
# -*- coding: utf-8 -*-

import os
import torch
import torch.nn as nn
from transformers import BertModel

# IMPORTANT:
# These lists MUST match the exact order/size used during training.
INTENTS    = ["move", "wave", "stop"]
REGIONS    = ["kitchen", "living_room", "table", "bedroom", "hallway", "none", "unknown"]
SPEEDS     = ["slow", "fast", "none", "normal", "unknown"]
HANDS      = ["left", "right", "none", "unknown"]
ORDERING   = ["sequential", "concurrent", "contradiction", "ambiguous", "unknown"]
DIRECTIONS = ["forward", "backward", "left", "right", "turn_left", "turn_right", "none", "unknown"]


class MultiHeadBERT(nn.Module):
    """
    Inference-only multi-head model.
    - BERT backbone is frozen (as in your training setup).
    - Heads output raw logits for multiclass slots.
    - 'correction' head returns a RAW LOGIT (apply sigmoid at inference if you need a probability).
    """

    def __init__(self):
        super().__init__()
        self.bert = BertModel.from_pretrained("bert-base-uncased")

        # Freeze BERT (matches your training)
        for p in self.bert.parameters():
            p.requires_grad = False

        H = self.bert.config.hidden_size

        self.intent_head    = nn.Linear(H, len(INTENTS))
        self.region_head    = nn.Linear(H, len(REGIONS))
        self.speed_head     = nn.Linear(H, len(SPEEDS))
        self.hand_head      = nn.Linear(H, len(HANDS))
        self.ordering_head  = nn.Linear(H, len(ORDERING))
        self.direction_head = nn.Linear(H, len(DIRECTIONS))
        self.correction_head = nn.Linear(H, 1)  # RAW logit

    def forward(self, input_ids, attention_mask, token_type_ids=None):
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,  # <-- pass through (BERT handles None fine)
        )
        x = outputs.last_hidden_state[:, 0, :]

        return {
            "intent":     self.intent_head(x),     # [B, |INTENTS|]   (logits)
            "region":     self.region_head(x),     # [B, |REGIONS|]   (logits)
            "speed":      self.speed_head(x),      # [B, |SPEEDS|]    (logits)
            "hand":       self.hand_head(x),       # [B, |HANDS|]     (logits)
            "ordering":   self.ordering_head(x),   # [B, |ORDERING|]  (logits)
            "direction":  self.direction_head(x),  # [B, |DIRECTIONS|](logits)
            "correction": self.correction_head(x), # [B, 1] RAW logit (apply sigmoid outside)
        }

    @classmethod
    def from_pretrained(cls, path: str) -> "MultiHeadBERT":
        """
        Load weights exported from Colab into this exact skeleton.
        Expects: <path>/pytorch_model.bin
        """
        model = cls()
        state = torch.load(os.path.join(path, "pytorch_model.bin"), map_location="cpu")
        model.load_state_dict(state, strict=True)
        model.eval()
        return model
