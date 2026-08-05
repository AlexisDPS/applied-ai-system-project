import streamlit as st

from pawpal_system import Owner, Pet, Task, Schedule
from ai_care_planner import AICarePlanner

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


def render_care_review(report):
    """Render an AICarePlanner CareReviewReport in the Streamlit UI."""
    st.markdown("### 🩺 AI Care Review")

    if not report.available:
        for note in report.notes:
            st.info(note)
        return

    st.write(
        f"**Overall schedule score for {report.owner_name}'s pets:** "
        f"{report.overall_score} / 10.0 &nbsp;|&nbsp; "
        f"**Confidence:** {confidence_label(report.overall_confidence)}"
    )

    for review in report.pet_reviews:
        with st.container(border=True):
            st.markdown(f"#### {review.pet_name} ({review.species})")
            st.write(
                f"**Score:** {review.score} / 10.0 &nbsp;|&nbsp; "
                f"**Confidence:** {confidence_label(review.confidence)}"
            )
            if review.fallback_used:
                st.caption(
                    "⚠️ No species-specific knowledge base entry found; "
                    "general veterinary guidelines were used."
                )
            st.write(review.summary)

            if review.recommendations:
                st.markdown("**Recommendations:**")
                for rec in review.recommendations:
                    st.write(f"- {rec}")

    if report.notes:
        st.markdown("**Notes:**")
        for note in report.notes:
            st.caption(note)


st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+ AI Care Planner")

st.markdown(
    """
Welcome to **PawPal+**, a pet care planning assistant. Add pets and tasks, build a
schedule based on your available time, and receive an automatic AI-generated
review of how well that schedule covers each pet's routine care needs.
"""
)

st.divider()

st.subheader("Quick Demo Inputs (UI only)")
owner_name = st.text_input("Owner name", value="Jordan")

if "owner" not in st.session_state:
    try:
        st.session_state.owner = Owner.load_from_json()
        st.toast("Loaded saved data from data.json")
    except FileNotFoundError:
        st.session_state.owner = Owner(name=owner_name, age=0)
owner = st.session_state.owner

st.markdown("### Pets")
st.caption("Add pets for this owner.")

col1, col2, col3 = st.columns(3)
with col1:
    pet_name = st.text_input("Pet name", value="Mochi")
with col2:
    breed = st.text_input("Breed", value="Tabby Cat")
with col3:
    species = st.selectbox("Species", ["dog", "cat", "fish", "other"])

if st.button("Add pet"):
    pet = Pet(name=pet_name, age=0, species=species, breed=breed, owner=owner)
    owner.add_pet(pet)
    owner.save_to_json()
    st.success(f"🐾 Added {pet_name} ({breed})")

if owner.pets:
    st.write("**Current pets:**")
    st.table([{"Name": p.name, "Species": p.species, "Breed": p.breed} for p in owner.pets])
else:
    st.info("No pets yet. Add one above.")

st.markdown("### Tasks")
st.caption("Add a few tasks. These feed into your scheduler.")

if owner.pets:
    pet_names = [p.name for p in owner.pets]
    selected_pet_name = st.selectbox("Pet", pet_names)
    selected_pet = next(p for p in owner.pets if p.name == selected_pet_name)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
    with col3:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)

    if st.button("Add task"):
        task = Task(
            task_type=task_title,
            time_to_complete=int(duration),
            priority=priority,
            pet=selected_pet,
        )
        selected_pet.add_task(task)
        owner.save_to_json()
        st.success(f"📝 Added '{task_title}' for {selected_pet.name}")

    all_tasks = owner.get_all_tasks()
    if all_tasks:
        st.write("**Current tasks:**")
        st.table(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.task_type,
                    "Duration (min)": t.time_to_complete,
                    "Priority": priority_label(t.priority),
                    "Status": status_label(t.is_completed),
                }
                for t in all_tasks
            ]
        )
    else:
        st.info("No tasks yet. Add one above.")
else:
    st.info("Add a pet before adding tasks.")

st.divider()

st.subheader("📅 Build Schedule")
st.caption("Generate today's schedule from the owner's pets and tasks.")

time_available = st.number_input("Time available (minutes)", min_value=1, max_value=1440, value=60)

if st.button("Generate schedule"):
    schedule = Schedule(owner=st.session_state.owner, time_available=int(time_available))
    schedule.create_schedule()

    if schedule.scheduled_tasks:
        st.success(f"✅ Schedule created with {len(schedule.scheduled_tasks)} task(s)!")
        st.table(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.task_type,
                    "Priority": priority_label(t.priority),
                    "Duration (min)": t.time_to_complete,
                }
                for t in schedule.scheduled_tasks
            ]
        )
    else:
        st.info("No tasks fit in the available time.")

    next_slot = schedule.next_available_slot()
    st.write(f"🕒 **Next available slot:** {next_slot.strftime('%Y-%m-%d %H:%M')}")

    st.markdown("#### ⏱️ Tasks Sorted by Time")
    time_sorted_tasks = schedule.sort_by_time(owner.get_all_tasks())
    if time_sorted_tasks:
        st.table(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.task_type,
                    "Priority": priority_label(t.priority),
                    "Duration (min)": t.time_to_complete,
                }
                for t in time_sorted_tasks
            ]
        )
    else:
        st.info("No tasks to sort yet.")

    st.markdown("#### 🥇 Tasks Sorted by Priority (then Time)")
    priority_sorted_tasks = schedule.sort_by_priority(owner.get_all_tasks())
    if priority_sorted_tasks:
        st.table(
            [
                {
                    "Pet": t.pet.name,
                    "Task": t.task_type,
                    "Priority": priority_label(t.priority),
                    "Duration (min)": t.time_to_complete,
                }
                for t in priority_sorted_tasks
            ]
        )
    else:
        st.info("No tasks to sort yet.")

    st.markdown("#### ⏳ Pending Tasks")
    pending_tasks = schedule.filter_tasks(is_completed=False)
    if pending_tasks:
        st.table(
            [
                {"Pet": t.pet.name, "Task": t.task_type, "Priority": priority_label(t.priority)}
                for t in pending_tasks
            ]
        )
    else:
        st.info("No pending tasks.")

    st.markdown("#### ⚠️ Scheduling Conflicts")
    conflicts = schedule.find_conflicts()
    if conflicts:
        for warning in conflicts:
            st.warning(warning)
    else:
        st.success("✅ No scheduling conflicts found.")

    st.divider()
    report = AICarePlanner().review_schedule(schedule)
    render_care_review(report)
