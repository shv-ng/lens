from pydantic import BaseModel


class VerdictOutput(BaseModel):
    verdict_label: str
    verdict_explanation: str
    framing_notes: str
