# Model Card

## Project Overview

PawPal AI Care Planner is a Python pet-care scheduling application. It combines
an existing rule-based scheduler (`Owner`, `Pet`, `Task`, `Schedule` in
`pawpal_system.py`) with a specialized AI planning component that evaluates schedules using deterministic reasoning and a local knowledge base (ai_care_planner.py). The component automatically reviews every schedule the scheduler produces. After a
schedule is generated — in either the command-line app (`main.py`) or the
Streamlit app (`app.py`) — the AI component reads that schedule and returns a
professional, veterinarian-toned review for each pet: a numeric schedule score,
a confidence level, a short summary, and a list of concrete recommendations
grounded in a local knowledge base. The AI component never builds, sorts, or
modifies the schedule itself; it only evaluates the output the scheduler already
produced.

## Intended Use

This tool is intended for individual pet owners who want help staying on top of
routine care tasks (feeding, exercise/enrichment, grooming, and habitat
cleaning) for dogs, cats, and fish. It is meant to be used as a **scheduling and
consistency aid** — surfacing gaps in a day's plan and suggesting what to add
next — not as a source of medical guidance. It is appropriate for personal or
educational use by pet owners, students, or developers exploring applied AI
patterns on top of a deterministic scheduling system. It is not intended for
veterinary clinics, breeders, or any setting where actual health decisions need
to be made about an animal.

## AI Component

The AI component is implemented in `ai_care_planner.py`, `retriever.py`, and
`guardrails.py`, and consists of four parts:

- **Specialized AI planning component.** `AICarePlanner.review_schedule()`
  inspects an already-built `Schedule` object per pet. It uses keyword matching
  to detect which core care categories (`feeding`, `exercise_enrichment`,
  `grooming_habitat`) are represented among a pet's tasks, and checks whether
  high-priority tasks are overdue or were left out of today's schedule. This is
  deterministic, rule-based reasoning — not a hosted or trained machine learning
  model.
- **Knowledge retrieval.** `KnowledgeRetriever.retrieve(species)` (in
  `retriever.py`) looks up a species-specific Markdown file in `knowledge/`. Dogs,
  cats, and fish each have a dedicated file and are retrieved with `High`
  confidence. Any other species automatically falls back to
  `veterinary_guidelines.md` with `Medium` confidence, and the fallback is
  disclosed to the user as a recommendation.
- **Schedule scoring.** Each pet's review includes a schedule score from
  **1.0–10.0**, computed from a baseline plus rewards for care-category coverage
  and having tasks fit into today's schedule, minus penalties for overdue or
  unscheduled high-priority tasks. The overall report score is the average of all
  pet scores.
- **Confidence levels.** Each pet review carries a confidence level of `High`,
  `Medium`, or `Low`, drawn from the knowledge retrieval result. The report's
  overall confidence is the lowest confidence among all pet reviews, so a
  fallback species pulls the whole report's confidence down.
- **Guardrails.** Every report is passed through `guardrails.guard_report()`
  before being returned, which clamps scores to `1.0–10.0`, validates confidence
  values, deduplicates and caps recommendations at 10, strips diagnosis/
  prescription/dosage-style language from generated text, and appends a fixed
  veterinary disclaimer.

## Data Sources

The AI component's knowledge comes entirely from a local, static knowledge base
in the `knowledge/` folder:

- **`dog_care.md`** — routine care guidance for dogs (feeding, exercise,
  grooming, safety).
- **`cat_care.md`** — routine care guidance for cats (feeding, enrichment,
  litter box and grooming, safety).
- **`fish_care.md`** — routine care guidance for fish (feeding, water quality,
  temperature stability, tank maintenance).
- **`veterinary_guidelines.md`** — species-neutral safety guidance, used as the
  fallback source for any species without a dedicated file, and used to remind
  users this tool does not replace a licensed veterinarian.

These files are read directly from disk by `KnowledgeRetriever._read_file()`.
There is no external API call, web lookup, or generative model involved in
producing this content — the knowledge base is fixed at the time the project was
authored.

## Limitations

- **Deterministic reasoning.** The AI component uses fixed keyword matching and
  a fixed scoring formula. It does not learn from data, adapt over time, or
  understand task descriptions beyond simple substring matches (e.g. a task
  titled "Pack for the vet trip" could be miscategorized because it contains
  "vet").
- **Only three species have dedicated knowledge.** Only `dog`, `cat`, and `fish`
  map to a species-specific file in `retriever.py`. Every other species (e.g.
  birds, reptiles, small mammals) falls back to the general veterinary
  guidelines file and receives a lower confidence rating.
- **Not a veterinary diagnostic tool.** The system does not assess an animal's
  health, interpret symptoms, or provide treatment guidance. It only evaluates
  whether a _schedule_ covers expected categories of routine care.
- **Recommendations depend entirely on the tasks provided.** If an owner never
  enters a task for a category (e.g. never logs a grooming task), the AI
  component cannot infer that grooming happens elsewhere — it can only reason
  over the data it is given.
- **No review without a schedule.** If an owner has no tasks, or has tasks but
  has not generated a schedule, the AI component does not produce a score; it
  reports that no review is available.

## Biases

- **Incomplete knowledge files bias the fallback path.** Because only three
  species have dedicated `knowledge/*.md` entries, owners of any other species
  are systematically routed to generic guidance and a `Medium` confidence
  rating, regardless of how well their actual schedule covers that pet's needs.
  This is a structural bias in coverage, not a bias in the scoring logic itself.
- **Keyword-based category detection can misclassify tasks.** The heuristic in
  `AICarePlanner._categories_present()` matches on a fixed, small set of English
  keywords per category (e.g. "walk", "play", "groom", "litter"). Tasks named
  with different wording, abbreviations, or a language other than English will
  not be recognized as covering a category, which can understate a pet's actual
  score even if the owner is providing good care.
- **Scoring weights are hand-chosen, not empirically validated.** The point
  values in `AICarePlanner._score_pet()` (e.g. `+1.2` per category, `-1.0` per
  overdue high-priority task) were set by design judgment, not derived from any
  study of what "good" pet care scheduling looks like. Different weighting could
  produce meaningfully different scores for the same schedule.

## Misuse Prevention

All safety-relevant behavior is centralized in `guardrails.py` and applied to
every report before it reaches a user:

- `sanitize_text()` regex-redacts language that would read as diagnosis,
  prescription, dosage, or treatment advice (e.g. "diagnose," "administer,"
  "mg/kg," "treatment"), replacing matches with `[reviewed]`.
- `clamp_score()` and `validate_confidence()` guarantee that even if the scoring
  logic produces an out-of-range or unexpected value, the output shown to the
  user is always a valid 1.0–10.0 score and a valid High/Medium/Low confidence
  level.
- `enforce_recommendation_limit()` deduplicates and caps recommendations at 10,
  preventing runaway or repetitive output.
- Every report ends with a fixed disclaimer: _"This AI review supports pet care
  scheduling only. It does not diagnose illness, prescribe treatment, or replace
  a licensed veterinarian."_
- When there is nothing to review, `AICarePlanner` returns an explicit
  "unavailable" result with an explanatory note rather than fabricating a score
  or recommendation.

## Testing

- **`python -m pytest`** — 5 tests passing. `tests/test_pawpal.py` verifies core
  scheduler behavior: marking tasks complete, adding tasks to a pet, sorting
  tasks by time, recurring daily task generation, and same-time conflict
  detection.
- **`python evaluate.py`** — 18 evaluation checks passing. This standalone
  harness verifies the AI component's behavior specifically: full
  category-coverage scoring, missing-category recommendations, unknown-species
  fallback and confidence downgrade, the honest "no review available" path (no
  tasks, and tasks with no schedule generated), overdue-task flagging, and
  guardrail text redaction.

## AI Collaboration Reflection

- **How AI helped during development.** An AI assistant was used to design and
  implement the AI Care Planner extension (`ai_care_planner.py`,
  `guardrails.py`, `evaluate.py`) on top of the existing scheduler, and to write
  the accompanying documentation (`README.md`, this model card). It also helped
  trace through `pawpal_system.py` and `retriever.py` first, so the new code
  would reuse the existing `Schedule` class rather than duplicating its logic.
- **One AI suggestion that was useful.** Centralizing all safety behavior
  (score clamping, confidence validation, recommendation limits, language
  redaction, disclaimer) into a single `guardrails.py` module, applied once via
  `guard_report()`, meant every entry point — the CLI, the Streamlit app, and
  the evaluation script — automatically inherited the same guarantees instead of
  needing the checks re-implemented in each place.
- **One AI suggestion that required correction.** An early version of the
  scoring logic checked whether a task was already scheduled using Python's
  `in` operator directly on `Task` objects. Because `Task` and `Pet` are
  dataclasses with auto-generated equality that reference each other (a task
  holds its pet, and a pet holds a list of tasks), this risked deep, expensive
  equality comparisons. It was corrected to compare tasks by object identity
  (`id()`) instead, which is both correct and cheap for this use case.
- **One thing learned while building the project.** Keeping the AI layer strictly
  read-only with respect to the scheduler — never sorting, filtering, or
  rebuilding tasks itself — made the system much easier to reason about and test
  independently: `evaluate.py` could exercise the AI component's scoring and
  guardrail behavior in isolation without needing to re-verify scheduling logic
  that `tests/test_pawpal.py` already covers.

## Future Improvements

- Replace fixed keyword matching with a small, configurable taxonomy per
  species so task categorization is easier to extend as the knowledge base
  grows.
- Score a pet's care trend across multiple days rather than a single day's
  schedule in isolation.
- Surface cross-pet, owner-level recommendations when one pet's tasks are
  crowding out another's available time.
- Make the species-to-knowledge-file mapping in `retriever.py` configurable so
  new species files can be added to `knowledge/` without a code change.
- Log when `guardrails.sanitize_text()` redacts content, so redactions are
  visible during development rather than silent.
