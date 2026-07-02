"""Read-only contracts for existing knowledge and maintenance views."""

from pydantic import BaseModel, ConfigDict, Field


class GraphNodeResponse(BaseModel):
    id: str
    label: str
    type: str
    x: float
    y: float


class GraphEdgeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(serialization_alias="from")
    to: str
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNodeResponse]
    edges: list[GraphEdgeResponse]


class MaintenanceTaskResponse(BaseModel):
    id: str
    equipment: str
    type: str
    due: str
    status: str
    assignee: str
    priority: str
