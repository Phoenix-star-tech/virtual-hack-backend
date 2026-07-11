from fastapi import APIRouter

from app.schemas.faq_schemas import FAQItem

router = APIRouter()

FAQS = [
    FAQItem(
        id=1,
        question="How does Module 1 online task system work?",
        answer="Once you register and log in, you will access 'My Tasks' in your dashboard. For 20 days, we assign daily targets consisting of 6 specific subtasks. Submitting these on time builds your points. The top 3 performers on the leaderboard secure immediate, free advancement to Module 2.",
    ),
    FAQItem(
        id=2,
        question="Do I need a team to register for Module 1?",
        answer="No. Module 1 is completely individual. You register and solve subtasks on your own. During the transition to Module 2, you will form or join a team of 1 to 4 members to build your hackathon project.",
    ),
    FAQItem(
        id=3,
        question="Are certificates provided to all participants?",
        answer="Yes! We believe participation and effort should be celebrated. Every participant who completes the daily tasks of Module 1 or submits a project in Module 2 receives an official digital participation certificate verified by VASHIK Platform.",
    ),
    FAQItem(
        id=4,
        question="Where will the Module 3 Offline Finals be held?",
        answer="The location for the physical Grand Finale will be announced to the top 5 qualifying teams at the end of Module 2. Travel details, accommodation guidelines, and schedules will be coordinated directly.",
    ),
]


@router.get("/", response_model=list[FAQItem])
async def get_faqs():
    return FAQS