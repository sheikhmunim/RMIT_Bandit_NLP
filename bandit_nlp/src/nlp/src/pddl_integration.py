# # pddl_integration.py 
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

# # ---------- ULTRA-MINIMAL PDDL ----------
# MINI_DOMAIN = """(define (domain base_actions)
#   (:requirements :strips)
#   (:predicates
#     (did_forward)
#     (did_backward)
#   )

#   (:action move-forward
#     :effect (and (did_forward))
#   )

#   (:action move-backward
#     :effect (and (did_backward))
#   )
# )
# """


# def write_domain_dynamic(path_domain: str, name: str = "base_actions"):
#     domain_text = f"""(define (domain {name})
#   (:requirements :strips)
#   (:predicates
#     (stopped)
#     (did_forward)
#     (did_backward)
#   )

#   (:action move-forward
#     :precondition (stopped)
#     :effect (and
#       (not (stopped))
#       (did_forward)
#     )
#   )

#   (:action move-backward
#     :precondition (stopped)
#     :effect (and
#       (not (stopped))
#       (did_backward)
#     )
#   )

#   (:action stop
#     :precondition (not (stopped))
#     :effect (stopped)
#   )
# )
# """
#     with open(path_domain, "w") as f:
#         f.write(domain_text)



# def write_domain(path_domain: str):
#     # emits the canonical base_actions domain
#     write_domain_dynamic(path_domain, name="base_actions")


# def write_problem_dynamic(path_problem: str, name: str, actions: list):
#     problem_text = f"""(define (problem {name})
#   (:domain base_actions)
#   (:init (stopped))
#   (:goal (and (stopped) (did_forward) (did_backward)))
# )
# """
#     with open(path_problem, "w") as f:
#         f.write(problem_text)

# # ---------- Fast Downward ----------

# def _read_plan_file(plan_file="sas_plan"):
#     """
#     Parse Fast Downward's plan file and return a list of action names.
#     Ignores comment lines (starting with ';') and the '(unit cost)' text.
#     Accepts lines either like '(move-forward)' or '0: (move-forward) ...'
#     """
#     import re, os
#     if not os.path.exists(plan_file):
#         return []
#     acts = []
#     with open(plan_file, "r", encoding="utf-8") as f:
#         for line in f:
#             s = line.strip().lower()
#             if not s or s.startswith(";"):
#                 continue
#             # Accept either "(action ...)" or "0: (action ...)"
#             m = re.match(r"(?:\d+:\s*)?\(\s*([a-z0-9_\-]+)", s)
#             if m:
#                 name = m.group(1)
#                 if name != "unit":   # skip the '(unit cost)' token in comments
#                     acts.append(name)
#     return acts





# # def run_fast_downward(domain_path, problem_path, downward_dir="downward", plan_file="plan.out"):
# #     import sys, shutil

# #     fd_py = os.path.join(downward_dir, "fast-downward.py")
# #     # Helpful sanity logs
# #     print(f"[pddl] FD path: {fd_py}")
# #     print(f"[pddl] Domain:  {domain_path}")
# #     print(f"[pddl] Problem: {problem_path}")
# #     print(f"[pddl] Planfile:{plan_file}")

# #     if not os.path.isfile(fd_py):
# #         return 127, [], f"fast-downward.py not found at {fd_py}", ""

# #     # Prefer python3 explicit call for robustness
# #     py = shutil.which("python3") or sys.executable
# #     cmd = [
# #         py, fd_py,
# #         domain_path, problem_path,
# #         "--plan-file", plan_file,
# #         "--search", "astar(lmcut())"
# #     ]

# #     r = subprocess.run(cmd, capture_output=True, text=True)
# #     # Always show stderr if it failed (so you see the real reason)
# #     if r.returncode != 0:
# #         print("----- FD STDOUT (tail) -----")
# #         print(r.stdout[-2000:])
# #         print("----- FD STDERR (tail) -----")
# #         print(r.stderr[-2000:])
# #     return r.returncode, _read_plan_file(plan_file), r.stdout[-2000:], r.stderr[-2000:]





# def run_fast_downward(domain_path, problem_path, downward_dir="downward", plan_file="sas_plan"):
#     import sys, shutil
#     fd_py = os.path.join(downward_dir, "fast-downward.py")
#     py = shutil.which("python3") or sys.executable
#     # Do NOT pass --plan-file; this build's search binary doesn't support it.
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
#         with tempfile.TemporaryDirectory() as tmp:
#             dom = os.path.join(tmp, "domain.pddl")
#             prob = os.path.join(tmp, "problem.pddl")
#             write_domain(dom)
#             write_problem_dynamic(prob, "seq_check", original)

#             # Optional: print exactly what we wrote
#             with open(dom, "r", encoding="utf-8") as f: dom_txt = f.read()
#             with open(prob, "r", encoding="utf-8") as f: prob_txt = f.read()
#             print("\n===== DOMAIN PDDL =====\n\n" + dom_txt + "\n\n===== PROBLEM PDDL =====\n\n" + prob_txt + "\n========================\n")

#             rc, plan_actions, out, err = run_fast_downward(dom, prob, downward_dir=downward_dir)
#             meta.update({"planner_rc": rc, "planner_out": out, "planner_err": err, "planner_actions": plan_actions})
#             if rc == 0 and plan_actions:
#                 repaired = plan_actions
#                 meta["method"] = "planner"
#             else:
#                 meta["method"] = "rule_fallback"

#     return repaired, meta





##############################################################################


# pddl_integration.py (static-domain integration)
import os, tempfile, subprocess, re

# ---------- Map between your steps and PDDL actions ----------
def step_to_action(step_scalar: dict):
    intent = step_scalar.get("intent", "move")
    direction = step_scalar.get("direction", "forward")
    if intent == "stop":
        return "stop"
    if intent == "move":
        if direction == "forward":
            return "move-forward"
        if direction == "backward":
            return "move-backward"
        if direction in ("turn_left", "turn_right", "spin"):
            return "spin"
    return None

def action_to_slots(a: str, default_speed="normal"):
    if a == "stop":
        return {"intent":"stop","region":"none","speed":"none","hand":"none","direction":"none"}
    if a == "move-forward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"forward"}
    if a == "move-backward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"backward"}
    if a == "spin":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"spin"}
    return None

# ---------- Simple rule-based repair ----------
def needs_stop_between(prev_a: str, curr_a: str):
    motion = {"move-forward", "move-backward"}
    return prev_a in motion and curr_a in motion

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
    # Priority 1: env var
    env_path = os.environ.get("PDDL_DOMAIN_PATH")
    if env_path:
        return env_path

    # Priority 2: rospack (if available)
    try:
        import rospkg
        rp = rospkg.RosPack()
        return os.path.join(rp.get_path("nlp"),"src","pddl", "domain_base.pddl")
    except Exception:
        pass

    # Priority 3: relative to this file (repo fallback)
    here = os.path.dirname(os.path.abspath(__file__))
    # .../src/nlp/src  -> .../src/nlp/pddl/domain_base.pddl
    repo_pddl = os.path.normpath(os.path.join(here, "..", "pddl", "domain_base.pddl"))
    return repo_pddl

def resolve_domain_path():
    p = _default_domain_path()
    if not os.path.isfile(p):
        raise FileNotFoundError(
            f"[pddl] Domain file not found. Tried: {p}\n"
            "Set PDDL_DOMAIN_PATH env var or place domain_base.pddl at nlp/pddl/"
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
    For the demo, we use a small goal that asks to have done forward/backward if they appear
    in the user's intended actions, and to be stopped if your domain models 'stopped'.
    Adjust as your domain grows (wave, pick/place, regions, etc.).
    """
    goal_atoms = []
    # If your domain uses 'stopped' predicate, you can include it here.
    # Comment this out if your static domain has no 'stopped' predicate.
    if True:
        goal_atoms.append("(stopped)")

    if "move-forward" in actions:
        goal_atoms.append("(did_forward)")
    if "move-backward" in actions:
        goal_atoms.append("(did_backward)")

    if not goal_atoms:
        goal_atoms = ["(stopped)"]  # safe default

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
    # Your build's search binary doesn't accept --plan-file, so we read 'sas_plan'.
    cmd = [
        py, fd_py,
        domain_path, problem_path,
        "--search", "astar(lmcut())"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, _read_plan_file(plan_file), r.stdout[-2000:], r.stderr[-2000:]

# ---------- Public API ----------
def plan_to_actions(plan: dict):
    actions = []
    for step in plan["steps"]:
        scalars = {"intent": step["intent"][0], "direction": step["direction"][0]}
        a = step_to_action(scalars)
        if a:
            actions.append(a)
    return actions

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

            # Optional: print exactly what we'll run
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
