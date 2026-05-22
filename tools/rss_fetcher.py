from pydantic import BaseModel

class RSSArticle(BaseModel):
    title: str
    link: str
    description: str
    pubDate: str
    source_name: str

