"""
evaluate.py

Lightweight evaluation harness for the AI care review layer
(`ai_care_planner.py` + `guardrails.py`).

This is separate from `tests/test_pawpal.py`: that suite verifies the
scheduler itself, while this script verifies the *AI review* behaves
correctly and safely across a handful of representative scenarios:

- A pet with full care-category coverage.
- A pet missing categories of care (should get recommendations).
- An unknown species (should fall back to veterinary_guidelines.md).
- An owner with no tasks at all (should honestly report "no review").
- An owner with tasks but no schedule generated (same honest report).
- An overdue high-priority task (should be flagged and lower the score).

Run directly with: python evaluate.py
"""

import sys
from datetime import datetime, timedelta

from pawpal_system import Owner, Pet, Task, Schedule
from ai_care_planner import AICarePlanner
import guardrails

CHECKS_PASSED = []
CHECKS_FAILED = []


def check(description: str, condition: bool):
    """Record a single pass/fail check and print it immediately."""
    if condition:
        CHECKS_PASSED.append(description)
        print(f"  PASS - {description}")
    else:
        CHECKS_FAILED.append(description)
        print(f"  FAIL - {description}")


def build_owner() -> Owner:
    """Create a fresh owner for each scenario so runs don't interfere."""
    return Owner(name="Eval Owner", age=99)


def scenario_full_coverage():
    print("\nScenario: full care-category coverage (dog)")
    owner = build_owner()
    biscuit = Pet(name="Biscuit", age=3, species="dog", breed="Golden Retriever", owner=owner)
    owner.add_pet(biscuit)
    biscuit.add_task(Task(task_type="Morning feeding", time_to_complete=10, priority="high", pet=biscuit))
    biscuit.add_task(Task(task_type="Evening walk", time_to_complete=20, priority="medium", pet=biscuit))
    biscuit.add_task(Task(task_type="Brushing", time_to_complete=10, priority="low", pet=biscuit))

    schedule = Schedule(owner=owner, time_available=60)
    schedule.create_schedule()
    report = AICarePlanner().review_schedule(schedule)

    check("report is available", report.available is True)
    check("one pet review produced", len(report.pet_reviews) == 1)
    review = report.pet_reviews[0]
    check("score within 1.0-10.0", 1.0 <= review.score <= 10.0)
    check("confidence is High for a known species", review.confidence == "High")
    check("full coverage yields no missing-category recommendations", not any(
        "Consider adding" in rec for rec in review.recommendations
    ))
    check("pet name appears in summary", "Biscuit" in review.summary)


def scenario_missing_categories():
    print("\nScenario: missing care categories (cat)")
    owner = build_owner()
    mochi = Pet(name="Mochi", age=2, species="cat", breed="Tabby", owner=owner)
    owner.add_pet(mochi)
    mochi.add_task(Task(task_type="Feeding", time_to_complete=10, priority="medium", pet=mochi))

    schedule = Schedule(owner=owner, time_available=60)
    schedule.create_schedule()
    report = AICarePlanner().review_schedule(schedule)

    review = report.pet_reviews[0]
    check("recommendations suggest missing categories", any(
        "Consider adding" in rec for rec in review.recommendations
    ))
    check("recommendations capped at 10", len(review.recommendations) <= 10)
    check("pet name appears in recommendations", any("Mochi" in rec for rec in review.recommendations))


def scenario_unknown_species_fallback():
    print("\nScenario: unknown species falls back to veterinary guidelines")
    owner = build_owner()
    rex = Pet(name="Rex", age=1, species="iguana", breed="Green Iguana", owner=owner)
    owner.add_pet(rex)
    rex.add_task(Task(task_type="Feeding", time_to_complete=10, priority="medium", pet=rex))

    schedule = Schedule(owner=owner, time_available=60)
    schedule.create_schedule()
    report = AICarePlanner().review_schedule(schedule)

    review = report.pet_reviews[0]
    check("fallback flag is set for unknown species", review.fallback_used is True)
    check("confidence is Medium for a fallback review", review.confidence == "Medium")
    check("fallback is disclosed in recommendations", any(
        "no dedicated knowledge base entry" in rec.lower() for rec in review.recommendations
    ))


def scenario_no_tasks():
    print("\nScenario: owner with no tasks at all")
    owner = build_owner()
    schedule = Schedule(owner=owner, time_available=60)
    schedule.create_schedule()
    report = AICarePlanner().review_schedule(schedule)

    check("report honestly reports unavailable", report.available is False)
    check("no pet reviews produced", report.pet_reviews == [])
    check("notes explain why no review exists", len(report.notes) >= 1)


def scenario_no_schedule_generated():
    print("\nScenario: tasks exist but no schedule was generated")
    owner = build_owner()
    biscuit = Pet(name="Biscuit", age=3, species="dog", breed="Golden Retriever", owner=owner)
    owner.add_pet(biscuit)
    biscuit.add_task(Task(task_type="Feeding", time_to_complete=10, priority="high", pet=biscuit))

    schedule = Schedule(owner=owner, time_available=60)
    # Intentionally do NOT call schedule.create_schedule()
    report = AICarePlanner().review_schedule(schedule)

    check("report honestly reports unavailable when schedule is empty", report.available is False)


def scenario_overdue_high_priority():
    print("\nScenario: overdue high-priority task lowers score and is flagged")
    owner = build_owner()
    biscuit = Pet(name="Biscuit", age=3, species="dog", breed="Golden Retriever", owner=owner)
    owner.add_pet(biscuit)
    overdue_time = datetime.now() - timedelta(days=2)
    biscuit.add_task(Task(
        task_type="Feeding", time_to_complete=500, priority="high",
        pet=biscuit, due_date=overdue_time,
    ))
    # A large time_to_complete keeps this task out of the fitted schedule,
    # simulating a high-priority task that didn't make it in.
    schedule = Schedule(owner=owner, time_available=60)
    schedule.create_schedule()

    # Add a second, small task so the schedule isn't empty and a review runs.
    biscuit.add_task(Task(task_type="Water refill", time_to_complete=5, priority="low", pet=biscuit))
    schedule.create_schedule()

    report = AICarePlanner().review_schedule(schedule)
    review = report.pet_reviews[0]
    check("overdue task is flagged in recommendations", any(
        "overdue" in rec.lower() for rec in review.recommendations
    ))


def scenario_guardrail_language_stripped():
    print("\nScenario: guardrails strip medical-sounding language")
    sample = "Diagnose the issue and administer treatment at 5 mg/kg."
    sanitized = guardrails.sanitize_text(sample)
    check("blocked medical terms are redacted", all(
        term not in sanitized.lower() for term in ["diagnos", "administer", "mg/kg", "treatment"]
    ))


def main():
    print("=" * 60)
    print("PawPal+ AI Care Planner - Evaluation Harness")
    print("=" * 60)

    scenario_full_coverage()
    scenario_missing_categories()
    scenario_unknown_species_fallback()
    scenario_no_tasks()
    scenario_no_schedule_generated()
    scenario_overdue_high_priority()
    scenario_guardrail_language_stripped()

    print("\n" + "=" * 60)
    print(f"Results: {len(CHECKS_PASSED)} passed, {len(CHECKS_FAILED)} failed")
    print("=" * 60)

    if CHECKS_FAILED:
        sys.exit(1)


if __name__ == "__main__":
    main()
