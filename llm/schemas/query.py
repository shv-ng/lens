from pydantic import BaseModel


class QueriesOutput(BaseModel):
    queries: list[str]
