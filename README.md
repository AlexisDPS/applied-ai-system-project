    # PawPal AI Care Planner

    PawPal AI Care Planner is a Python pet-care scheduling application that plans a pet
    owner's daily care tasks and then automatically reviews the generated schedule with
    a specialized AI planning component that scores coverage, flags gaps, and provides veterinarian-toned recommendations grounded in a local knowledge base.

    The project has two parts:

    1. **The scheduler (PawPal+)** — the original project: `Owner`, `Pet`, `Task`, and `Schedule` classes that build, sort, filter, and explain a day's pet-care plan.
    2. **The AI Care Planner extension** — a review layer (`ai_care_planner.py`,
    `guardrails.py`, `retriever.py`, `knowledge/`) that reads an already-built
    schedule and produces an automatic quality review, without changing how the
    schedule itself is built.

    ---

    ## 1. Original Project Description

    **Scenario:** A busy pet owner needs help staying consistent with pet care. They
    want an assistant that can track care tasks (walks, feeding, grooming, litter/tank
    cleaning, vet visits, etc.), take constraints into account (time available and task
    priority), and produce a daily plan.

    **Core classes** (`pawpal_system.py`):

    | Class      | Responsibility |
    |------------|-----------------|
    | `Owner`    | Stores the owner's info, holds a list of `Pet`s, aggregates all tasks across pets, and persists everything to/from `data.json`. |
    | `Pet`      | Stores a pet's name, age, **species**, breed, owner, and its own list of `Task`s. |
    | `Task`     | A single care task: type, duration, priority, frequency, due date, and completion state. Completing a daily/weekly task automatically spawns its next occurrence. |
    | `Schedule` | Builds a day's plan from an owner's pending tasks within a time budget, sorts by time or priority, filters tasks, detects same-time conflicts, and explains the resulting plan. |

    **Implemented scheduler features:**

    - **Sorting** — `sort_by_time()` (shortest first) and `sort_by_priority()`
    (high → medium → low, ties broken by shorter duration).
    - **Schedule generation** — `create_schedule()` greedily fits pending tasks,
    priority-first, into the owner's available time.
    - **Filtering** — `filter_tasks()` by completion status and/or pet name.
    - **Conflict detection** — `find_conflicts()` flags any two tasks due at the exact
    same timestamp.
    - **Recurring tasks** — `Task.mark_complete()` automatically creates the next
    daily/weekly occurrence of a task.
    - **Explanations** — `Schedule.explain()` gives a human-readable reason for each
    scheduled task.
    - **Persistence** — `Owner.save_to_json()` / `Owner.load_from_json()` round-trip
    the owner, pets, and tasks through `data.json`.

    This part of the system is unchanged by the AI extension below — the AI layer only
    *reads* `Schedule` output, it never sorts, filters, or builds a schedule itself.

    ---

    ## 2. AI Extension: The AI Care Planner

    The AI Care Planner adds an automatic review step that runs immediately after a
    schedule is generated, in both the CLI (`main.py`) and the Streamlit app (`app.py`).
    It answers one question in a professional, veterinarian-style tone: **"How well
    does this schedule actually cover each pet's routine care needs, and what should
    the owner add next?"**

    For every pet with tasks, it produces:

    - A **schedule score from 1.0–10.0**
    - A **confidence level** (`High` / `Medium` / `Low`)
    - A short professional **summary**
    - Up to **10 recommendations** for additional or overdue tasks
    - Whether the review had to **fall back** to general veterinary guidance because
    the pet's species has no dedicated knowledge base entry

    If there is nothing to review — no tasks at all, or tasks exist but no schedule has
    been generated — the system **honestly reports that no AI review can be
    generated** instead of fabricating a score.

    ### New files

    | File | Purpose |
    |------|---------|
    | `retriever.py` | `KnowledgeRetriever` — loads species-specific guidance from `knowledge/*.md`, falling back to `veterinary_guidelines.md` for unrecognized species. |
    | `knowledge/*.md` | Local knowledge base: `dog_care.md`, `cat_care.md`, `fish_care.md`, `veterinary_guidelines.md`. |
    | `ai_care_planner.py` | `AICarePlanner` — reads a `Schedule` and produces a `CareReviewReport` (score, confidence, summary, recommendations per pet). |
    | `guardrails.py` | Safety/consistency layer — clamps scores, validates confidence values, caps/deduplicates recommendations, strips medical-diagnosis-style language, and attaches the standing veterinary disclaimer. |
    | `evaluate.py` | Standalone evaluation harness that exercises the AI layer across representative scenarios and asserts its guarantees hold. |

    ---

    ## 3. Architecture Overview

    ```
    Owner / Pet / Task            (pawpal_system.py — unchanged scheduling model)
            │
            ▼
        Schedule                  (pawpal_system.py — builds today's plan)
            │  (read-only)
            ▼
    AICarePlanner.review_schedule(schedule)      (ai_care_planner.py)
            │
            ├─► KnowledgeRetriever.retrieve(species)   (retriever.py)
            │        └─► knowledge/{dog,cat,fish}_care.md
            │            knowledge/veterinary_guidelines.md  (fallback)
            │
            ├─► per-pet scoring, summary, recommendations
            │
            ▼
    guardrails.guard_report(report)             (guardrails.py)
            │   (clamp score, validate confidence, cap/dedupe
            │    recommendations, strip unsafe language, add disclaimer)
            ▼
    CareReviewReport  ──►  rendered in main.py (CLI) and app.py (Streamlit)
    ```

    Key design decisions:

    - **Separation of concerns.** `AICarePlanner` never touches `Schedule`'s sorting,
    filtering, or scheduling logic — it only reads `schedule.scheduled_tasks`,
    `schedule.owner`, and `schedule.find_conflicts()`. All scheduling logic remains
    exactly as originally implemented.
    - **No external AI/API calls.** The specialized AI planning component uses deterministic reasoning over the generated schedule and local knowledge base rather than relying on an external hosted model. This keeps the system fully offline, reproducible, and easy to evaluate — appropriate for a safety-sensitive domain like pet care.
    - **Guardrails are a separate, mandatory pass.** Every report returned to a caller
    has already been through `guardrails.guard_report()`, so all entry points
    (CLI, UI, evaluation script) get the same safety guarantees for free.

    ---

    ## Design Decisions

    Several design decisions shaped the final system:

    - Added support for dogs, cats, and fish through a local knowledge base.
    - Unknown species automatically fall back to general veterinary guidance when no species-specific information is available.
    - The AI review uses each pet's name to provide more personalized feedback.
    - Every AI review includes a schedule score from 1.0–10.0 and a confidence rating (High, Medium, or Low).
    - The AI automatically reviews every generated schedule rather than requiring a separate action from the user.

    ---

    ## 4. Installation

    ```bash
    python -m venv .venv
    source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

    Dependencies (`requirements.txt`): `streamlit`, `pytest`, `tabulate`.

    ---

    ## 5. Usage

    ### Command line

    ```bash
    python main.py
    ```

    Builds a small sample owner with two pets (a dog and a cat), generates today's
    schedule, prints all the existing scheduler views (sorted tasks, conflicts, next
    available slot), then prints the **AI Care Review**, and finally saves/reloads
    `data.json`.

    ### Streamlit app

    ```bash
    streamlit run app.py
    ```

    Add an owner, add pets (with species), add tasks, set the available time, and
    click **Generate schedule**. The scheduler output appears first, followed by a
    **🩺 AI Care Review** section with per-pet scores, confidence, and recommendations.

    ### Tests

    ```bash
    python -m pytest
    ```

    ### AI evaluation harness

    ```bash
    python evaluate.py
    ```

    ---

    ## 6. Reproducible Example

    Running `python main.py` against the sample data (Biscuit the dog, Mochi the cat,
    one overdue vet checkup, and a same-time conflict) produces output like:

    ```text
    🩺 AI Care Review
    ----------------
    Overall schedule score for Jordan's pets: 6.9 / 10.0  |  Confidence: 🟢 High

    Biscuit (dog)
    Score: 5.4 / 10.0  |  Confidence: 🟢 High
    Biscuit's schedule covers 2/3 core care categories (feeding, exercise/enrichment, grooming/habitat) with 2 task(s) planned for today.
    Recommendations:
        - Consider adding a grooming or habitat-cleaning task for Biscuit; see the dog care guidance in the knowledge base.
        - Biscuit's 'Vet checkup' is overdue (was due 2026-07-08 08:00); reschedule it soon.
        - Biscuit's 'Feeding' is overdue (was due 2026-08-04 22:14); reschedule it soon.
        - Biscuit's 'Morning walk' is overdue (was due 2026-08-04 22:14); reschedule it soon.

    Mochi (cat)
    Score: 8.4 / 10.0  |  Confidence: 🟢 High
    Mochi's schedule covers 2/3 core care categories (feeding, exercise/enrichment, grooming/habitat) with 1 task(s) planned for today.
    Recommendations:
        - Consider adding a feeding task for Mochi; see the cat care guidance in the knowledge base.
        - Mochi's 'Grooming' is overdue (was due 2026-07-08 08:00); reschedule it soon.
        - Mochi's 'Playtime' is overdue (was due 2026-08-04 22:14); reschedule it soon.

    Notes:
        - 1 scheduling conflict(s) were detected across pets; review the conflict list before finalizing today's plan.
        - This AI review supports pet care scheduling only. It does not diagnose illness, prescribe treatment, or replace a licensed veterinarian.
    ```

    This example is fully reproducible by running `python main.py` — the sample owner,
    pets, and tasks are hardcoded in the script (only the "overdue" timestamps will
    shift relative to whenever you run it, since they're computed from `datetime.now()`).

    ---

    ## 7. AI Feature Explanation

    `AICarePlanner.review_schedule(schedule)` works in three steps per pet:

    1. **Category coverage.** Each of the pet's tasks is matched against keyword
    groups for three core care categories — `feeding`, `exercise_enrichment`, and
    `grooming_habitat` (e.g. "walk" and "play" match exercise/enrichment; "litter",
    "tank", and "brush" match grooming/habitat). The set of categories actually
    represented is compared against the expected set.

    2. **Scoring.** A pet's score starts at a baseline of 5.0, then:
    - `+1.2` per core category covered (up to `+3.6` for full coverage)
    - `+1.0` if at least one of the pet's tasks made it into today's schedule
    - `-1.0` per high-priority task that is both overdue and unscheduled
    - `-0.5` per additional high-priority task left unscheduled
    The result is clamped to `1.0–10.0` by `guardrails.clamp_score()`.

    3. **Recommendations & confidence.** `KnowledgeRetriever.retrieve(pet.species)`
    looks up `knowledge/{species}_care.md`. Known species (`dog`, `cat`, `fish`) get
    `confidence="High"`; any other species falls back to
    `knowledge/veterinary_guidelines.md` with `confidence="Medium"` and an explicit
    recommendation disclosing the fallback. Missing categories and overdue tasks are
    turned into concrete, pet-name-specific recommendations (e.g. *"Consider adding
    a feeding task for Mochi..."*), capped at 10 by
    `guardrails.enforce_recommendation_limit()`.

    The overall report's confidence is the **lowest** confidence across all pet
    reviews, so one fallback pet appropriately lowers the whole household's confidence
    rating.

    ---

    ## 8. Reliability & Guardrails

    All safety and consistency rules live in `guardrails.py` and are applied to every
    report before it is returned:

    - **Score bounds** — `clamp_score()` guarantees every score is a float in
    `[1.0, 10.0]`, rounded to one decimal, regardless of what the scoring heuristic
    computes.
    - **Confidence validity** — `validate_confidence()` forces any unrecognized value
    down to `"Low"` rather than surfacing an invalid label.
    - **Recommendation limits** — `enforce_recommendation_limit()` deduplicates and
    caps recommendations at 10.
    - **No medical advice** — `sanitize_text()` regex-redacts diagnosis/prescription/
    dosage/treatment-style language (e.g. "diagnose", "administer", "mg/kg") from any
    generated text, replacing it with `[reviewed]`.
    - **Standing disclaimer** — `guard_report()` appends a fixed disclaimer to every
    report: *"This AI review supports pet care scheduling only. It does not diagnose
    illness, prescribe treatment, or replace a licensed veterinarian."*
    - **Honest "no review" path** — if an owner has no tasks, or has tasks but no
    generated schedule, `AICarePlanner` returns `available=False` with an explanatory
    note instead of inventing a score.

    ---

    ## 9. Evaluation Script

    `evaluate.py` is a standalone harness (separate from the pytest suite) that checks
    the AI layer's *behavior*, not the scheduler's. It runs 7 scenarios and 18 checks:

    | Scenario | What it verifies |
    |----------|-------------------|
    | Full care-category coverage (dog) | Valid score/confidence, no false "missing category" recommendations, pet name in summary. |
    | Missing care categories (cat) | Missing categories are recommended, capped at 10, pet name included. |
    | Unknown species fallback | `fallback_used=True`, confidence downgraded to `Medium`, fallback disclosed as a recommendation. |
    | No tasks at all | Report honestly marked unavailable, no pet reviews, explanatory note present. |
    | Tasks exist but no schedule generated | Same honest "unavailable" behavior. |
    | Overdue high-priority task | Overdue task is surfaced in recommendations. |
    | Guardrail language stripping | Medical-sounding terms are redacted from sanitized text. |

    Run it with:

    ```bash
    python evaluate.py
    ```

    Latest run: **18/18 checks passed.**

    ---

    ## 10. Testing Summary

    `tests/test_pawpal.py` covers the core scheduler behaviors with `pytest`:

    - `mark_complete()` correctly flips a task's completion status.
    - Adding a task increases a pet's task count.
    - `sort_by_time()` orders tasks shortest-to-longest.
    - Completing a daily task spawns its next occurrence exactly one day later.
    - `find_conflicts()` correctly flags two different pets' tasks scheduled at the
    same timestamp.

    ```bash
    $ python -m pytest -q
    .....
    5 passed in 0.03s
    ```

    **Confidence level:** 5/5 — all scheduler tests pass, and the AI layer's own
    18-check evaluation harness (`evaluate.py`) also passes in full, covering the score
    range, confidence fallback, recommendation limits, the honest "no review" path, and
    guardrail text sanitization.

    ---

    ## 11. Future Improvements

    - **Richer category detection** — replace keyword matching with a small
    configurable taxonomy per species (e.g. distinguishing "tank cleaning" from
    "water change" for fish) as the knowledge base grows.
    - **Trend-aware scoring** — factor in a pet's task history over multiple days
    (e.g. consistently skipped categories) rather than scoring a single day's
    schedule in isolation.
    - **Owner-level recommendations** — surface cross-pet suggestions (e.g. balancing
    time allocation when one pet's tasks crowd out another's).
    - **Configurable knowledge base** — allow additional species files to be dropped
    into `knowledge/` and picked up by `KnowledgeRetriever` without code changes
    (currently the dog/cat/fish mapping is hardcoded in `retriever.py`).
    - **UI surfacing of guardrail redactions** — currently sanitized text silently
    replaces blocked terms with `[reviewed]`; a future version could log when
    redaction occurred for transparency during development.
