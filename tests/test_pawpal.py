from datetime import datetime, timedelta

from pawpal_system import Owner, Pet, Task, Schedule


def test_mark_complete_changes_status():
    owner = Owner(name="Jordan", age=30)
    pet = Pet(
    name="Biscuit",
    age=3,
    species="dog",
    breed="Golden Retriever",
    owner=owner,
)
    task = Task(task_type="Morning walk", time_to_complete=30, priority="high", pet=pet)

    assert task.is_completed is False

    task.mark_complete()

    assert task.is_completed is True


def test_add_task_increases_pet_task_count():
    owner = Owner(name="Jordan", age=30)
    pet = Pet(
    name="Biscuit",
    age=3,
    species="dog",
    breed="Golden Retriever",
    owner=owner,
)
    task = Task(task_type="Feeding", time_to_complete=10, priority="high", pet=pet)

    assert len(pet.tasks) == 0

    pet.add_task(task)

    assert len(pet.tasks) == 1


def test_sort_by_time_orders_tasks_shortest_first():
    owner = Owner(name="Jordan", age=30)
    pet = Pet(
    name="Biscuit",
    age=3,
    species="dog",
    breed="Golden Retriever",
    owner=owner,
)

    long_task = Task(task_type="Walk", time_to_complete=30, priority="high", pet=pet)
    short_task = Task(task_type="Feeding", time_to_complete=10, priority="high", pet=pet)
    medium_task = Task(task_type="Playtime", time_to_complete=20, priority="low", pet=pet)

    schedule = Schedule(owner=owner, time_available=60)
    sorted_tasks = schedule.sort_by_time([long_task, short_task, medium_task])

    assert [task.task_type for task in sorted_tasks] == ["Feeding", "Playtime", "Walk"]


def test_mark_complete_on_daily_task_creates_next_day_task():
    owner = Owner(name="Jordan", age=30)
    pet = Pet(
    name="Biscuit",
    age=3,
    species="dog",
    breed="Golden Retriever",
    owner=owner,
)
    task = Task(
        task_type="Feeding",
        time_to_complete=10,
        priority="high",
        pet=pet,
        frequency="daily",
    )
    pet.add_task(task)

    assert len(pet.tasks) == 1

    task.mark_complete()

    assert len(pet.tasks) == 2

    new_task = pet.tasks[1]
    assert new_task.is_completed is False
    assert new_task.task_type == "Feeding"

    expected_due_date = datetime.now() + timedelta(days=1)
    assert new_task.due_date.date() == expected_due_date.date()


def test_find_conflicts_flags_tasks_at_the_same_time():
    owner = Owner(name="Jordan", age=30)
    biscuit = Pet(name="Biscuit", age=3, species="dog", breed="Golden Retriever", owner=owner)
    mochi = Pet(name="Mochi", age=2, species="cat", breed="Tabby Cat", owner=owner)
    owner.add_pet(biscuit)
    owner.add_pet(mochi)

    same_time = datetime(2026, 7, 8, 8, 0)
    task_a = Task(
        task_type="Vet checkup",
        time_to_complete=30,
        priority="high",
        pet=biscuit,
        due_date=same_time,
    )
    task_b = Task(
        task_type="Grooming",
        time_to_complete=30,
        priority="medium",
        pet=mochi,
        due_date=same_time,
    )
    biscuit.add_task(task_a)
    mochi.add_task(task_b)

    schedule = Schedule(owner=owner, time_available=60)
    warnings = schedule.find_conflicts()

    assert len(warnings) == 1
    assert "Biscuit" in warnings[0]
    assert "Mochi" in warnings[0]
