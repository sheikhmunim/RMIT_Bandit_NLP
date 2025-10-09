# pddl_integration.py (static-domain integration) — updated
import os, tempfile, subprocess, re


# --- put these helpers near the top of pddl_integration.py ---
def _get1(v, default=""):
    """Return the first element if v is a list/tuple, else v or default."""
    if isinstance(v, (list, tuple)):
        return v[0] if v else default
    return v if v is not None else default

def _norm1(v, default=""):
    """_get1 + lowercased string."""
    return str(_get1(v, default)).lower()




# ---------- Map between your steps and PDDL actions ----------
def step_to_action(step_scalar: dict):
    intent    = step_scalar.get("intent", "move")
    direction = step_scalar.get("direction", "forward")
    hand      = step_scalar.get("hand", "none")

    if intent == "stop":
        return "stop"
    if intent == "wave":
        # keep hand info encoded in action name (optional)
        if hand in ("left", "right"):
            return f"wave-{hand}"
        return "wave"

    if intent == "move":
        if direction == "forward":
            return "move-forward"
        if direction == "backward":
            return "move-backward"
        if direction == "turn_left":
            return "turn-left"
        if direction == "turn_right":
            return "turn-right"
        if direction == "spin":
            return "spin"

    return None

def action_to_slots(a: str, default_speed="normal"):
    if a == "stop":
        return {"intent":"stop","region":"none","speed":"none","hand":"none","direction":"none"}
    if a == "move-forward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"forward"}
    if a == "move-backward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"backward"}
    if a == "turn-left":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"turn_left"}
    if a == "turn-right":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"turn_right"}
    if a == "spin":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"spin"}
    # NEW ---- handle wave actions ----
    if a in ("wave", "wave-left", "wave-right"):
        hand = "left" if "left" in a else ("right" if "right" in a else "none")
        return {
            "intent": "wave",
            "region": "none",
            "speed": "none",
            "hand": hand,
            "direction": "none"
        }

    return None

# ---------- Simple rule-based repair ----------
PHASE_ACTIONS = {"move-forward", "move-backward", "turn-left", "turn-right", "spin"}

def needs_stop_between(prev_a: str, curr_a: str):
    # Any two consecutive phase actions must be separated by 'stop'
    return prev_a in PHASE_ACTIONS and curr_a in PHASE_ACTIONS

def repair_sequence(actions):
    if not actions:
        return []
    repaired = [actions[0]]
    for a in actions[1:]:
        prev = repaired[-1]
        if needs_stop_between(prev, a) and prev != "stop":
            repaired.append("stop")
        repaired.append(a)
    if repaired[-1] != "stop":
        repaired.append("stop")
    return repaired

# ---------- Domain resolution ----------
def _default_domain_path():
    # Priority 1: explicit env var
    env_path = os.environ.get("PDDL_DOMAIN_PATH")
    if env_path:
        return env_path

    # Priority 2: rospack (if available) — try both filenames
    try:
        import rospkg
        rp = rospkg.RosPack()
        base = os.path.join(rp.get_path("nlp"), "src", "pddl")
        cand = [os.path.join(base, "domain_base.pddl"),
                os.path.join(base, "base_actions_ext.pddl")]
        for c in cand:
            if os.path.isfile(c):
                return c
        # fall through if none exist
    except Exception:
        pass

    # Priority 3: repo relative (try both filenames)
    here = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.normpath(os.path.join(here, "..", "pddl"))
    cand = [os.path.join(repo_dir, "domain_base.pddl"),
            os.path.join(repo_dir, "base_actions_ext.pddl")]
    for c in cand:
        if os.path.isfile(c):
            return c
    # default to first candidate path for error message
    return cand[0]

def resolve_domain_path():
    p = _default_domain_path()
    if not os.path.isfile(p):
        raise FileNotFoundError(
            f"[pddl] Domain file not found. Tried: {p}\n"
            "Set PDDL_DOMAIN_PATH env var or place domain_base.pddl or base_actions_ext.pddl at nlp/pddl/"
        )
    return p

def read_domain_name(domain_path: str) -> str:
    with open(domain_path, "r", encoding="utf-8") as f:
        txt = f.read().lower()
    m = re.search(r"\(\s*define\s*\(\s*domain\s+([^)]+)\)", txt)
    if not m:
        raise ValueError(f"[pddl] Could not parse domain name from {domain_path}")
    return m.group(1).strip()

# # ---------- Problem writer (dynamic from user command) ----------
def write_problem_dynamic(path_problem: str, problem_name: str, domain_name: str, actions: list):
    """
    Add (speed-normal) to :init so move-* preconditions are satisfiable.
    Also keep (stopped) so stop-insertion remains meaningful.
    """
    goal_atoms = []
    if "move-forward" in actions:
        goal_atoms.append("(did_forward)")
    if "move-backward" in actions:
        goal_atoms.append("(did_backward)")
    if "turn-left" in actions:
        goal_atoms.append("(did_turn_left)")
    if "turn-right" in actions:
        goal_atoms.append("(did_turn_right)")
    if "spin" in actions:
        goal_atoms.append("(did_spin)")

    if not goal_atoms:
        goal_atoms = ["(stopped)"]

    problem = f"""(define (problem {problem_name})
  (:domain {domain_name})
  (:init (stopped))
  (:goal (and {' '.join(goal_atoms)}))
)
"""
    with open(path_problem, "w", encoding="utf-8") as f:
        f.write(problem)


















# def write_problem_dynamic(path_problem: str, problem_name: str, domain_name: str, actions: list):
#     goal_atoms = []

#     if "move-forward" in actions:
#         goal_atoms.append("(did_forward)")
#     if "move-backward" in actions:
#         goal_atoms.append("(did_backward)")
#     if "turn-left" in actions:
#         goal_atoms.append("(did_turn_left)")
#     if "turn-right" in actions:
#         goal_atoms.append("(did_turn_right)")
#     if "spin" in actions:
#         goal_atoms.append("(did_spin)")

#     # NEW: parameterized wave
#     need_wave_left  = "wave-left" in actions
#     need_wave_right = "wave-right" in actions
#     need_wave_any   = "wave" in actions

#     if need_wave_left:
#         goal_atoms.append("(did_wave left)")
#     if need_wave_right:
#         goal_atoms.append("(did_wave right)")
#     if need_wave_any and not (need_wave_left or need_wave_right):
#         # accept either hand if user didn't specify
#         # simplest: require at least one of them – encode both or choose one
#         goal_atoms.append("(did_wave left)")

#     if not goal_atoms:
#         goal_atoms = ["(stopped)"]

#     problem = f"""(define (problem {problem_name})
#   (:domain {domain_name})
#   (:objects left right - hand)
#   (:init (stopped))
#   (:goal (and {' '.join(goal_atoms)}))
# )
# """
#     with open(path_problem, "w", encoding="utf-8") as f:
#         f.write(problem)



# ---------- Fast Downward ----------
def _read_plan_file(plan_file="sas_plan"):
    if not os.path.exists(plan_file):
        return []
    acts = []
    with open(plan_file, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip().lower()
            if not s or s.startswith(";"):
                continue
            m = re.match(r"(?:\d+:\s*)?\(\s*([a-z0-9_\-]+)", s)
            if m:
                name = m.group(1)
                if name != "unit":
                    acts.append(name)
    return acts

def run_fast_downward(domain_path, problem_path, downward_dir="downward", plan_file="sas_plan"):
    import sys, shutil
    fd_py = os.path.join(downward_dir, "fast-downward.py")
    py = shutil.which("python3") or sys.executable
    cmd = [py, fd_py, domain_path, problem_path, "--search", "astar(lmcut())"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, _read_plan_file(plan_file), r.stdout[-2000:], r.stderr[-2000:]

# ---------- Public API ----------
def plan_to_actions(plan: dict):
    actions = []
    for step in plan["steps"]:
        scalars = {
            "intent":    step["intent"][0],
            "direction": step["direction"][0],
        }
        a = step_to_action(scalars)
        if a:
            actions.append(a)
    return actions


# def pddl_validate_and_repair(plan: dict, *, use_planner=False, downward_dir="downward"):
#     original = plan_to_actions(plan)
#     repaired = repair_sequence(original)
#     meta = {"method": "rule_repair", "original": original}

#     if use_planner:
#         domain_path = resolve_domain_path()
#         domain_name = read_domain_name(domain_path)

#         with tempfile.TemporaryDirectory() as tmp:
#             prob = os.path.join(tmp, "problem.pddl")
#             write_problem_dynamic(prob, "seq_check", domain_name, original)

#             # Optional: print what we'll run (helps debugging)
#             try:
#                 with open(domain_path, "r", encoding="utf-8") as f: dom_txt = f.read()
#                 with open(prob, "r", encoding="utf-8") as f: prob_txt = f.read()
#                 print("\n===== DOMAIN PDDL (from disk) =====\n\n" + dom_txt +
#                       "\n\n===== PROBLEM PDDL (generated) =====\n\n" + prob_txt +
#                       "\n========================\n")
#             except Exception:
#                 pass

#             rc, plan_actions, out, err = run_fast_downward(domain_path, prob, downward_dir=downward_dir)
#             meta.update({"planner_rc": rc, "planner_out": out, "planner_err": err, "planner_actions": plan_actions})
#             if rc == 0 and plan_actions:
#                 repaired = plan_actions
#                 meta["method"] = "planner"
#             else:
#                 meta["method"] = "rule_fallback"

#     return repaired, meta



def pddl_validate_and_repair(plan: dict, *, use_planner=False, downward_dir="downward"):
    original = plan_to_actions(plan)          # e.g., ['move-forward','move-forward']
    repaired = repair_sequence(original)      # your existing rule repair (e.g., insert 'stop' between opposite moves)
    meta = {"method": "rule_repair", "original": original}

    # ---------- SPEED-ONLY SHORT-CIRCUIT (Option A) ----------
# --- replace your _is_speed_only_sequence with this ---
    def _is_speed_only_sequence(p: dict) -> bool:
        steps = p.get("steps", [])
        if len(steps) < 2:
            return False

        intents_ok = all(_norm1(s.get("intent"), "unknown") == "move" for s in steps)
        dirs      = { _norm1(s.get("direction"), "none") for s in steps }
        speeds    = { _norm1(s.get("speed"), "normal")  for s in steps }

        same_dir = len(dirs) == 1 and (("forward" in dirs) or ("backward" in dirs))
        mult_speeds = len(speeds) > 1
        return intents_ok and same_dir and mult_speeds

    if _is_speed_only_sequence(plan):
        direction = _norm1(plan["steps"][0].get("direction"), "forward")
        act = "move-forward" if direction == "forward" else "move-backward"
        repaired = []
        for k in range(len(plan["steps"])):
            if k > 0:
                repaired.append("stop")
            repaired.append(act)
        meta.update({"method": "rule_speed_chain", "repaired": True})
        return repaired, meta
    # ---------------------------------------------------------

    if use_planner:
        domain_path = resolve_domain_path()
        domain_name = read_domain_name(domain_path)

        with tempfile.TemporaryDirectory() as tmp:
            prob = os.path.join(tmp, "problem.pddl")
            write_problem_dynamic(prob, "seq_check", domain_name, original)

            try:
                with open(domain_path, "r", encoding="utf-8") as f: dom_txt = f.read()
                with open(prob, "r", encoding="utf-8") as f: prob_txt = f.read()
                print("\n===== DOMAIN PDDL (from disk) =====\n\n" + dom_txt +
                      "\n\n===== PROBLEM PDDL (generated) =====\n\n" + prob_txt +
                      "\n========================\n")
            except Exception:
                pass

            rc, plan_actions, out, err = run_fast_downward(domain_path, prob, downward_dir=downward_dir)
            meta.update({"planner_rc": rc, "planner_out": out, "planner_err": err, "planner_actions": plan_actions})
            if rc == 0 and plan_actions:
                repaired = plan_actions
                meta["method"] = "planner"
            else:
                meta["method"] = "rule_fallback"

    return repaired, meta
