# Operator handoff pilot

This exercise compares recovery of an already-prepared candidate using manual Git plus notes and managed recovery. It measures capture through verification. Completing new code after handoff is a separate question.

Participation is voluntary. Use a disposable local checkout, avoid any personal or job-related code, and keep the receipt local unless you separately agree to share it. The receipt contains the sequence, case, timing, and grade. It carries no name, owner credential, or terminal transcript.

## Prepare

From the study repository, create two distinct tasks using the public reference changes. Across participants, assign sequences 0, 1, 2, and 3 in rotation. Sequences vary both arm order and case assignment. Follow the order printed during preparation.

```sh
study_root="$(mktemp -d /tmp/continuity-operator.XXXXXX)/exercise"
python -m evals.operator_pilot prepare "$study_root" --sequence 0
```

Review both procedures before starting the first arm. Work without AI assistance on either arm. Use the supplied procedure or equivalent Git and CLI steps. Mark each boundary as it happens. Cap each arm at four minutes and preserve any partial result by making a receipt, including if you withdraw. Use a stopwatch that you pause during command waits if you choose to report active time separately.

## Perform each arm

Set `arm` to the printed arm name. Let `$study_root/$arm` be your initial worktree and `$study_root/$arm-restored` your replacement. The selected file is `continuity-eval-note.txt`. Run the phase commands from the study repository.

```sh
python -m evals.operator_pilot mark "$study_root" --arm "$arm" --phase start
```

- **Manual.** Save a binary patch with `git diff --binary HEAD` and explicitly copy the selected note out of the initial worktree. For restore, use `git worktree add --detach` against its parent commit, apply the patch, and copy the note into the replacement.
- **Managed.** Start a task, checkpoint it with `--include continuity-eval-note.txt`, and use `continue --into` to restore into the replacement. Use the same note. Keep the owner token local.

Mark `captured` when you have stored the patch plus note or the checkpoint. Mark `restored` when the replacement is ready. Inspect the files and run the case check if desired using `python /absolute/path/to/study/evals/check_case.py CASE` from inside the replacement. Return to the study repository to mark `finish`. The instrument independently grades the files and behavior at that point.

```sh
python -m evals.operator_pilot mark "$study_root" --arm "$arm" --phase captured
python -m evals.operator_pilot mark "$study_root" --arm "$arm" --phase restored
python -m evals.operator_pilot mark "$study_root" --arm "$arm" --phase finish
python -m evals.operator_pilot receipt "$study_root" --output "$study_root/receipt.json"
```

Add `--active-seconds NUMBER` at the finish mark only if you separately measured active time. Each phase elapsed value includes interaction and command waits. The receipt records an unfinished arm explicitly. A pilot with one participant gives descriptive feedback. Comparisons require multiple participants and counterbalanced assignments.
