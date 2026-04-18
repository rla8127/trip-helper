from pydantic import BaseModel
from typing import List, Optional

# Travel Agent A,B,C 공통으로 사용할 스키마
class TravelerProfile(BaseModel):
    destination: str
    duration_days: int
    budget: int
    travelers: int
    travel_style: List[str]
    start_date: Optional[str] = None


class Activity(BaseModel):
    time: str
    title: str
    location: str
    estimated_cost: int
    transport: Optional[str] = None
    duration: Optional[str] = None


class DayPlan(BaseModel):
    day: int
    theme: str
    activities: List[Activity]
    estimated_day_cost: int


class TravelPlan(BaseModel):
    destination: str
    total_budget: int
    total_estimated_cost: int
    days: List[DayPlan]
    warnings: List[str]


class PlanReview(BaseModel):
    approved: bool
    issues: List[str]
    suggestions: List[str]


class StyledPlan(BaseModel):
    title: str
    intro: str
    daily_highlights: List[str]
    hanatour_products: List[str]
    booking_tips: List[str]
    closing_cta: str
