from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class TranscodeRequest(BaseModel):
    prompt: str = Field(min_length=1)
    verbosity: Literal["minimal", "normal", "verbose"] = "normal"
    style_profile: Optional[dict] = None


class TranscodeResponse(BaseModel):
    # Mirror the canonical schema shape loosely (validated separately by jsonschema)
    goal: str
    inputs: list[str] = []
    outputs: list[str] = []
    constraints_explicit: list[str] = []
    constraints_inferred: list[str] = []
    libraries_preferred: list[str] = []
    libraries_forbidden: list[str] = []
    style_guides: list[str] = []
    naming_conventions: list[str] = []
    design_patterns: list[str] = []
    testing_strategy: str | None = None
    edge_cases: list[str] = []
    verbosity: Literal["minimal", "normal", "verbose"]
    open_questions: list[str] = []


class GenerateRequest(BaseModel):
    spec: dict
    context: dict | None = None


class GenerateResponse(BaseModel):
    code: str


class GenerateOpsRequest(BaseModel):
    spec: dict
    context: dict | None = None


class Op(BaseModel):
    action: str
    path: str
    content: str | None = None
    locator: dict | None = None
class GenerateOpsResponse(BaseModel):
    ops: list[Op]


class TaskSpec(BaseModel):
    goal: str
    inputs: list[str] = []
    outputs: list[str] = []
    constraints_explicit: list[str] = []
    constraints_inferred: list[str] = []
    libraries_preferred: list[str] = []
    libraries_forbidden: list[str] = []
    style_guides: list[str] = []
    naming_conventions: list[str] = []
    design_patterns: list[str] = []
    testing_strategy: str = ""
    edge_cases: list[str] = []
    verbosity: Literal["minimal", "normal", "verbose"] = "normal"
    open_questions: list[str] = []
    risk: str = "medium"
    priority: str = "medium"
    estimated_cost: str = "medium"




