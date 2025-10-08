# trial_logger.py
import csv, os, time

HEADER = [
    "trial_id","scenario","success","ttc_s","path_m","interventions",
    "collisions","replans","policy_viol","asr_ms","nlp_ms","plan_ms","exec_ms","err_tag"
]

class TrialLogger:
    def __init__(self, csv_path):
        self.csv_path = os.path.expanduser(csv_path)
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if not os.path.exists(self.csv_path) or os.path.getsize(self.csv_path) == 0:
            with open(self.csv_path, "w", newline="") as f:
                csv.writer(f).writerow(HEADER)
        self.reset()

    def reset(self):
        self.trial_id = 0
        self.scenario = ""
        self.t0 = None
        self.path_m = 0.0
        self.interventions = 0
        self.collisions = 0
        self.replans = 0
        self.policy_viol = 0
        self.asr_ms = 0.0
        self.nlp_ms = 0.0
        self.plan_ms = 0.0

    def begin(self, trial_id, scenario, asr_ms=0.0, nlp_ms=0.0, plan_ms=0.0):
        self.reset()
        self.trial_id = int(trial_id)
        self.scenario = str(scenario)
        self.asr_ms = float(asr_ms)
        self.nlp_ms = float(nlp_ms)
        self.plan_ms = float(plan_ms)
        self.t0 = time.time()

    def add_replan(self, n=1):           self.replans += int(n)
    def add_intervention(self, n=1):     self.interventions += int(n)
    def set_collided(self):              self.collisions = 1
    def add_policy_violation(self, n=1): self.policy_viol += int(n)
    def add_path(self, meters):          self.path_m += float(meters)

    def end(self, success=True, err_tag="none"):
        ttc_s = max(0.0, time.time() - self.t0) if self.t0 else 0.0
        row = [
            self.trial_id, self.scenario, int(bool(success)),
            round(ttc_s, 3), round(self.path_m, 3),
            self.interventions, self.collisions, self.replans, self.policy_viol,
            round(self.asr_ms, 1), round(self.nlp_ms, 1), round(self.plan_ms, 1),
            round(ttc_s * 1000.0, 1), str(err_tag)
        ]
        with open(self.csv_path, "a", newline="") as f:
            csv.writer(f).writerow(row)
        return ttc_s
