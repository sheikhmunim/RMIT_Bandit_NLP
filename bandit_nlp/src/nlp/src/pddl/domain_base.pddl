(define (domain base_actions)
  (:requirements :strips)

  ;; ---------- Predicates ----------
  (:predicates
    (stopped)        ;; robot is stopped
    (did_forward)    ;; executed move-forward
    (did_backward)   ;; executed move-backward
    (did_turn_left)  ;; executed turn-left
    (did_turn_right) ;; executed turn-right
    (did_spin)       ;; executed spin
   
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

  (:action turn-left
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (did_turn_left)
    )
  )

  (:action turn-right
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (did_turn_right)
    )
  )

  (:action spin
    :precondition (stopped)
    :effect (and
      (not (stopped))
      (did_spin)
    )
  )

  (:action stop
    :precondition (not (stopped))
    :effect (stopped)
  )
)

