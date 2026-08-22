"""商机、跟进相关 Schema。"""
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OpportunityListItem(BaseModel):
    id: int
    title: str = ""
    province: str | None = None
    city: str | None = None
    purchaser: str | None = None
    budget: Decimal | None = None
    contents: list[str] = []
    stage: str | None = None
    total_score: Decimal
    level: str | None = None
    status: str
    publish_time: datetime | None = None
    source_url: str | None = None
    verify_status: int = 0
    verify_note: str | None = None


class ScoreDetail(BaseModel):
    total: Decimal
    demand: Decimal | None = None
    budget: Decimal | None = None
    region: Decimal | None = None
    urgency: Decimal | None = None
    competition: Decimal | None = None
    rules_version: str


class ProjectProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purchaser: str | None = None
    project_type: str | None = None
    budget: Decimal | None = None
    budget_est: bool = False
    bid_deadline: datetime | None = None
    household_cnt: int | None = None
    building_cnt: int | None = None
    contents: list[str] = []
    fund_source: str | None = None
    stage: str | None = None
    relevance: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    address: str | None = None


class OpportunityDetail(BaseModel):
    opportunity: OpportunityListItem
    profile: ProjectProfileOut | None = None
    score_detail: ScoreDetail | None = None
    strategy: dict | None = None
    follow_logs: list[dict] = []
    competitors: list[dict] = []


class FollowUpCreate(BaseModel):
    action: str = Field(min_length=1, max_length=50)
    to_status: str | None = None
    note: str | None = None
    next_plan: str | None = None
    follow_time: datetime | None = None


class AssignRequest(BaseModel):
    owner_id: int


class OpportunityFilter(BaseModel):
    keyword: str | None = None
    province: str | None = None
    city: str | None = None
    level: str | None = None
    status: str | None = None
    min_score: float | None = None
    max_score: float | None = None
    relevance: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    sort: str = "score_desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=10000)
