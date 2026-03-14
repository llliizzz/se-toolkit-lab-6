"""Router for analytics endpoints.

Each endpoint performs SQL aggregation queries on the interaction data
populated by the ETL pipeline. All endpoints require a `lab` query
parameter to filter results by lab (e.g., "lab-01").
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.models.interaction import InteractionLog
from app.models.item import ItemRecord
from app.models.learner import Learner

router = APIRouter()


async def _find_lab_and_tasks(
    lab: str, session: AsyncSession
) -> tuple[ItemRecord | None, list[int]]:
    """Find a lab item and its child task IDs."""
    # Convert "lab-04" → "Lab 04" pattern for title matching
    lab_number = lab.replace("lab-", "").lstrip("0") or "0"
    lab_padded = lab.replace("lab-", "").zfill(2)

    # Search for lab by title
    labs = (await session.exec(select(ItemRecord).where(ItemRecord.type == "lab"))).all()
    lab_item = None
    for item in labs:
        if f"Lab {lab_padded}" in item.title or f"Lab {lab_number}" in item.title:
            lab_item = item
            break

    if not lab_item:
        return None, []

    # Find child tasks
    tasks = (
        await session.exec(
            select(ItemRecord).where(ItemRecord.parent_id == lab_item.id)
        )
    ).all()

    item_ids = [lab_item.id] + [t.id for t in tasks]
    return lab_item, item_ids


@router.get("/scores")
async def get_scores(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Score distribution histogram for a given lab."""
    _, item_ids = await _find_lab_and_tasks(lab, session)
    if not item_ids:
        return [
            {"bucket": "0-25", "count": 0},
            {"bucket": "26-50", "count": 0},
            {"bucket": "51-75", "count": 0},
            {"bucket": "76-100", "count": 0},
        ]

    bucket = case(
        (InteractionLog.score <= 25, "0-25"),
        (InteractionLog.score <= 50, "26-50"),
        (InteractionLog.score <= 75, "51-75"),
        else_="76-100",
    )

    stmt = (
        select(bucket.label("bucket"), func.count().label("count"))
        .where(
            InteractionLog.item_id.in_(item_ids),
            InteractionLog.score.is_not(None),
        )
        .group_by(bucket)
    )

    rows = (await session.exec(stmt)).all()
    result_map = {r.bucket: r.count for r in rows}

    return [
        {"bucket": b, "count": result_map.get(b, 0)}
        for b in ["0-25", "26-50", "51-75", "76-100"]
    ]


@router.get("/pass-rates")
async def get_pass_rates(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-task pass rates for a given lab."""
    lab_item, _ = await _find_lab_and_tasks(lab, session)
    if not lab_item:
        return []

    tasks = (
        await session.exec(
            select(ItemRecord).where(ItemRecord.parent_id == lab_item.id)
        )
    ).all()

    results = []
    for task in sorted(tasks, key=lambda t: t.title):
        stmt = select(
            func.round(func.avg(InteractionLog.score), 1).label("avg_score"),
            func.count().label("attempts"),
        ).where(
            InteractionLog.item_id == task.id,
            InteractionLog.score.is_not(None),
        )
        row = (await session.exec(stmt)).first()
        if row and row.attempts > 0:
            results.append({
                "task": task.title,
                "avg_score": float(row.avg_score) if row.avg_score else 0.0,
                "attempts": row.attempts,
            })

    return results


@router.get("/timeline")
async def get_timeline(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Submissions per day for a given lab."""
    _, item_ids = await _find_lab_and_tasks(lab, session)
    if not item_ids:
        return []

    stmt = (
        select(
            func.date(InteractionLog.created_at).label("date"),
            func.count().label("submissions"),
        )
        .where(InteractionLog.item_id.in_(item_ids))
        .group_by(func.date(InteractionLog.created_at))
        .order_by(func.date(InteractionLog.created_at))
    )

    rows = (await session.exec(stmt)).all()
    return [{"date": str(r.date), "submissions": r.submissions} for r in rows]


@router.get("/groups")
async def get_groups(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Per-group performance for a given lab."""
    _, item_ids = await _find_lab_and_tasks(lab, session)
    if not item_ids:
        return []

    stmt = (
        select(
            Learner.student_group.label("group"),
            func.round(func.avg(InteractionLog.score), 1).label("avg_score"),
            func.count(func.distinct(InteractionLog.learner_id)).label("students"),
        )
        .join(Learner, InteractionLog.learner_id == Learner.id)
        .where(
            InteractionLog.item_id.in_(item_ids),
            InteractionLog.score.is_not(None),
        )
        .group_by(Learner.student_group)
        .order_by(Learner.student_group)
    )

    rows = (await session.exec(stmt)).all()
    return [
        {
            "group": r.group,
            "avg_score": float(r.avg_score) if r.avg_score else 0.0,
            "students": r.students,
        }
        for r in rows
    ]


@router.get("/completion-rate")
async def get_completion_rate(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    session: AsyncSession = Depends(get_session),
):
    """Completion rate for a given lab — percentage of learners who scored >= 60."""
    _, item_ids = await _find_lab_and_tasks(lab, session)
    if not item_ids:
        return {
            "lab": lab,
            "completion_rate": 0.0,
            "passed": 0,
            "total": 0,
        }

    # Count distinct learners with any interaction
    total_stmt = (
        select(func.count(func.distinct(InteractionLog.learner_id)))
        .where(InteractionLog.item_id.in_(item_ids))
    )
    total_learners = (await session.exec(total_stmt)).one()

    # Count distinct learners who scored >= 60
    passed_stmt = (
        select(func.count(func.distinct(InteractionLog.learner_id)))
        .where(
            InteractionLog.item_id.in_(item_ids),
            InteractionLog.score >= 60,
        )
    )
    passed_learners = (await session.exec(passed_stmt)).one()

    rate = 0.0 if total_learners == 0 else (passed_learners / total_learners) * 100

    return {
        "lab": lab,
        "completion_rate": round(rate, 1),
        "passed": passed_learners,
        "total": total_learners,
    }


@router.get("/top-learners")
async def get_top_learners(
    lab: str = Query(..., description="Lab identifier, e.g. 'lab-01'"),
    limit: int = Query(default=10, description="Number of top learners to return"),
    session: AsyncSession = Depends(get_session),
):
    """Top learners by average score for a given lab."""
    _, item_ids = await _find_lab_and_tasks(lab, session)
    if not item_ids:
        return []

    stmt = (
        select(
            InteractionLog.learner_id,
            func.avg(InteractionLog.score).label("avg_score"),
            func.count().label("attempts"),
        )
        .where(InteractionLog.item_id.in_(item_ids))
        .group_by(InteractionLog.learner_id)
    )

    rows = (await session.exec(stmt)).all()

    ranked = sorted(
        rows,
        key=lambda r: float(r.avg_score) if r.avg_score is not None else -1.0,
        reverse=True,
    )

    return [
        {
            "learner_id": r.learner_id,
            "avg_score": round(float(r.avg_score), 1) if r.avg_score is not None else 0.0,
            "attempts": r.attempts,
        }
        for r in ranked[:limit]
    ]
