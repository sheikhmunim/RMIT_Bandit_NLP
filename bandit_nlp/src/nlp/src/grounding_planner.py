import re
from typing import Callable, Dict, List, Tuple, Any


class GroundingPlanner:
    """
    Pure splitter + per-chunk classifier adapter, with ordering predicted once
    from the FULL command via your model's ordering head and then resolved via
    lightweight language cues.

    You pass:
      - predict_fn(chunk_text) -> slots dict    (per-chunk classification)
      - order_predict_fn(full_text) -> slots    (ordering from full text; can reuse predict_fn)

    The class:
      - splits the text into chunks (no defaults/inheritance),
      - classifies each chunk (intent/speed/direction/hand/region),
      - queries ordering ONCE on the full command,
      - resolves final ordering using simple linguistic rules,
      - returns a multi-step plan dict.
    """

    # Step boundaries: treat these as separators between actions
    _SEP_REGEX = re.compile(
        r"\b(?:and then|then|and|after that|afterwards|next|;|,|&|->|→)\b",
        flags=re.IGNORECASE,
    )

    # Ordering cues
    _SEQ_CUES = re.compile(r"\b(?:and then|then|after that|afterwards|next)\b", re.IGNORECASE)
    _CONC_CUES = re.compile(r"\b(?:while|at the same time|together|simultaneously|concurrently)\b", re.IGNORECASE)

    def __init__(
        self,
        predict_fn: Callable[[str], Dict[str, Any]],
        order_predict_fn: Callable[[str], Dict[str, Any]] = None,
        *,
        normalize_lr_to_turn: bool = True,
        map_unknown_speed_to: str = "normal",
        map_unknown_direction_to: str = "forward",
        fallback_ordering: str = "sequential",
    ) -> None:
        """
        Args:
            predict_fn: per-chunk classifier. Returns slots dict with keys like:
                intent, region, speed, hand, direction, ordering, correction, correction_score
            order_predict_fn: full-text classifier used solely to read 'ordering'.
                If None, predict_fn will be reused on the full text.
            normalize_lr_to_turn: map 'left'/'right' -> 'turn_left'/'turn_right'
            map_unknown_speed_to: replace speed='unknown' with this value
            map_unknown_direction_to: replace direction='unknown' with this value
            fallback_ordering: used when model returns missing/unknown ordering
        """
        self.predict_fn = predict_fn
        self.order_predict_fn = order_predict_fn or predict_fn
        self.normalize_lr_to_turn = normalize_lr_to_turn
        self.map_unknown_speed_to = map_unknown_speed_to
        self.map_unknown_direction_to = map_unknown_direction_to
        self.fallback_ordering = fallback_ordering

    # ---------- public API ----------

    def split_into_chunks(self, command: str) -> Tuple[List[str], int]:
        """Pure splitter: text -> ordered list of chunk strings (no defaults/inheritance)."""
        text = re.sub(r"\s+", " ", command or "").strip()
        if not text:
            return [], 0
        parts = [p.strip(" .,!?:;") for p in self._SEP_REGEX.split(text)]
        chunks = [p for p in parts if p]
        return chunks, len(chunks)

    def predict_step(self, chunk_text: str) -> Dict[str, List[str]]:
        """Classify a single chunk string -> step dict (list-valued fields)."""
        slots = self.predict_fn(chunk_text)
        return self._slots_to_step(slots)

    def predict_steps(self, full_text: str) -> Dict[str, Any]:
        """
        Split into chunks, classify each chunk, and attach ordering predicted
        from the full text using the model's ordering head, then resolved by rules.
        """
        chunks, n = self.split_into_chunks(full_text)
        if n == 0:
            chunks, n = [full_text], 1

        steps = [self.predict_step(ch) for ch in chunks]

        # ---- ordering from the full command (model) ----
        ord_slots = self.order_predict_fn(full_text) or {}
        model_ordering = (ord_slots.get("ordering") or self.fallback_ordering)

        # ---- rule-based override / resolution ----
        ordering = self._resolve_ordering(full_text, model_ordering)

        return {
            "text": full_text,
            "num_steps": n,
            "chunks": chunks,
            "steps": steps,
            "ordering": ordering,  # final, rule-resolved ordering
            "correction": 0,       # keep simple; wire per-chunk correction if needed
        }

    # ---------- internals ----------

    def _resolve_ordering(self, text: str, model_ordering: str) -> str:
        """
        Resolve final ordering using lightweight cues:
          - If concurrent cue present: concurrent
          - Else if sequential cue (or comma-separated verbs): sequential
          - Else if model said contradiction/unknown: downgrade to sequential
          - Else: use model ordering
        """
        t = text or ""
        if self._CONC_CUES.search(t):
            return "concurrent"

        if self._SEQ_CUES.search(t) or "," in t:
            return "sequential"

        if model_ordering in (None, "", "unknown", "contradiction"):
            return self.fallback_ordering

        return model_ordering

    def _slots_to_step(self, slots: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Map a single-slot dict from the model into the dataset step schema,
        ensuring each field is a single-item list.
        """
        direction = (slots.get("direction") or "none")
        speed = (slots.get("speed") or "normal")
        intent = (slots.get("intent") or "move")

        # Normalize unknowns
        if speed == "unknown":
            speed = self.map_unknown_speed_to
        if direction == "unknown":
            direction = self.map_unknown_direction_to

        # Optionally map left/right to turn_left/turn_right
        if self.normalize_lr_to_turn and direction in ("left", "right"):
            direction = f"turn_{direction}"

        # If stop, normalize fields to none
        if intent == "stop":
            speed = "none"
            direction = "none"

        return {
            "intent":    [intent],
            "region":    [slots.get("region", "none") or "none"],
            "speed":     [speed],
            "hand":      [slots.get("hand", "none") or "none"],
            "direction": [direction],
        }
