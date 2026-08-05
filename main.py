import sys
from datetime import datetime

from tabulate import tabulate

from pawpal_system import Owner, Pet, Task, Schedule
from ai_care_planner import AICarePlanner

# Ensure emoji print correctly even on Windows terminals that default to cp1252.
sys.stdout.reconfigure(encoding="utf-8")

PRIORITY_LABELS = {"high": "🔴 High", "medium": "🟡 Medium", "low": "🟢 Low"}
CONFIDENCE_LABELS = {"High": "🟢 High", "Medium": "🟡 Medium", "Low": "🔴 Low"}


def priority_label(priority: str) -> str:
    """Return a priority string with a color-coded emoji."""
    return PRIORITY_LABELS.get(priority, priority)


def status_label(is_completed: bool) -> str:
    """Return a status string with a checkmark or hourglass emoji."""
    return "✅ Done" if is_completed else "⏳ Pending"


def confidence_label(confidence: str) -> str:
    """Return a confidence string with a color-coded emoji."""
    return CONFIDENCE_LABELS.get(confidence, confidence)


def print_table(rows: list, title: str):
    """Print a section title followed by a table (or a friendly empty message)."""
    print(f"\n{title}")
    print("-" * len(title))
    if rows:
        print(tabulate(rows, headers="keys", tablefmt="grid"))
    else:
        print("(nothing to show)")


def print_care_review(report):
    """Print an AICarePlanner CareReviewReport to the console."""
    print("\n🩺 AI Care Review")
    print("-" * 16)

    if not report.available:
        for note in report.notes:
            print(f"ℹ️  {note}")
        return

    print(
        f"Overall schedule score for {report.owner_name}'s pets: "
        f"{report.overall_score} / 10.0  |  "
        f"Confidence: {confidence_label(report.overall_confidence)}"
    )

    for review in report.pet_reviews:
        print(f"\n  {review.pet_name} ({review.species})")
        print(f"  Score: {review.score} / 10.0  |  Confidence: {confidence_label(review.confidence)}")
        if review.fallback_used:
            print("  ⚠️  No species-specific knowledge base entry found; general veterinary guidelines used.")
        print(f"  {review.summary}")
        if review.recommendations:
            print("  Recommendations:")
            for rec in review.recommendations:
                print(f"    - {rec}")

    if report.notes:
        print("\n  Notes:")
        for note in report.notes:
            print(f"    - {note}")


owner = Owner(name="Jordan", age=30)

biscuit = Pet(name="Biscuit", age=3, species="dog", breed="Golden Retriever", owner=owner)
mochi = Pet(name="Mochi", age=2, species="cat", breed="Tabby Cat", owner=owner)

owner.add_pet(biscuit)
owner.add_pet(mochi)

biscuit.add_task(Task(task_type="Feeding", time_to_complete=10, priority="high", pet=biscuit))
mochi.add_task(Task(task_type="Playtime", time_to_complete=20, priority="low", pet=mochi))
mochi.add_task(Task(task_type="Litter box cleaning", time_to_complete=15, priority="medium", pet=mochi))
biscuit.add_task(Task(task_type="Morning walk", time_to_complete=30, priority="high", pet=biscuit))

# Two tasks (different pets) due at the exact same time, to demonstrate conflict detection
same_time = datetime(2026, 7, 8, 8, 0)
biscuit.add_task(Task(task_type="Vet checkup", time_to_complete=30, priority="high", pet=biscuit, due_date=same_time))
mochi.add_task(Task(task_type="Grooming", time_to_complete=30, priority="medium", pet=mochi, due_date=same_time))

# Mark one task complete so filtering has something to show
mochi.tasks[1].mark_complete()

schedule = Schedule(owner=owner, time_available=60)
schedule.create_schedule()

print("=" * 50)
print("🐾  PawPal+ Daily Schedule")
print("=" * 50)

print_table(
    [
        {
            "Pet": t.pet.name,
            "Task": t.task_type,
            "Priority": priority_label(t.priority),
            "Time (min)": t.time_to_complete,
        }
        for t in schedule.scheduled_tasks
    ],
    "📅 Today's Schedule",
)

print_table(
    [
        {"Pet": t.pet.name, "Task": t.task_type, "Time (min)": t.time_to_complete}
        for t in schedule.sort_by_time(owner.get_all_tasks())
    ],
    "⏱️  All Tasks Sorted by Time",
)

print_table(
    [
        {
            "Pet": t.pet.name,
            "Task": t.task_type,
            "Priority": priority_label(t.priority),
            "Time (min)": t.time_to_complete,
        }
        for t in schedule.sort_by_priority(owner.get_all_tasks())
    ],
    "🥇 All Tasks Sorted by Priority (then Time)",
)

print_table(
    [
        {"Pet": t.pet.name, "Task": t.task_type, "Status": status_label(t.is_completed)}
        for t in schedule.filter_tasks(is_completed=True)
    ],
    "✅ Completed Tasks",
)

print_table(
    [
        {
            "Task": t.task_type,
            "Status": status_label(t.is_completed),
            "Due": t.due_date.strftime("%Y-%m-%d"),
        }
        for t in schedule.filter_tasks(pet_name="Mochi")
    ],
    "🐱 Mochi's Tasks",
)

print("\n⚠️  Scheduling Conflicts")
print("-" * 24)
warnings = schedule.find_conflicts()
if warnings:
    for warning in warnings:
        print(f"⚠️  {warning}")
else:
    print("✅ No conflicts found.")

print("\n🕒 Next Available Slot")
print("-" * 22)
next_slot = schedule.next_available_slot()
print(f"You're free again at {next_slot.strftime('%Y-%m-%d %H:%M')}.")

care_report = AICarePlanner().review_schedule(schedule)
print_care_review(care_report)

print("\n💾 Saving Data")
print("-" * 14)
owner.save_to_json()
print("✅ Saved owner, pets, and tasks to data.json")

reloaded_owner = Owner.load_from_json()
print(f"✅ Reloaded '{reloaded_owner.name}' with {len(reloaded_owner.pets)} pet(s) from data.json")
