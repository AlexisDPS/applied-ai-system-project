"""
ai_care_planner.py

AI-assisted review layer for PawPal+ schedules.

This module does NOT build, sort, or modify schedules -- that logic lives
entirely in `pawpal_system.Schedule`. Instead, it *reads* an already-built
Schedule and produces a professional, veterinarian-toned review: a
1.0-10.0 quality score per pet, a confidence level, a short summary, and
up to 10 practical recommendations grounded in the local knowledge base
(`knowledge/*.md`, accessed through `retriever.KnowledgeRetriever`).

Every review produced here is passed through `guardrails.py` before being
returned, so callers can treat the output of `AICarePlanner.review_schedule`
as safe to display directly to a user.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from pawpal_system import Pet, Schedule, Task
from retriever import KnowledgeRetriever
import guardrails

# Keyword groups used to recognize which "care category" a task belongs to.
# This is intentionally simple keyword matching (not NLP) -- it only needs
# to be reliable enough to notice obviously missing categories of care.
CARE_CATEGORY_KEYWORDS = {
    "feeding": ["feed", "food", "meal", "water"],
    "exercise_enrichment": ["walk", "play", "exercise", "enrichment", "training"],
    "grooming_habitat": [
        "groom", "brush", "nail", "bath", "litter", "tank", "cage", "clean",
    ],
}

# Core categories every pet's care schedule should show some coverage of.
EXPECTED_CATEGORIES = ["feeding", "exercise_enrichment", "grooming_habitat"]

CATEGORY_LABELS = {
    "feeding": "a feeding task",
    "exercise_enrichment": "an exercise or enrichment task",
    "grooming_habitat": "a grooming or habitat-cleaning task",
}


@dataclass
class PetCareReview:
    """AI-generated review for a single pet's portion of a schedule."""

    pet_name: str
    species: str
    score: float
    confidence: str
    summary: str
    recommendations: List[str] = field(default_factory=list)
    fallback_used: bool = False


@dataclass
class CareReviewReport:
    """Full AI review for an owner's generated schedule."""

    owner_name: str
    generated_at: datetime
    pet_reviews: List[PetCareReview] = field(default_factory=list)
    overall_score: Optional[float] = None
    overall_confidence: Optional[str] = None
    notes: List[str] = field(default_factory=list)
    available: bool = True  # False when there was nothing to review


class AICarePlanner:
    """
    Reviews an existing Schedule and produces a professional, veterinarian-
    toned assessment of how well it covers each pet's routine care needs.

    This class only *reads* the Schedule/Owner/Pet/Task objects that already
    exist in pawpal_system.py. It never sorts, filters, or rebuilds a
    schedule -- that responsibility stays with `Schedule` alone.
    """

    def __init__(self, retriever: Optional[KnowledgeRetriever] = None):
        self.retriever = retriever or KnowledgeRetriever()

    def review_schedule(self, schedule: Schedule) -> CareReviewReport:
        """
        Build a CareReviewReport for the given Schedule.

        If the owner has no tasks at all, or no schedule has been generated
        yet, this honestly reports that no AI review can be produced rather
        than fabricating one.
        """
        owner = schedule.owner
        all_tasks = owner.get_all_tasks()

        if not all_tasks:
            return CareReviewReport(
                owner_name=owner.name,
                generated_at=datetime.now(),
                available=False,
                notes=[
                    "No tasks exist for this owner yet, so no AI schedule "
                    "review can be generated. Add pets and tasks, then "
                    "build a schedule, to receive a review."
                ],
            )

        if not schedule.scheduled_tasks:
            return CareReviewReport(
                owner_name=owner.name,
                generated_at=datetime.now(),
                available=False,
                notes=[
                    "No schedule has been generated yet (or no pending "
                    "tasks fit the available time), so no AI schedule "
                    "review can be generated. Generate a schedule first."
                ],
            )

        pet_reviews = [
            self._review_pet(pet, schedule) for pet in owner.pets if pet.tasks
        ]

        report = CareReviewReport(
            owner_name=owner.name,
            generated_at=datetime.now(),
            pet_reviews=pet_reviews,
            available=True,
        )

        if pet_reviews:
            report.overall_score = round(
                sum(r.score for r in pet_reviews) / len(pet_reviews), 1
            )
            report.overall_confidence = self._aggregate_confidence(pet_reviews)

        conflicts = schedule.find_conflicts()
        if conflicts:
            report.notes.append(
                f"{len(conflicts)} scheduling conflict(s) were detected across "
                "pets; review the conflict list before finalizing today's plan."
            )

        return guardrails.guard_report(report)

    def _review_pet(self, pet: Pet, schedule: Schedule) -> PetCareReview:
        """Build a single pet's review from its tasks and knowledge base guidance."""
        knowledge = self.retriever.retrieve(pet.species)
        scheduled_ids = {id(t) for t in schedule.scheduled_tasks if t.pet is pet}
        all_for_pet = pet.tasks

        categories_present = self._categories_present(all_for_pet)
        score = self._score_pet(all_for_pet, scheduled_ids, categories_present)
        recommendations = self._build_recommendations(
            pet, all_for_pet, categories_present, knowledge
        )
        summary = self._build_summary(
            pet, scheduled_ids, categories_present, knowledge
        )

        return PetCareReview(
            pet_name=pet.name,
            species=pet.species,
            score=score,
            confidence=knowledge["confidence"],
            summary=summary,
            recommendations=recommendations,
            fallback_used=knowledge["fallback"],
        )

    @staticmethod
    def _categories_present(tasks: List[Task]) -> set:
        """Return the set of care categories represented among a pet's tasks."""
        present = set()
        for task in tasks:
            text = task.task_type.lower()
            for category, keywords in CARE_CATEGORY_KEYWORDS.items():
                if any(keyword in text for keyword in keywords):
                    present.add(category)
        return present

    @staticmethod
    def _score_pet(all_tasks: List[Task], scheduled_ids: set, categories_present: set) -> float:
        """
        Heuristic 1.0-10.0 quality score for one pet's schedule coverage.

        Starts from a baseline, rewards coverage of the core care categories
        and having tasks actually fit into today's schedule, and penalizes
        high-priority tasks that are overdue or left unscheduled.
        """
        score = 5.0

        covered = len(categories_present & set(EXPECTED_CATEGORIES))
        score += covered * 1.2  # up to +3.6 for full category coverage

        if scheduled_ids:
            score += 1.0

        now = datetime.now()
        pending_high_priority = [
            t for t in all_tasks if not t.is_completed and t.priority == "high"
        ]
        overdue_high_priority = [t for t in pending_high_priority if t.due_date < now]
        unscheduled_high_priority = [
            t for t in pending_high_priority if id(t) not in scheduled_ids
        ]

        score -= len(overdue_high_priority) * 1.0
        score -= max(
            0, len(unscheduled_high_priority) - len(overdue_high_priority)
        ) * 0.5

        return guardrails.clamp_score(score)

    def _build_recommendations(
        self, pet: Pet, all_tasks: List[Task], categories_present: set, knowledge: dict
    ) -> List[str]:
        """Suggest concrete additions, grounded in the pet's knowledge base entry."""
        recommendations = []

        for category in EXPECTED_CATEGORIES:
            if category not in categories_present:
                recommendations.append(
                    f"Consider adding {CATEGORY_LABELS[category]} for {pet.name}; "
                    f"see the {knowledge['species']} care guidance in the knowledge base."
                )

        now = datetime.now()
        overdue = sorted(
            (t for t in all_tasks if not t.is_completed and t.due_date < now),
            key=lambda t: t.due_date,
        )
        for task in overdue[:3]:
            recommendations.append(
                f"{pet.name}'s '{task.task_type}' is overdue "
                f"(was due {task.due_date.strftime('%Y-%m-%d %H:%M')}); reschedule it soon."
            )

        if knowledge["fallback"]:
            recommendations.append(
                f"No dedicated knowledge base entry exists for {pet.name}'s species "
                f"('{pet.species}'); general veterinary guidelines were used instead. "
                "Confirm species-specific routine care needs with a veterinarian."
            )

        return guardrails.enforce_recommendation_limit(recommendations)

    @staticmethod
    def _build_summary(
        pet: Pet, scheduled_ids: set, categories_present: set, knowledge: dict
    ) -> str:
        """Write a short, professional summary of this pet's schedule coverage."""
        covered = len(categories_present & set(EXPECTED_CATEGORIES))
        total = len(EXPECTED_CATEGORIES)

        if not scheduled_ids:
            return (
                f"{pet.name} has recorded tasks, but none fit into today's "
                f"available time. Core care category coverage: {covered}/{total}."
            )

        return (
            f"{pet.name}'s schedule covers {covered}/{total} core care "
            f"categories (feeding, exercise/enrichment, grooming/habitat) "
            f"with {len(scheduled_ids)} task(s) planned for today."
        )

    @staticmethod
    def _aggregate_confidence(pet_reviews: List[PetCareReview]) -> str:
        """Overall confidence is the lowest confidence among individual pet reviews."""
        order = {"Low": 0, "Medium": 1, "High": 2}
        lowest = min(pet_reviews, key=lambda r: order.get(r.confidence, 0))
        return lowest.confidence
