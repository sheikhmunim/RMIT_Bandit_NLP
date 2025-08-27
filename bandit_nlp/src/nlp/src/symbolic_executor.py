#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# import rospy
# from geometry_msgs.msg import Twist

# # --- Config (safe spin) ---
# PUBLISH_HZ = 10.0
# SPIN_Z     = 0.5   # rad/s spin rate
# SEQ_PAUSE  = 0.2   # s, small pause for SEQUENCE

# # --- Globals ---
# cmd_pub = None
# _spinning = False   # whether we should spin in place now

# def _vel_tick(_evt):
#     """Publish cmd_vel at a steady rate (ROS1 convention)."""
#     t = Twist()
#     if _spinning:
#         t.angular.z = SPIN_Z      # spin only; linear stays 0 for safety
#     cmd_pub.publish(t)

# def init_executor():
#     """Call once from the grounding node AFTER rospy.init_node(...)."""
#     global cmd_pub
#     cmd_pub = rospy.Publisher('/mobile_base_controller/cmd_vel', Twist, queue_size=1)
#     rospy.Timer(rospy.Duration(1.0 / PUBLISH_HZ), _vel_tick)
#     rospy.loginfo("[executor] Streaming /mobile_base_controller/cmd_vel at %.1f Hz", PUBLISH_HZ)

# def execute_symbolic(labels):
#     """
#     Use EXISTING grounding labels (no grounding changes):
#       - Treat any GO_* (region/speed) as 'move' → spin in place.
#       - STOP → stop spinning.
#       - CORRECTION → stop first, then apply latest intent.
#       - SEQUENCE → STOP then spin (if both present).
#       - CONCURRENT/default → STOP wins if present, else spin if move-ish labels present.
#     """
#     global _spinning
#     if not isinstance(labels, (list, tuple)):
#         rospy.logwarn("[executor] labels must be list/tuple"); return

#     # Move intent according to your current grounding outputs
#     moveish = any(l in labels for l in (
#         'GO_SLOW', 'GO_FAST', 'GO_KITCHEN', 'GO_LIVING_ROOM', 'GO_TABLE'
#     ))
#     want_stop = ('STOP' in labels)

#     # Ordering
#     ordering = 'CONCURRENT'
#     if 'SEQUENCE' in labels:   ordering = 'SEQUENCE'
#     if 'CONCURRENT' in labels: ordering = 'CONCURRENT'

#     # Correction → cancel current behavior first
#     if 'CORRECTION' in labels:
#         _spinning = False
#         rospy.loginfo("[executor] CORRECTION → stop then apply new labels")

#     if ordering == 'SEQUENCE':
#         if want_stop:
#             rospy.loginfo("→ STOP (SEQ)")
#             _spinning = False
#             rospy.sleep(SEQ_PAUSE)
#         if moveish and not want_stop:
#             rospy.loginfo("→ SPIN (SEQ)")
#             _spinning = True
#     else:
#         if want_stop:
#             rospy.loginfo("→ STOP (CONCURRENT)")
#             _spinning = False
#         elif moveish:
#             rospy.loginfo("→ SPIN (CONCURRENT)")
#             _spinning = True

#     rospy.loginfo("[executor] spinning=%s (labels=%s)", _spinning, labels)



###################################################################################



import rospy
from geometry_msgs.msg import Twist

# --- Config (safe spin only) ---
PUBLISH_HZ = 10.0
SPIN_Z     = 0.5   # rad/s spin rate
SEQ_PAUSE  = 0.2   # s pause for sequential demo

# --- Globals ---
_cmd_pub   = None
_spinning  = False

def _vel_tick(_evt):
    """Publish steady velocity to spin if enabled."""
    t = Twist()
    if _spinning:
        t.angular.z = SPIN_Z  # rotate in place; linear stays 0 for safety
    _cmd_pub.publish(t)

def init_executor():
    """Initialize publishers/timers once at startup (call after rospy.init_node)."""
    global _cmd_pub
    _cmd_pub = rospy.Publisher('/mobile_base_controller/cmd_vel', Twist, queue_size=1)
    rospy.Timer(rospy.Duration(1.0 / PUBLISH_HZ), _vel_tick)
    rospy.loginfo("[executor] streaming /mobile_base_controller/cmd_vel at %.1f Hz", PUBLISH_HZ)

def execute_symbolic(slots: dict):
    """
    Accept the full slots dict but only do spin/stop for now.

    Expected slots shape:
      {
        'intent': 'move|wave|stop|...',
        'region': 'kitchen|living_room|table|bedroom|hallway|none|unknown',
        'speed': 'slow|fast|normal|none|unknown',
        'hand': 'left|right|none|unknown',
        'ordering': 'sequential|concurrent|contradiction|ambiguous|unknown',
        'direction': 'forward|backward|left|right|turn_left|turn_right|none|unknown',
        'correction': bool,
        'correction_score': float
      }
    """
    global _spinning

    # pull everything (we'll log it, ignore most for now)
    intent    = slots.get('intent', 'unknown')
    region    = slots.get('region', 'unknown')
    speed     = slots.get('speed', 'unknown')
    hand      = slots.get('hand', 'unknown')
    ordering  = slots.get('ordering', 'concurrent')
    direction = slots.get('direction', 'unknown')
    corr      = bool(slots.get('correction', False))
    corr_s    = float(slots.get('correction_score', 0.0))

    # log full slots for visibility while developing
    rospy.loginfo("[executor] slots intent=%s region=%s speed=%s hand=%s ordering=%s direction=%s corr=%.3f",
                  intent, region, speed, hand, ordering, direction, corr_s)

    # correction semantics: stop first, then handle the new intent
    if corr:
        _spinning = False
        rospy.loginfo("[executor] CORRECTION → stop first")

    # simple policy (spin-only for now)
    if ordering == 'sequential':
        if intent == 'stop':
            rospy.loginfo("→ STOP (SEQ)")
            _spinning = False
            rospy.sleep(SEQ_PAUSE)
        elif intent == 'move':
            rospy.loginfo("→ SPIN (SEQ)")
            _spinning = True
    else:  # 'concurrent' / unknown → treat as concurrent
        if intent == 'stop':
            rospy.loginfo("→ STOP (CONCURRENT)")
            _spinning = False
        elif intent == 'move':
            rospy.loginfo("→ SPIN (CONCURRENT)")
            _spinning = True

    rospy.loginfo("[executor] spinning=%s", _spinning)
