# AI Interactions Log

## Project AI Workflow Summary

This section documents how AI (Claude) was used across the PawPal+ project, phase by phase.

### Files modified with AI assistance

- `tests/test_pawpal.py` — added new test functions
- `pytest.ini` — created to fix test discovery
- `app.py` — added scheduling display features
- `pawpal_system.py` — added the `next_available_slot()` method
- `main.py` — added a demo of the new feature
- `README.md` — added Features and Demo Walkthrough sections
- `diagrams/uml_final.mmd` — created from the original UML, updated to match final code
- `ai_interactions.md` — this file

### Phase 1: Test planning

- **Asked:** For a test plan covering the most important edge cases for the scheduler (sorting, recurring tasks, conflicts, no tasks, completed tasks, two tasks at the same time), based on `pawpal_system.py` and the existing `tests/test_pawpal.py`.
- **AI completed:** Reviewed the code and returned a written test plan (happy path + edge cases) with no code changes.
- **Manual decision:** Chose to implement only a focused subset of the full plan (sorting, recurrence, conflict detection) rather than every edge case listed, to keep the test suite simple.

### Phase 2: Writing tests

- **Asked:** To add pytest tests for sorting correctness, recurrence logic, and conflict detection, without changing `pawpal_system.py`.
- **AI completed:** Added three new test functions to `tests/test_pawpal.py` and ran `pytest` to confirm all 5 tests passed.

### Phase 3: Fixing a test import error

- **Asked:** To fix a `ModuleNotFoundError: No module named 'pawpal_system'` without changing app logic.
- **AI completed:** Diagnosed the cause (project root not on `sys.path` when pytest is run from certain directories) and added `pytest.ini` with `pythonpath = .`. Verified the fix by running pytest from inside the `tests/` folder.
- **Manual decision:** Confirmed the fix should be config-only — no changes to `pawpal_system.py` or test logic.

### Phase 4: Connecting the UI to the scheduler

- **Asked:** To update `app.py` to use `sort_by_time()`, `filter_tasks()`, and `find_conflicts()`, showing conflicts with `st.warning()`, successes with `st.success()`, and results in `st.table()`, without redesigning the app or backend.
- **AI completed:** Updated the "Generate schedule" button logic in `app.py` to display a sorted-tasks table, a pending-tasks table, and conflict warnings/success messages.

### Phase 5: Reviewing and updating the UML diagram

- **Asked:** First, to identify what was out of date in `diagrams/uml.mmd` compared to the final `pawpal_system.py`; then to apply only those changes to the existing Mermaid code (not redesign it).
- **AI completed:** Listed the specific gaps (missing attributes/methods, an incorrect `create_schedule()` signature, a renamed `tasks` → `scheduled_tasks` attribute), then produced `diagrams/uml_final.mmd` with only those fixes applied, keeping the same classes, relationships, and layout.

### Phase 6: README documentation

- **Asked:** To draft a Features section (sorting, filtering, conflict warnings, recurring tasks, schedule generation) and later a full Demo Walkthrough to replace the placeholder section, both based strictly on the actual implementation.
- **AI completed:** Added a Features section listing each method and its behavior. For the Demo Walkthrough, ran `main.py` to capture real CLI output and used it in the fenced code block, along with a written explanation of the example workflow and scheduler behaviors.

### Phase 7: Adding a new feature (Next Available Slot)

- **Asked:** To add a `next_available_slot()` method to `Schedule` (simple, beginner-friendly, no redesign of existing logic), demo it in `main.py`, and surface it in `app.py`.
- **AI completed:** Added the method (sums `time_to_complete` of `scheduled_tasks` and adds those minutes to `datetime.now()`), added a demo print statement in `main.py`, and displayed the result in the Streamlit UI. Verified with `pytest` and by running `main.py` that nothing else broke.

### Phase 8: Documenting the AI workflow (this file)

- **Asked:** To create a log of the AI workflow across the project.
- **Manual decision:** `ai_interactions.md` already existed as an empty stretch-feature template (Agent Workflow / Prompt Comparison sections below). Chose to append this summary above that template rather than overwrite it or use a different filename.

---

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

<!-- Describe the goal you asked the agent to accomplish -->

**What did the agent do?**

<!-- List the steps the agent took (files edited, commands run, etc.) -->

**What did you have to verify or fix manually?**

<!-- Describe anything the agent got wrong or that required human review -->

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

**Prompt used for both:** "How would you implement the logic for rescheduling weekly recurring tasks in my PawPal+ scheduler while keeping the code simple and beginner-friendly?"

|                       | Option A                                                                                                                                                                                                                                                                                                                                         | Option B                                                                                                                                                                                                                                                                                                                |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Model / tool used** | Claude (this project's assistant)                                                                                                                                                                                                                                                                                                                | ChatGPT                                                                                                                                                                                                                                                                                                                 |
| **Prompt**            | Same prompt as above                                                                                                                                                                                                                                                                                                                             | Same prompt as above                                                                                                                                                                                                                                                                                                    |
| **Response summary**  | Pointed out that weekly rescheduling is already implemented in `Task.mark_complete()`: it spawns a new `Task` with `due_date = datetime.now() + timedelta(weeks=1)` and adds it via `pet.add_task()`. Flagged that this bases the next date on _completion time_, not the original due date, so a late completion pushes the whole series later. | Recommended keeping the logic inside `Task.mark_complete()`, creating a new task with the same info when a weekly task is completed, setting its due date to the **original due date + one week**, adding it back to the pet's task list, and keeping the scheduler itself focused only on scheduling (not recurrence). |
| **What was useful**   | Correctly identified the logic already existed instead of suggesting a duplicate implementation; clearly explained the drift tradeoff of `datetime.now()`-based scheduling.                                                                                                                                                                      | Gave a clean, concrete rule (`original due date + 1 week`) for a fixed weekly cadence, and reinforced good separation of concerns (recurrence stays on `Task`, not `Schedule`).                                                                                                                                         |
| **Problems noticed**  | Didn't propose a fix outright — asked whether a fixed cadence was wanted before suggesting the one-line change.                                                                                                                                                                                                                                  | Assumed the feature needed to be built from scratch and didn't acknowledge that `mark_complete()` already existed with `datetime.now()`-based logic.                                                                                                                                                                    |
| **Decision**          | Used as the basis for understanding the current code and the two possible behaviors (drift vs. fixed cadence).                                                                                                                                                                                                                                   | Considered as a possible fix (`self.due_date + timedelta(weeks=1)`), but not applied — see final decision below.                                                                                                                                                                                                        |

**Which approach did you use in your final implementation and why?**

Neither change was applied. After comparing both responses, I decided to keep the existing `datetime.now() + timedelta(weeks=1)` logic in `Task.mark_complete()` as-is, since it already worked correctly for the project's requirements and I didn't want to introduce a behavior change (fixed cadence vs. drift) without a specific need for it. This comparison was completed to satisfy Challenge 5, not to change the implementation.
