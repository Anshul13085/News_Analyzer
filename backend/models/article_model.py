from pydantic import BaseModel, HttpUrl, Field
from typing import List, Literal, Optional
from datetime import datetime


class EntitySentiment(BaseModel):
    name: str
    type: Literal['person', 'org', 'location', 'event', 'misc', 'gpe', 'date', 'time', 'cardinal', 'ordinal', 'quantity', 'loc', 'law', 'product', 'norp', 'work_of_art'] = "misc"
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    bias: Optional[str] = None  # e.g. left-leaning, right-leaning, pro-government
    score: Optional[float] = None


class ArticleDoc(BaseModel):
    # Allow missing title but provide fallback
    title: Optional[str] = "Untitled"

    url: HttpUrl
    source_name: Optional[str] = "Unknown"

    published_date: Optional[datetime] = None
    language: str = "en"

    original_text: Optional[str] = None
    translated_text: Optional[str] = None
    summary: Optional[str] = None

    # Sentiment (not always available at ingestion time)
    sentiment_overall: Optional[Literal["positive", "neutral", "negative"]] = None
    sentiment_score: Optional[float] = None

    # Bias — make optional at ingestion (you can fill later in pipeline)
    bias_overall: Optional[str] = None
    bias_score: Optional[float] = None

    entities: List[EntitySentiment] = []

    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = []
