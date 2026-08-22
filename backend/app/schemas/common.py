"""通用响应与分页结构。"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: T | None = None
    trace_id: str = ""


class PageResult(BaseModel, Generic[T]):
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[T] = []
