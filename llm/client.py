from pydantic import BaseModel
from langchain_groq import ChatGroq

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0,
)


def get_llm(schema: type[BaseModel] | None = None):
    if not schema:
        return llm
    return llm.with_structured_output(schema)
