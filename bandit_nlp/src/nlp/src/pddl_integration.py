# # pddl_integration.py (static-domain integration)
# import os, tempfile, subprocess, re

# # ---------- Map between your steps and PDDL actions ----------
# def step_to_action(step_scalar: dict):
#     intent = step_scalar.get("intent", "move")
#     direction = step_scalar.get("direction", "forward")
#     if intent == "stop":
#         return "stop"
#     if intent == "move":
#         if direction == "forward":
#             return "move-forward"
#         if direction == "backward":
#             return "move-backward"
#         if direction in ("turn_left", "turn_right", "spin"):
#             return "spin"
#     return None

# def action_to_slots(a: str, default_speed="normal"):
#     if a == "stop":
#         return {"intent":"stop","region":"none","speed":"none","hand":"none","direction":"none"}
#     if a == "move-forward":
#         return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"forward"}
#     if a == "move-backward":
#         return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"backward"}
#     if a == "spin":
#         return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"spin"}
#     return None

# # ---------- Simple rule-based repair ----------
# def needs_stop_between(prev_a: str, curr_a: str):
#     motion = {"move-forward", "move-backward"}
#     return prev_a in motion and curr_a in motion

# def repair_sequence(actions):
#     if not actions:
#         return []
#     repaired = [actions[0]]
#     for a in actions[1:]:
#         prev = repaired[-1]
#         if needs_stop_between(prev, a) and prev != "stop":
#             repaired.append("stop")
#         repaired.append(a)
#     if repaired[-1] != "stop":
#         repaired.append("stop")
#     return repaired

# # ---------- Domain resolution ----------
# def _default_domain_path():
#     # Priority 1: env var
#     env_path = os.environ.get("PDDL_DOMAIN_PATH")
#     if env_path:
#         return env_path

#     # Priority 2: rospack (if available)
#     try:
#         import rospkg
#         rp = rospkg.RosPack()
#         return os.path.join(rp.get_path("nlp"),"src","pddl", "domain_base_old.pddl")
#     except Exception:
#         pass

#     # Priority 3: relative to this file (repo fallback)
#     here = os.path.dirname(os.path.abspath(__file__))
#     # .../src/nlp/src  -> .../src/nlp/pddl/domain_base.pddl
#     repo_pddl = os.path.normpath(os.path.join(here, "..", "pddl", "domain_base_old.pddl"))
#     return repo_pddl

# def resolve_domain_path():
#     p = _default_domain_path()
#     if not os.path.isfile(p):
#         raise FileNotFoundError(
#             f"[pddl] Domain file not found. Tried: {p}\n"
#             "Set PDDL_DOMAIN_PATH env var or place domain_base.pddl at nlp/pddl/"
#         )
#     return p

# def read_domain_name(domain_path: str) -> str:
#     with open(domain_path, "r", encoding="utf-8") as f:
#         txt = f.read().lower()
#     m = re.search(r"\(\s*define\s*\(\s*domain\s+([^)]+)\)", txt)
#     if not m:
#         raise ValueError(f"[pddl] Could not parse domain name from {domain_path}")
#     return m.group(1).strip()

# # ---------- Problem writer (dynamic from user command) ----------
# def write_problem_dynamic(path_problem: str, problem_name: str, domain_name: str, actions: list):
#     """
#     For the demo, we use a small goal that asks to have done forward/backward if they appear
#     in the user's intended actions, and to be stopped if your domain models 'stopped'.
#     Adjust as your domain grows (wave, pick/place, regions, etc.).
#     """
#     goal_atoms = []
#     # If your domain uses 'stopped' predicate, you can include it here.
#     # Comment this out if your static domain has no 'stopped' predicate.
#     if True:
#         goal_atoms.append("(stopped)")

#     if "move-forward" in actions:
#         goal_atoms.append("(did_forward)")
#     if "move-backward" in actions:
#         goal_atoms.append("(did_backward)")

#     if not goal_atoms:
#         goal_atoms = ["(stopped)"]  # safe default

#     problem = f"""(define (problem {problem_name})
#   (:domain {domain_name})
#   (:init (stopped))
#   (:goal (and {' '.join(goal_atoms)}))
# )
# """
#     with open(path_problem, "w", encoding="utf-8") as f:
#         f.write(problem)

# # ---------- Fast Downward ----------
# def _read_plan_file(plan_file="sas_plan"):
#     if not os.path.exists(plan_file):
#         return []
#     acts = []
#     with open(plan_file, "r", encoding="utf-8") as f:
#         for line in f:
#             s = line.strip().lower()
#             if not s or s.startswith(";"):
#                 continue
#             m = re.match(r"(?:\d+:\s*)?\(\s*([a-z0-9_\-]+)", s)
#             if m:
#                 name = m.group(1)
#                 if name != "unit":
#                     acts.append(name)
#     return acts

# def run_fast_downward(domain_path, problem_path, downward_dir="downward", plan_file="sas_plan"):
#     import sys, shutil
#     fd_py = os.path.join(downward_dir, "fast-downward.py")
#     py = shutil.which("python3") or sys.executable
#     # Your build's search binary doesn't accept --plan-file, so we read 'sas_plan'.
#     cmd = [
#         py, fd_py,
#         domain_path, problem_path,
#         "--search", "astar(lmcut())"
#     ]
#     r = subprocess.run(cmd, capture_output=True, text=True)
#     return r.returncode, _read_plan_file(plan_file), r.stdout[-2000:], r.stderr[-2000:]

# # ---------- Public API ----------
# def plan_to_actions(plan: dict):
#     actions = []
#     for step in plan["steps"]:
#         scalars = {"intent": step["intent"][0], "direction": step["direction"][0]}
#         a = step_to_action(scalars)
#         if a:
#             actions.append(a)
#     return actions

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

#             # Optional: print exactly what we'll run
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



######################################################################################################################################



# pddl_integration.py (static-domain integration) — updated
import os, tempfile, subprocess, re

# ---------- Map between your steps and PDDL actions ----------
def step_to_action(step_scalar: dict):
    intent    = step_scalar.get("intent", "move")
    direction = step_scalar.get("direction", "forward")

    if intent == "stop":
        return "stop"

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

# ---------- Problem writer (dynamic from user command) ----------
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


###############################################################

# PHASE_ACTIONS = {"move-forward", "move-backward", "turn-left", "turn-right", "spin"}

# def _classify_command_issues(plan: dict):
#     """Return a dict with flags describing illogical/underspecified aspects."""
#     issues = {
#         "unknown_actions": [],      # steps that map to None
#         "missing_direction": [],    # move with direction none/unknown
#         "forbid_stop": False,       # user said "without stopping"
#         "wants_concurrency": False, # ordering says concurrent
#     }

#     # 1) parse per-step scalar slots
#     for idx, step in enumerate(plan.get("steps", [])):
#         intent = (step.get("intent") or ["unknown"])[0]
#         direction = (step.get("direction") or ["unknown"])[0]
#         # “no stop” marker if you already propagate it; otherwise detect phrases earlier
#         forbid = bool((step.get("no_stop") or [False])[0])
#         if forbid:
#             issues["forbid_stop"] = True

#         # missing direction for a move?
#         if intent == "move" and direction in ("none", "unknown"):
#             issues["missing_direction"].append(idx)

#         # check mapping result
#         a = step_to_action({"intent": intent, "direction": direction})
#         if a is None and intent != "stop":
#             issues["unknown_actions"].append(idx)

#     # 2) full-text ordering
#     ord_full = plan.get("ordering", "sequential")
#     if ord_full == "concurrent":
#         issues["wants_concurrency"] = True

#     # quick overall flag
#     issues["has_hard_issue"] = bool(issues["unknown_actions"] or issues["wants_concurrency"])
#     issues["has_soft_issue"] = bool(issues["missing_direction"] or issues["forbid_stop"])

#     return issues


# def _make_seq_wrapped_domain(domain_name: str, seq_actions: list, *, allow_stop: bool) -> str:
#     flags = []
#     if any(a == "move-forward"  for a in seq_actions): flags.append("(did_forward)")
#     if any(a == "move-backward" for a in seq_actions): flags.append("(did_backward)")
#     if any(a == "turn-left"     for a in seq_actions): flags.append("(did_turn_left)")
#     if any(a == "turn-right"    for a in seq_actions): flags.append("(did_turn_right)")
#     if any(a == "spin"          for a in seq_actions): flags.append("(did_spin)")
#     stages = [f"(stage{i})" for i in range(len(seq_actions)+1)]
#     preds = "\n    ".join(["(stopped)"] + flags + stages)

#     stop_action = ""
#     if allow_stop:
#         stop_action = """
#   (:action stop
#     :precondition (not (stopped))
#     :effect (stopped)
#   )"""

#     wrapper_actions = []
#     for i, a in enumerate(seq_actions):
#         did = {
#             "move-forward":"(did_forward)",
#             "move-backward":"(did_backward)",
#             "turn-left":"(did_turn_left)",
#             "turn-right":"(did_turn_right)",
#             "spin":"(did_spin)"
#         }.get(a, "")
#         eff_flag = f"\n      {did}" if did else ""
#         wrapper_actions.append(f"""
#   (:action step{i+1}-{a}
#     :precondition (and (stopped) (stage{i}))
#     :effect (and
#       (not (stopped))
#       (not (stage{i}))
#       (stage{i+1}){eff_flag}
#     )
#   )""")

#     return f"""(define (domain {domain_name}-seqwrap)
#   (:requirements :strips)
#   (:predicates
#     {preds}
#   )
#   {stop_action}
#   {''.join(wrapper_actions)}
# )"""

# def _write_seqwrap_problem(path_problem: str, domain_name: str, seq_len: int):
#     problem = f"""(define (problem seqwrap_check)
#   (:domain {domain_name}-seqwrap)
#   (:init (stopped) (stage0))
#   (:goal (and (stopped) (stage{seq_len})))
# )
# """
#     with open(path_problem, "w", encoding="utf-8") as f:
#         f.write(problem)

# def _check_exact_sequence_feasible(seq_actions: list, downward_dir: str, *, allow_stop: bool):
#     import tempfile, os, shutil, sys, subprocess
#     if not seq_actions:
#         return True, {"reason":"empty_sequence"}
#     with tempfile.TemporaryDirectory() as tmp:
#         dom_name = "base_actions"
#         dom_txt = _make_seq_wrapped_domain(dom_name, seq_actions, allow_stop=allow_stop)
#         dom_path = os.path.join(tmp, "domain_seqwrap.pddl")
#         with open(dom_path, "w") as f: f.write(dom_txt)
#         prob_path = os.path.join(tmp, "problem_seqwrap.pddl")
#         _write_seqwrap_problem(prob_path, dom_name, len(seq_actions))
#         fd_py = os.path.join(downward_dir or "downward", "fast-downward.py")
#         py = shutil.which("python3") or sys.executable
#         r = subprocess.run([py, fd_py, dom_path, prob_path, "--search", "astar(lmcut())"],
#                            capture_output=True, text=True, cwd=tmp)
#         return (r.returncode == 0), {"rc": r.returncode, "out": r.stdout[-2000:], "err": r.stderr[-2000:]}


########################################################################

def pddl_validate_and_repair(plan: dict, *, use_planner=False, downward_dir="downward"):
    original = plan_to_actions(plan)
    repaired = repair_sequence(original)
    meta = {"method": "rule_repair", "original": original}

    if use_planner:
        domain_path = resolve_domain_path()
        domain_name = read_domain_name(domain_path)

        with tempfile.TemporaryDirectory() as tmp:
            prob = os.path.join(tmp, "problem.pddl")
            write_problem_dynamic(prob, "seq_check", domain_name, original)

            # Optional: print what we'll run (helps debugging)
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


###########################################################################################################


# def pddl_validate_and_repair(plan: dict, *, use_planner=False, downward_dir="downward"):
#     """
#     Behavior:
#       - If exact user intent is clean & feasible → preserve that exact order (with glue stops).
#       - Else → planner INTERVENES to produce a feasible plan on the normal domain.
#     """
#     original = plan_to_actions(plan)  # exact order the user asked (might be partial)
#     issues = _classify_command_issues(plan)

#     # Preserve user order but make it executable (insert stop between phases + trailing stop).
#     user_exec = repair_sequence(original)
#     if user_exec and user_exec[-1] != "stop":
#         user_exec.append("stop")

#     meta = {"original": original, "issues": issues, "method": "rule_preserve"}

#     if not use_planner:
#         return user_exec, meta

#     # If we detected hard issues, skip exact-sequence check and intervene.
#     if issues["has_hard_issue"]:
#         feasible = False
#         meta["seq_check"] = {"skipped": True, "reason": "hard_issue"}
#     else:
#         # “No stop” → forbid stop during feasibility check; else allow
#         allow_stop_in_check = not issues["forbid_stop"]
#         # IMPORTANT: check the *exact* sequence the user asked (NO glue stops)
#         seq_to_check = list(original)
#         feasible, chk = _check_exact_sequence_feasible(seq_to_check, downward_dir, allow_stop=allow_stop_in_check)
#         meta["seq_check"] = {"feasible": feasible, "allow_stop": allow_stop_in_check, **chk}

#     if feasible and not issues["missing_direction"]:
#         # Good to go: preserve user’s intent & order; execute with glue stops
#         meta["method"] = "preserve_user_sequence"
#         return user_exec, meta

#     # --- Planner INTERVENES on the real domain ---
#     domain_path = resolve_domain_path()
#     domain_name = read_domain_name(domain_path)

#     with tempfile.TemporaryDirectory() as tmp:
#         prob = os.path.join(tmp, "problem.pddl")
#         write_problem_dynamic(prob, "loose_goal", domain_name, original)
#         rc, plan_actions, out, err = run_fast_downward(domain_path, prob, downward_dir=downward_dir, workdir=tmp)

#     meta.update({"planner_rc": rc, "planner_out": out, "planner_err": err, "planner_actions": plan_actions})

#     if rc == 0 and plan_actions:
#         repaired = list(plan_actions)
#         if repaired and repaired[-1] in PHASE_ACTIONS:
#             repaired.append("stop")
#         meta["method"] = "planner_intervene"
#         return repaired, meta

#     # No feasible plan even after intervention → safe fallback
#     meta["method"] = "infeasible_no_plan"
#     return ["stop"], meta
