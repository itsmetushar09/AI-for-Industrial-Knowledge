"""Read-only adapters for existing frontend operational views."""

import math
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db_session
from app.models.equipment import Equipment
from app.models.knowledge import KnowledgeEdge, KnowledgeNode
from app.schemas.ui_support import (
    GraphEdgeResponse,
    GraphNodeResponse,
    GraphResponse,
    MaintenanceTaskResponse,
)

router = APIRouter(tags=["operations"])


@router.get("/compliance", response_model=list[dict[str, Any]])
async def compliance() -> list[dict[str, Any]]:
    """Return an honest empty state until a compliance domain is introduced."""

    return []


@router.get("/maintenance", response_model=list[MaintenanceTaskResponse])
async def maintenance(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[MaintenanceTaskResponse]:
    """Expose maintenance-task metadata attached to registered equipment."""

    equipment = (await session.scalars(select(Equipment).order_by(Equipment.name))).all()
    tasks: list[MaintenanceTaskResponse] = []
    for item in equipment:
        task = item.metadata_.get("maintenance_task")
        if not isinstance(task, dict):
            continue
        tasks.append(
            MaintenanceTaskResponse(
                id=str(task.get("id") or item.id),
                equipment=item.name,
                type=str(task.get("type") or "Inspection"),
                due=str(task.get("due") or ""),
                status=str(task.get("status") or "Open"),
                assignee=str(task.get("assignee") or "Unassigned"),
                priority=str(task.get("priority") or "Medium"),
            )
        )
    return tasks


@router.get("/graph", response_model=GraphResponse)
async def graph(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GraphResponse:
    """Return persisted knowledge nodes and edges with deterministic coordinates."""

    nodes = (await session.scalars(select(KnowledgeNode).order_by(KnowledgeNode.label))).all()
    edges = (await session.scalars(select(KnowledgeEdge).order_by(KnowledgeEdge.created_at))).all()
    count = max(1, len(nodes))
    return GraphResponse(
        nodes=[
            GraphNodeResponse(
                id=str(node.id),
                label=node.label,
                type=node.node_type,
                x=400 + math.cos((index / count) * math.tau) * 220,
                y=300 + math.sin((index / count) * math.tau) * 200,
            )
            for index, node in enumerate(nodes)
        ],
        edges=[
            GraphEdgeResponse(
                from_=str(edge.source_node_id),
                to=str(edge.target_node_id),
                label=edge.relation_type,
            )
            for edge in edges
        ],
    )
