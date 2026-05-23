from pydantic import BaseModel


class ConflictOutput(BaseModel):
    has_conflict: bool
    conflicting_indices: list[int]
    reasoning: str
