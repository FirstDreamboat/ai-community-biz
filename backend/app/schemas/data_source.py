"""数据源与知识库 Schema。"""
from datetime import datetime

from pydantic import BaseModel, Field


class DataSourceCreate(BaseModel):
    source_name: str = Field(min_length=1, max_length=100)
    # 老类型 gov/property/policy/news/api + 智能商机四类新数据源（采购意向/项目计划/立项审批/土地出让）
    source_type: str = Field(pattern="^(gov|property|policy|news|api|intention|planlist|approval|land)$")
    base_url: str | None = None
    list_pages: list[str] = []
    spider_class: str | None = None
    keywords: list[str] = []
    regions: list[str] = []
    schedule_cron: str | None = None
    proxy_enabled: bool = False


class DataSourceUpdate(DataSourceCreate):
    pass


class DataSourceOut(BaseModel):
    id: int
    source_name: str
    source_type: str
    base_url: str | None = None
    list_pages: list[str] = []
    spider_class: str | None = None
    keywords: list[str] = []
    regions: list[str] = []
    schedule_cron: str | None = None
    proxy_enabled: int = 0
    status: int = 1
    last_run_at: datetime | None = None
    last_run_status: str | None = None


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)
    tags: list[str] = []


class KnowledgeUpdate(KnowledgeCreate):
    pass


class KnowledgeOut(BaseModel):
    id: int
    title: str
    category: str
    content: str
    tags: list[str] = []
    status: int = 1


class PolicyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    level: str | None = Field(default=None, max_length=20)  # 国家级/省级/市级
    region: str | None = Field(default=None, max_length=100)
    content: str | None = None
    publish_time: datetime | None = None


class PolicyUpdate(PolicyCreate):
    pass
