import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

DEFAULT_DATA_FILE = "data.json"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


class Owner:
    def __init__(self, name: str, age: int):
        self.name = name
        self.age = age
        self.pets: List["Pet"] = []

    def add_pet(self, pet: "Pet"):
        """Add a pet to this owner's list of pets."""
        self.pets.append(pet)

    def get_all_tasks(self) -> List["Task"]:
        """Return a combined list of tasks from all of this owner's pets."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks

    def update_info(self):
        """Update the owner's stored information."""
        pass

    def save_to_json(self, filepath: str = DEFAULT_DATA_FILE):
        """Save this owner, their pets, and all tasks to a JSON file."""
        data = {
            "name": self.name,
            "age": self.age,
            "pets": [
                {
                    "name": pet.name,
                    "age": pet.age,
                    "species": pet.species,
                    "breed": pet.breed,
                    "tasks": [
                        {
                            "task_type": task.task_type,
                            "time_to_complete": task.time_to_complete,
                            "priority": task.priority,
                            "frequency": task.frequency,
                            "is_completed": task.is_completed,
                            "due_date": task.due_date.isoformat(),
                        }
                        for task in pet.tasks
                    ],
                }
                for pet in self.pets
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_from_json(filepath: str = DEFAULT_DATA_FILE) -> "Owner":
        """Load an owner, their pets, and all tasks back from a JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        owner = Owner(name=data["name"], age=data["age"])
        for pet_data in data["pets"]:
            pet = Pet(
    name=pet_data["name"],
    age=pet_data["age"],
    species=pet_data.get("species", "other"),
    breed=pet_data["breed"],
    owner=owner,
    )
            
            owner.add_pet(pet)
            for task_data in pet_data["tasks"]:
                task = Task(
                    task_type=task_data["task_type"],
                    time_to_complete=task_data["time_to_complete"],
                    priority=task_data["priority"],
                    pet=pet,
                    frequency=task_data["frequency"],
                    is_completed=task_data["is_completed"],
                    due_date=datetime.fromisoformat(task_data["due_date"]),
                )
                pet.add_task(task)
        return owner


@dataclass
class Pet:
    name: str
    age: int
    species: str
    breed: str
    owner: Owner
    tasks: List["Task"] = field(default_factory=list)

    def add_task(self, task: "Task"):
        """Add a task to this pet's list of tasks."""
        self.tasks.append(task)

    def update_info(self):
        """Update the pet's stored information."""
        pass


@dataclass
class Task:
    task_type: str
    time_to_complete: int
    priority: str
    pet: Pet
    frequency: str = "daily"
    is_completed: bool = False
    due_date: datetime = field(default_factory=datetime.now)

    def change_priority(self, new_priority: str):
        """Update this task's priority level."""
        self.priority = new_priority

    def mark_complete(self):
        """Mark this task as completed. Daily/weekly tasks spawn their next occurrence."""
        self.is_completed = True

        if self.frequency in ("daily", "weekly"):
            today = datetime.now()
            if self.frequency == "daily":
                next_due_date = today + timedelta(days=1)
            else:
                next_due_date = today + timedelta(weeks=1)

            next_task = Task(
                task_type=self.task_type,
                time_to_complete=self.time_to_complete,
                priority=self.priority,
                pet=self.pet,
                frequency=self.frequency,
                is_completed=False,
                due_date=next_due_date,
            )
            self.pet.add_task(next_task)


class Schedule:
    def __init__(self, owner: Owner, time_available: int):
        self.owner = owner
        self.time_available = time_available
        self.scheduled_tasks: List[Task] = []

    def sort_by_time(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by how long they take to complete, shortest first."""
        return sorted(tasks, key=lambda task: task.time_to_complete)

    def sort_by_priority(self, tasks: List[Task]) -> List[Task]:
        """Sort tasks by priority (high, then medium, then low). Ties go to the shorter task."""
        return sorted(
            tasks,
            key=lambda task: (PRIORITY_ORDER.get(task.priority, len(PRIORITY_ORDER)), task.time_to_complete),
        )

    def create_schedule(self):
        """Build the day's schedule from the owner's pending tasks within the available time."""
        all_tasks = self.owner.get_all_tasks()
        pending_tasks = [task for task in all_tasks if not task.is_completed]

        sorted_tasks = self.sort_by_priority(pending_tasks)

        self.scheduled_tasks = []
        remaining_time = self.time_available
        for task in sorted_tasks:
            if task.time_to_complete <= remaining_time:
                self.scheduled_tasks.append(task)
                remaining_time -= task.time_to_complete

        return self.scheduled_tasks

    def filter_tasks(self, is_completed: bool = None, pet_name: str = None) -> List[Task]:
        """Filter the owner's tasks by completion status and/or pet name."""
        tasks = self.owner.get_all_tasks()

        if is_completed is not None:
            tasks = [task for task in tasks if task.is_completed == is_completed]

        if pet_name is not None:
            tasks = [task for task in tasks if task.pet.name == pet_name]

        return tasks

    def find_conflicts(self) -> List[str]:
        """Check for tasks scheduled at the same time and return a warning for each conflict found."""
        tasks = self.owner.get_all_tasks()
        warnings = []

        for i in range(len(tasks)):
            for j in range(i + 1, len(tasks)):
                task_a = tasks[i]
                task_b = tasks[j]
                if task_a.due_date == task_b.due_date:
                    when = task_a.due_date.strftime("%Y-%m-%d %H:%M")
                    warnings.append(
                        f"Warning: {task_a.pet.name}'s '{task_a.task_type}' and "
                        f"{task_b.pet.name}'s '{task_b.task_type}' are both scheduled at {when}."
                    )

        return warnings

    def update_schedule(self):
        """Rebuild the schedule to reflect any changes to tasks."""
        self.create_schedule()

    def next_available_slot(self) -> datetime:
        """Return when the owner is free again after finishing today's scheduled tasks."""
        minutes_used = sum(task.time_to_complete for task in self.scheduled_tasks)
        return datetime.now() + timedelta(minutes=minutes_used)

    def explain(self):
        """Return a human-readable reason for each task in the current schedule."""
        explanations = []
        for task in self.scheduled_tasks:
            explanations.append(
                f"{task.pet.name}: {task.task_type} "
                f"({task.priority} priority, {task.time_to_complete} min)"
            )
        return explanations
