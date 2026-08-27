from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    items: list[T]


class MessageResponse(BaseModel):
    message: str
