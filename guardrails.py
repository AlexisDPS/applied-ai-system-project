"""
guardrails.py

Safety and consistency checks applied to every AI-generated care review
before it is shown to a user.

This module never generates review content itself -- it only validates,
clamps, sanitizes, and finalizes output produced by `ai_care_planner.py`.
Keeping these checks in one place means every entry point (CLI, Streamlit
app, evaluation script) enforces the same guarantees:

- Scores always fall within 1.0-10.0.
- Confidence is always one of High/Medium/Low.
- Recommendations never exceed the maximum count and are never duplicated.
- Generated text never reads as a medical diagnosis, prescription, or
  treatment instruction.
- Every report is accompanied by a disclaimer stating this tool does not
  replace a licensed veterinarian.
"""

import re
from typing import List

ALLOWED_CONFIDENCE_LEVELS = ("High", "Medium", "Low")
MAX_RECOMMENDATIONS = 10
MIN_SCORE = 1.0
MAX_SCORE = 10.0

DISCLAIMER = (
    "This AI review supports pet care scheduling only. It does not diagnose "
    "illness, prescribe treatment, or replace a licensed veterinarian."
)

# Language that would push this tool from "scheduling assistant" into
# "medical advice" territory. Any generated text containing one of these
# terms is redacted rather than shown to the user.
BLOCKED_PATTERNS = [
    r"\bdiagnos\w*\b",
    r"\bprescri\w*\b",
    r"\bdosage\b",
    r"\bmg/kg\b",
    r"\badminister\w*\b",
    r"\btreat(?:ment|ments|ed|ing)?\b",
    r"\bcure[sd]?\b",
]
_BLOCKED_RE = re.compile("|".join(BLOCKED_PATTERNS), re.IGNORECASE)


def clamp_score(score: float) -> float:
    """Force a score into the supported 1.0-10.0 range, rounded to one decimal."""
    if score is None:
        return MIN_SCORE
    return round(max(MIN_SCORE, min(MAX_SCORE, float(score))), 1)


def validate_confidence(confidence: str) -> str:
    """Fall back to 'Low' if an unrecognized confidence level is produced."""
    if confidence in ALLOWED_CONFIDENCE_LEVELS:
        return confidence
    return "Low"


def sanitize_text(text: str) -> str:
    """Remove language that would read as medical diagnosis or treatment advice."""
    if not text:
        return text
    return _BLOCKED_RE.sub("[reviewed]", text)


def enforce_recommendation_limit(
    recommendations: List[str], limit: int = MAX_RECOMMENDATIONS
) -> List[str]:
    """Sanitize, deduplicate, and cap recommendations at the maximum allowed count."""
    seen = set()
    deduped = []
    for rec in recommendations:
        clean = sanitize_text(rec)
        if clean and clean not in seen:
            seen.add(clean)
            deduped.append(clean)
    return deduped[:limit]


def guard_review(review):
    """Apply all safety and consistency checks to a single PetCareReview."""
    review.score = clamp_score(review.score)
    review.confidence = validate_confidence(review.confidence)
    review.summary = sanitize_text(review.summary)
    review.recommendations = enforce_recommendation_limit(review.recommendations)
    return review


def guard_report(report):
    """Apply guardrails to every pet review in a report, then finalize notes."""
    report.pet_reviews = [guard_review(r) for r in report.pet_reviews]

    if report.overall_score is not None:
        report.overall_score = clamp_score(report.overall_score)
    if report.overall_confidence is not None:
        report.overall_confidence = validate_confidence(report.overall_confidence)

    report.notes = [sanitize_text(note) for note in report.notes]
    report.notes.append(DISCLAIMER)

    return report
