# pddl_integration.py
import os
import tempfile
import subprocess

# ---------- Mapping between your steps and PDDL actions ----------

def step_to_action(step_scalar: dict):
    """
    step_scalar = {intent, direction, ...} (all scalars)
    Returns one of: move-forward | move-backward | stop | spin | None
    """
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
    """Map PDDL action tokens back to your executor slot dict."""
    if a == "stop":
        return {"intent":"stop","region":"none","speed":"none","hand":"none","direction":"none"}
    if a == "move-forward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"forward"}
    if a == "move-backward":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"backward"}
    if a == "spin":
        return {"intent":"move","region":"none","speed":default_speed,"hand":"none","direction":"spin"}
    return None

# ---------- Simple rule-based validator/repair (no external tools) ----------

def needs_stop_between(prev_a: str, curr_a: str):
    """
    Enforce a safety invariant:
      - Any two motion actions must be separated by STOP
      - Particularly opposite motions (forward <-> backward)
    """
    motion = {"move-forward", "move-backward"}
    if prev_a in motion and curr_a in motion:
        return True
    return False

def repair_sequence(actions):
    """Insert stop where needed, and ensure final stop."""
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

# ---------- PDDL files ----------

MINI_DOMAIN = """(define (domain base_actions)
  (:requirements :strips)
  (:predicates
    (stopped)
    (moving-forward)
    (moving-backward)
  )

  (:action move-forward
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (moving-forward)
      (not (moving-backward))
    )
  )

  (:action move-backward
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (moving-backward)
      (not (moving-forward))
    )
  )

  (:action stop
    :precondition (or (moving-forward) (moving-backward))
    :effect (and
      (stopped)
      (not (moving-forward))
      (not (moving-backward))
    )
  )

  (:action spin
    :precondition (stopped)
    :effect (stopped)
  )
)
"""

def write_domain(path_domain: str):
    with open(path_domain, "w", encoding="utf-8") as f:
        f.write(MINI_DOMAIN)

def write_problem(path_problem: str, name: str = "seq"):
    problem = f"""(define (problem {name})
  (:domain base_actions)
  (:init (stopped))
  (:goal (stopped))
)"""
    with open(path_problem, "w", encoding="utf-8") as f:
        f.write(problem)

# ---------- Optional: Fast Downward cross-check ----------

def run_fast_downward(domain_path, problem_path, downward_dir="downward"):
    """
    Returns (return_code, stdout_tail, stderr_tail). Requires Fast Downward installed.
    """
    cmd = [
        os.path.join(downward_dir, "fast-downward.py"),
        domain_path, problem_path,
        "--search", "astar(lmcut())"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout[-2000:], r.stderr[-2000:]

# ---------- Public API ----------

def plan_to_actions(plan: dict):
    """
    Flatten your planner output -> list of PDDL actions.
    plan['steps'][i] has list fields; we flatten first.
    """
    actions = []
    for i, step in enumerate(plan["steps"]):
        scalars = {
            "intent": step["intent"][0],
            "direction": step["direction"][0],
        }
        a = step_to_action(scalars)
        if a:
            actions.append(a)
    return actions

def pddl_validate_and_repair(plan: dict, *, use_planner=False, downward_dir="downward"):
    """
    Returns: (repaired_actions, meta)
      - repaired_actions: safe sequence under the PDDL domain
      - meta: dict with debug info
    """
    original = plan_to_actions(plan)
    repaired = repair_sequence(original)

    meta = {"method": "rule_repair", "original": original}
    if use_planner:
        with tempfile.TemporaryDirectory() as tmp:
            dom = os.path.join(tmp, "domain.pddl")
            prob = os.path.join(tmp, "problem.pddl")
            write_domain(dom)
            write_problem(prob, "seq_check")
            rc, out, err = run_fast_downward(dom, prob, downward_dir=downward_dir)
            meta.update({"planner_rc": rc, "planner_out": out, "planner_err": err, "method": "rule+planner"})
    return repaired, meta
