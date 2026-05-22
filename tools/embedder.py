from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_core.documents import Document

embedding_model = FastEmbedEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",cache_dir="./models")


def get_embeddings(documents: list[Document] | list[str]) -> list[list[float]]:
    if not documents:
        return []

    texts: list[str] = [
        doc.page_content if isinstance(doc, Document) else doc for doc in documents
    ]
    return embedding_model.embed_documents(texts)
