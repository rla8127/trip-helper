from __future__ import annotations

import json
import os
from typing import Any

from crewai import Agent, LLM, Task

from schemas.travel_schema import PlanReview, TravelPlan, TravelerProfile


class PlanReviewerService:
    """Agent B: 여행 초안을 검수하고 수정 제안을 만드는 서비스."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.2,
    ) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

        self.llm = LLM(model=model, temperature=temperature)

    def _rule_issues(self, profile: TravelerProfile, draft_plan: TravelPlan) -> list[str]:
        issues: list[str] = []

        if len(draft_plan.days) != profile.duration_days:
            issues.append(
                f"일정 일수 불일치: 요청 {profile.duration_days}일, 결과 {len(draft_plan.days)}일"
            )

        if draft_plan.total_estimated_cost > profile.budget:
            issues.append(
                f"예산 초과: 요청 예산 {profile.budget}원, 예상 비용 {draft_plan.total_estimated_cost}원"
            )

        for day in draft_plan.days:
            if len(day.activities) > 6:
                issues.append(
                    f"{day.day}일차 활동 과다: 활동 {len(day.activities)}개(권장 6개 이하)"
                )

        return issues

    def _prompt(
        self,
        profile: TravelerProfile,
        draft_plan: TravelPlan,
        rule_issues: list[str],
    ) -> str:
        base_issues = rule_issues or ["규칙 기반 문제 없음"]

        return f"""
너는 여행 일정 검수 담당자(Agent B)다.
Agent A가 만든 초안을 검수하고, 필요한 수정 제안을 간단하게 반환하라.

규칙:
1. 출력은 JSON 객체만 작성한다.
2. 결과는 PlanReview 스키마를 정확히 따른다.
3. issues와 suggestions는 중복 없이 간단명료하게 작성한다.
4. suggestions는 최대 3개까지만 작성한다.
5. 모든 설명은 한국어로 작성한다.
6. 마크다운 코드블록은 쓰지 않는다.

[요청자 정보]
- 목적지: {profile.destination}
- 여행 일수: {profile.duration_days}일
- 총예산: {profile.budget}원
- 인원: {profile.travelers}명
- 스타일: {", ".join(profile.travel_style) if profile.travel_style else "일반 여행"}

[규칙 기반 1차 점검 결과]
{json.dumps(base_issues, ensure_ascii=False, indent=2)}

[Agent A 초안]
{json.dumps(draft_plan.model_dump(), ensure_ascii=False, indent=2)}

PlanReview 형식:
{{
  "approved": true,
  "issues": ["string"],
  "suggestions": ["string"]
}}

approved 작성 기준:
- 치명 이슈(예산 초과, 일수 불일치)가 있으면 false
- 치명 이슈가 없고 경미한 조정만 필요하면 true
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
            raise ValueError(f"검수 결과를 JSON으로 파싱하지 못했습니다.\n{text}") from exc

        return PlanReview.model_validate(parsed).model_dump()

    def review_plan(
        self,
        profile: TravelerProfile,
        draft_plan: dict[str, Any] | TravelPlan,
    ) -> dict[str, Any]:
        validated_plan = (
            draft_plan
            if isinstance(draft_plan, TravelPlan)
            else TravelPlan.model_validate(draft_plan)
        )

        rule_issues = self._rule_issues(profile, validated_plan)
        prompt = self._prompt(profile, validated_plan, rule_issues)
        result = self.llm.call(prompt)
        review = self._parse_json(result)

        if rule_issues:
            merged_issues = list(dict.fromkeys([*rule_issues, *review["issues"]]))
            review["issues"] = merged_issues
            if any("예산 초과" in issue or "일정 일수 불일치" in issue for issue in rule_issues):
                review["approved"] = False

        return PlanReview.model_validate(review).model_dump()

    def build_agent(self) -> Agent:
        return Agent(
            role="Plan Reviewer",
            goal="여행 초안의 예산/동선/리스크를 검수하고 수정 제안을 제공한다.",
            backstory="여행 일정의 현실성과 안정성을 점검하는 검수 담당자",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def build_task(self, profile: TravelerProfile, draft_plan: dict[str, Any] | TravelPlan) -> Task:
        validated_plan = (
            draft_plan
            if isinstance(draft_plan, TravelPlan)
            else TravelPlan.model_validate(draft_plan)
        )
        rule_issues = self._rule_issues(profile, validated_plan)
        return Task(
            description=self._prompt(profile, validated_plan, rule_issues),
            expected_output="PlanReview 스키마를 만족하는 JSON 객체 문자열",
        )
