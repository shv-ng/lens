from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

# llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
# )
llm = ChatOllama(
    model="llama-3.3-70b-versatile",
)


def get_llm(schema: type[BaseModel] | None = None, temperature: int = 0):
    llm.temperature = temperature
    if not schema:
        return llm
    return llm.with_structured_output(schema)
