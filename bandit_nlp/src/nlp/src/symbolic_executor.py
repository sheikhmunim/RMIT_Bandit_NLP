# symbolic_executor.py
# Executor aligned to base_actions_ext domain (no wave; includes spin).
# Adds CSV logging while keeping DRY-RUN printing.

import os, time, csv
import rospy
from geometry_msgs.msg import Twist

# ---------- defaults (overridable) ----------
PUBLISH_HZ_DEFAULT     = 10.0
MOVE_DURATION_DEFAULT  = 1.5
TURN_DURATION_DEFAULT  = 1.0
SPIN_DURATION_DEFAULT  = 1.0
SEQ_PAUSE_DEFAULT      = 0.10

LIN_X_DEFAULTS = {"slow": 0.12, "normal": 0.22, "fast": 0.32}
ANG_Z_DEFAULTS = {"slow": 0.35, "normal": 0.55, "fast": 0.75}
LIN_X_MAX = 0.60
ANG_Z_MAX = 1.50

# ---------- module state ----------
_cmd_pub     = None
_timer       = None
_curr_twist  = Twist()
_speed_state = "normal"
_dry_run     = True

_publish_hz = PUBLISH_HZ_DEFAULT
_move_dur   = MOVE_DURATION_DEFAULT
_turn_dur   = TURN_DURATION_DEFAULT
_spin_dur   = SPIN_DURATION_DEFAULT
_seq_pause  = SEQ_PAUSE_DEFAULT

_lin_map = LIN_X_DEFAULTS.copy()
_ang_map = ANG_Z_DEFAULTS.copy()

# logging
_log_csv       = False
_log_csv_path  = os.path.expanduser("~/.ros/symbolic_exec_log.csv")
_csv_header    = ["ts", "event", "intent", "direction", "speed", "duration_s", "ok", "reason"]

def _param(name, default): return rospy.get_param("~" + name, default)

def _ensure_csv_header():
    if not _log_csv:
        return
    d = os.path.dirname(_log_csv_path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    new_file = not os.path.exists(_log_csv_path)
    if new_file:
        with open(_log_csv_path, "w", newline="") as f:
            csv.writer(f).writerow(_csv_header)

def _log_row(event, intent="", direction="", speed="", duration_s="", ok="", reason=""):
    if not _log_csv:
        return
    with open(_log_csv_path, "a", newline="") as f:
        csv.writer(f).writerow([time.time(), event, intent, direction, speed, duration_s, ok, reason])

def _load_params():
    global _publish_hz, _move_dur, _turn_dur, _spin_dur, _seq_pause, _lin_map, _ang_map
    global _dry_run, _log_csv, _log_csv_path
    _publish_hz = float(_param("publish_hz", PUBLISH_HZ_DEFAULT))
    _move_dur   = float(_param("move_duration", MOVE_DURATION_DEFAULT))
    _turn_dur   = float(_param("turn_duration", TURN_DURATION_DEFAULT))
    _spin_dur   = float(_param("spin_duration", SPIN_DURATION_DEFAULT))
    _seq_pause  = float(_param("seq_pause", SEQ_PAUSE_DEFAULT))
    _dry_run    = bool(_param("dry_run", True))  # default: desktop DRY-RUN
    _log_csv    = bool(_param("log_csv", True))
    _log_csv_path = os.path.expanduser(_param("log_csv_path", "~/.ros/symbolic_exec_log.csv"))

    lin_override = _param("lin_x_map", {})
    ang_override = _param("ang_z_map", {})
    if isinstance(lin_override, dict):
        _lin_map.update({k: float(v) for k, v in lin_override.items() if k in _lin_map})
    if isinstance(ang_override, dict):
        _ang_map.update({k: float(v) for k, v in ang_override.items() if k in _ang_map})

def _tick(_evt):
    if _dry_run or _cmd_pub is None:
        return
    _cmd_pub.publish(_curr_twist)

def _clamp(v, lo, hi): return max(lo, min(hi, v))
def _speed_lin(): return _clamp(_lin_map.get(_speed_state, _lin_map["normal"]), 0.0, LIN_X_MAX)
def _speed_ang(): return _clamp(_ang_map.get(_speed_state, _ang_map["normal"]), 0.0, ANG_Z_MAX)

def init_executor():
    global _cmd_pub, _timer
    _load_params()
    _ensure_csv_header()

    if _dry_run:
        rospy.logwarn("[executor] DRY-RUN: will PRINT actions, simulate timing; no cmd_vel published.")
    else:
        _cmd_pub = rospy.Publisher("/mobile_base_controller/cmd_vel", Twist, queue_size=1)
        _timer   = rospy.Timer(rospy.Duration(1.0 / _publish_hz), _tick)
        rospy.loginfo("[executor] streaming cmd_vel at %.1f Hz", _publish_hz)

    rospy.loginfo("[executor] speed=%s | move=%.2fs turn=%.2fs spin=%.2fs | pause=%.2fs | csv=%s -> %s",
                  _speed_state, _move_dur, _turn_dur, _spin_dur, _seq_pause, _log_csv, _log_csv_path)

def _run_phase(duration_sec, twist, label, intent, direction, speed):
    global _curr_twist
    start = time.time()
    _log_row("ACTION_START", intent, direction, speed, "", "", "")

    if _dry_run:
        print(f"[DRYRUN] EXEC {label} for {duration_sec:.2f}s")
        time.sleep(float(duration_sec))
        print(f"[DRYRUN] BRAKE + pause {_seq_pause:.2f}s")
        time.sleep(_seq_pause)
        dur = time.time() - start
        _log_row("ACTION_DONE", intent, direction, speed, f"{dur:.3f}", 1, "")
        return

    end_t = start + float(duration_sec)
    while time.time() < end_t and not rospy.is_shutdown():
        _curr_twist = twist
        time.sleep(0.02)

    _curr_twist = Twist()
    time.sleep(_seq_pause)
    dur = time.time() - start
    _log_row("ACTION_DONE", intent, direction, speed, f"{dur:.3f}", 1, "")

def _apply_speed_slot(speed_slot):
    global _speed_state
    if not isinstance(speed_slot, str):
        return
    s = speed_slot.strip().lower()
    if s in ("slow", "normal", "fast"):
        _speed_state = s
        msg = f"[executor] speed_state := {s}"
        print("[DRYRUN] " + msg if _dry_run else msg)
        rospy.loginfo(msg)
        _log_row("SPEED_SET", "", "", s, "", "", "")

def execute_symbolic(slots: dict):
    global _curr_twist

    if not slots:
        rospy.logwarn("[executor] empty slots; ignoring")
        return

    intent     = str(slots.get("intent", "unknown"))
    direction  = str(slots.get("direction", "unknown"))
    speed_slot = str(slots.get("speed", "unknown"))
    correction = bool(slots.get("correction", False))

    pretty = f"{intent}:{direction} speed={speed_slot} corr={correction}"
    print(f"[EXEC] {pretty}")
    rospy.loginfo("[executor] " + pretty)

    # correction → immediate stop before new step
    if correction:
        if _dry_run:
            print(f"[DRYRUN] CORRECTION -> hard STOP + pause {_seq_pause:.2f}s")
        _curr_twist = Twist()
        time.sleep(_seq_pause)
        _log_row("CORRECTION", intent, direction, speed_slot, "", "", "pre-stop")

    _apply_speed_slot(speed_slot)

    lin_mag = _speed_lin()
    ang_mag = _speed_ang()
    cmd = Twist(); dur = 0.0; label = ""

    if intent == "stop":
        label = "STOP"
        _run_phase(_seq_pause, Twist(), label, intent, direction, speed_slot)
        return

    if intent != "move":
        rospy.logwarn("[executor] unsupported intent=%s", intent)
        _log_row("ACTION_SKIP", intent, direction, speed_slot, "", 0, "unsupported_intent")
        return

    if direction == "forward":
        cmd.linear.x = lin_mag; dur = _move_dur; label = f"MOVE FORWARD (vx={cmd.linear.x:.2f})"
    elif direction == "backward":
        cmd.linear.x = -lin_mag; dur = _move_dur; label = f"MOVE BACKWARD (vx={cmd.linear.x:.2f})"
    elif direction == "turn_left":
        cmd.angular.z = ang_mag; dur = _turn_dur; label = f"TURN LEFT (wz={cmd.angular.z:.2f})"
    elif direction == "turn_right":
        cmd.angular.z = -ang_mag; dur = _turn_dur; label = f"TURN RIGHT (wz={-cmd.angular.z:.2f})"
    elif direction == "spin":
        cmd.angular.z = ang_mag; dur = _spin_dur; label = f"SPIN (wz={cmd.angular.z:.2f})"
    else:
        rospy.logwarn("[executor] unknown direction=%s; ignoring", direction)
        _log_row("ACTION_SKIP", intent, direction, speed_slot, "", 0, "unknown_direction")
        return

    _run_phase(dur, cmd, label, intent, direction, speed_slot)
