from __future__ import annotations

import json
import os
from typing import Any

from crewai import Agent, LLM, Task

from schemas.travel_schema import PlanReview, StyledPlan, TravelPlan, TravelerProfile


class HanatourStylerService:
    """Agent C: 여행 계획을 하나투어 톤으로 정리하고 상품 제안을 붙이는 서비스."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.4,
    ) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

        self.llm = LLM(model=model, temperature=temperature)

    def _prompt(
        self,
        profile: TravelerProfile,
        draft_plan: TravelPlan,
        review: PlanReview,
    ) -> str:
        return f"""
너는 하나투어 고객 커뮤니케이션 담당자(Agent C)다.
입력받은 여행 일정 초안을 하나투어 말투로 재구성하고, 고객에게 맞는 상품 카테고리를 소개하라.

규칙:
1. 출력은 JSON 객체만 작성한다.
2. 결과는 StyledPlan 스키마를 정확히 따른다.
3. 어조는 친절하고 신뢰감 있게, 과장 없이 작성한다.
4. hanatour_products는 '실제 상품 코드/가격'을 지어내지 말고 카테고리 중심으로 제안한다.
5. daily_highlights는 {profile.duration_days}개 이내로 작성한다.
6. booking_tips는 3개 이내로 작성한다.
7. 모든 문장은 한국어로 작성한다.
8. 마크다운 코드블록은 쓰지 않는다.

[고객 프로필]
- 목적지: {profile.destination}
- 인원: {profile.travelers}명
- 여행일: {profile.duration_days}일
- 예산: {profile.budget}원
- 스타일: {", ".join(profile.travel_style) if profile.travel_style else "일반 여행"}
- 출발일: {profile.start_date or "미정"}

[최종 일정안]
{json.dumps(draft_plan.model_dump(), ensure_ascii=False, indent=2)}

[검수 결과]
{json.dumps(review.model_dump(), ensure_ascii=False, indent=2)}

StyledPlan 형식:
{{
  "title": "string",
  "intro": "string",
  "daily_highlights": ["string"],
  "hanatour_products": ["string"],
  "booking_tips": ["string"],
  "closing_cta": "string"
}}
""".strip()

    def _parse_json(self, result: Any) -> dict[str, Any]:
        text = str(result).strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"스타일링 결과를 JSON으로 파싱하지 못했습니다.\n{text}") from exc

        return StyledPlan.model_validate(parsed).model_dump()

    def style_plan(
        self,
        profile: TravelerProfile,
        draft_plan: dict[str, Any] | TravelPlan,
        review: dict[str, Any] | PlanReview,
    ) -> dict[str, Any]:
        validated_plan = (
            draft_plan
            if isinstance(draft_plan, TravelPlan)
            else TravelPlan.model_validate(draft_plan)
        )
        validated_review = (
            review if isinstance(review, PlanReview) else PlanReview.model_validate(review)
        )
        prompt = self._prompt(profile, validated_plan, validated_review)
        result = self.llm.call(prompt)
        return self._parse_json(result)

    def build_agent(self) -> Agent:
        return Agent(
            role="HanaTour Brand Styler",
            goal="여행 계획을 하나투어 톤으로 고객 친화적으로 재구성한다.",
            backstory="브랜드 톤앤매너와 고객 안내 문구를 설계하는 콘텐츠 담당자",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def build_task(
        self,
        profile: TravelerProfile,
        draft_plan: dict[str, Any] | TravelPlan,
        review: dict[str, Any] | PlanReview,
    ) -> Task:
        validated_plan = (
            draft_plan
            if isinstance(draft_plan, TravelPlan)
            else TravelPlan.model_validate(draft_plan)
        )
        validated_review = (
            review if isinstance(review, PlanReview) else PlanReview.model_validate(review)
        )
        return Task(
            description=self._prompt(profile, validated_plan, validated_review),
            expected_output="StyledPlan 스키마를 만족하는 JSON 객체 문자열",
        )
