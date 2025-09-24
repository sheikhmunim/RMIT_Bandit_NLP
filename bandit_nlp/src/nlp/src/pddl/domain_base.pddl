(define (domain base_actions)
  (:requirements :strips)

  ;; ---------- Predicates ----------
  (:predicates
    (stopped)        ;; robot is stopped
    (did_forward)    ;; has executed move-forward at least once
    (did_backward)   ;; has executed move-backward at least once
  )

  ;; ---------- Actions ----------
  (:action move-forward
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (did_forward)
    )
  )

  (:action move-backward
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (did_backward)
    )
  )

  (:action stop
    :precondition (not (stopped))
    :effect (stopped)
  )
)
