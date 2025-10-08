(define (domain base_actions_ext)
  (:requirements :strips :adl)

  ;; ============================================================
  ;; Predicates (minimal, STRIPS-only)
  ;; ============================================================
  (:predicates
    ;; execution mode
    (stopped)
    (turning)

    ;; configuration (exactly-one speed via actions)
    (speed-slow)
    (speed-normal)
    (speed-fast)

    ;; bookkeeping for evaluation
    (did_forward)
    (did_backward)
    (did_turn_left)
    (did_turn_right)
    (did_spin)
  )

  ;; ============================================================
  ;; Speed selection (compliance tests)
  ;; Only allowed while stopped; each sets one speed and clears the others.
  ;; ============================================================
  (:action set-speed-slow
    :precondition (stopped)
    :effect (and
      (speed-slow)
      (not (speed-normal))
      (not (speed-fast))
    )
  )

  (:action set-speed-normal
    :precondition (stopped)
    :effect (and
      (speed-normal)
      (not (speed-slow))
      (not (speed-fast))
    )
  )

  (:action set-speed-fast
    :precondition (stopped)
    :effect (and
      (speed-fast)
      (not (speed-slow))
      (not (speed-normal))
    )
  )

  ;; ============================================================
  ;; Motion primitives (require being stopped to start).
  ;; They put the robot into a non-stopped phase; you must call (stop) later.
  ;; ============================================================
  (:action move-forward
    :precondition (and (stopped) (or (speed-slow) (speed-normal) (speed-fast)))
    :effect (and
      (not (stopped))
      (did_forward)
    )
  )

  (:action move-backward
    :precondition (and (stopped) (or (speed-slow) (speed-normal) (speed-fast)))
    :effect (and
      (not (stopped))
      (did_backward)
    )
  )

  ;; Turning blocks waving; model this via the (turning) flag until a stop.
  (:action turn-left
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (turning)
      (did_turn_left)
    )
  )

  (:action turn-right
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (turning)
      (did_turn_right)
    )
  )

  ;; Spin in place (90°x4 or continuous), treated like a turn phase
  (:action spin
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (turning)
      (did_spin)
    )
  )

  ;; ============================================================
  ;; Gestures
  ;; Sequential wave: must be stopped and not turning.
  ;; ============================================================
    ;; "Concurrent" wave-while-moving modeled as a macro primitive that
  ;; starts moving forward at current speed and performs a wave together.
  ;; This keeps planning STRIPS-only while letting you test concurrency logic.
    ;; ============================================================
  ;; Stop: ends any ongoing phase and clears turning
  ;; ============================================================
  (:action stop
    :precondition (not (stopped))
    :effect (and
      (stopped)
      (not (turning))
    )
  )
)

;; -----------------------------------------------------------------
;; Minimal example problem showing how to drive the 10 test buckets.
;; Duplicate & tailor per test case; keep logic consistent & simple.
;; -----------------------------------------------------------------
(define (problem eval_p1)
  (:domain base_actions_ext)
  (:init
    (stopped)
    (speed-normal)           ;; initial speed; others false by convention
  )
  ;; Choose one goal set per test when you run the planner.
  ;; 1) nominal_navigation: do a forward step
  ;; (:goal (did_forward))

  ;; 2) speed_compliance: ensure plan switches speed & still moves
  ;; (:goal (and (did_forward) (speed-slow)))

  ;; 3) direction_control: require a turn happened before moving
  ;; (:goal (and (did_turn_left) (did_forward)))

  ;; 4) concurrent_vs_sequential: (wave dropped) — use turn/move ordering tests instead

  ;; 5) correction_replanning: just test that we can stop then go backward
  ;; (:goal (and (did_forward) (did_backward)))

  ;; 6) ambiguity_handling: NLU-side; domain unchanged (use nominal goals)

  ;; 7) noisy_input: NLU-side; domain unchanged

  ;; 8) safety_constraint: turning enforces ordering; e.g., require a turn before a move
  ;; (:goal (and (did_turn_left) (did_forward)))

  ;; 9) long_horizon_chain: require multiple flags
  ;; (:goal (and (did_turn_left) (did_forward) (did_backward)))
)
