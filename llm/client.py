from langchain_groq import ChatGroq

# llm = ChatGroq(
#     model="llama-3.3-70b-versatile",
# )


def get_llm(temperature: float = 0.0):
    # base = ChatOllama(
    #     model="qwen2.5-coder:1.5b",
    #     temperature=temperature,
    # )

    base = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=temperature,
    )
    return base
