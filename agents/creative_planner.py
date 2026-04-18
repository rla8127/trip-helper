from __future__ import annotations

import json
import os
from typing import Any

from crewai import Agent, LLM, Task

from schemas.travel_schema import TravelPlan, TravelerProfile
from tools.trip_tavily_wrapper import TripTavilySearch


class CreativePlannerService:
    """Tavily 검색을 바탕으로 여행 초안을 만드는 간단한 서비스."""

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.5,
        searcher: TripTavilySearch | None = None,
    ) -> None:
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError("OPENAI_API_KEY가 설정되어 있지 않습니다.")

        self.searcher = searcher or TripTavilySearch()
        self.llm = LLM(model=model, temperature=temperature)

    def _research(self, profile: TravelerProfile) -> dict[str, str]:
        style_text = ", ".join(profile.travel_style) if profile.travel_style else "일반 여행"

        places = self.searcher.search_places(
            destination=profile.destination,
            query=(
                f"{profile.duration_days}일 일정에 맞는 핵심 관광지, "
                f"{style_text} 여행자에게 맞는 장소, 대표 음식, 이동 동선을 알려줘"
            ),
        )
        news = self.searcher.search_news(
            destination=profile.destination,
            query=(
                f"{profile.start_date or '예정일 미정'} 전후 여행자가 알아야 할 최신 이슈, "
                "운영 변경, 혼잡도, 축제, 교통 주의사항을 알려줘"
            ),
        )
        return {"places": places, "news": news}

    def _prompt(self, profile: TravelerProfile, research: dict[str, str]) -> str:
        style_text = ", ".join(profile.travel_style) if profile.travel_style else "일반 여행"
        return f"""
너는 여행 초안을 만드는 여행 플래너다.
아래 검색 결과를 참고해서 현실적인 여행 일정을 작성하라.

규칙:
1. 출력은 JSON 객체만 작성한다.
2. 결과는 TravelPlan 스키마를 정확히 따른다.
3. 여행 일수는 반드시 {profile.duration_days}일이다.
4. 총예산 {profile.budget}원을 크게 넘기지 않는다.
5. 하루 동선은 무리하지 않게 구성한다.
6. 모든 설명은 한국어로 작성한다.
7. 마크다운 코드블록은 쓰지 않는다.

[사용자 정보]
- 목적지: {profile.destination}
- 여행 일수: {profile.duration_days}일
- 총예산: {profile.budget}원
- 인원: {profile.travelers}명
- 스타일: {style_text}
- 출발일: {profile.start_date or '미정'}

[장소 검색 결과]
{research["places"]}

[최신 이슈 검색 결과]
{research["news"]}

TravelPlan 형식:
{{
  "destination": "string",
  "total_budget": 0,
  "total_estimated_cost": 0,
  "days": [
    {{
      "day": 1,
      "theme": "string",
      "activities": [
        {{
          "time": "09:00",
          "title": "string",
          "location": "string",
          "estimated_cost": 0,
          "transport": "string 또는 null",
          "duration": "string 또는 null"
        }}
      ],
      "estimated_day_cost": 0
    }}
  ],
  "warnings": ["string"]
}}
""".strip()

    def _prompt_with_feedback(
        self,
        profile: TravelerProfile,
        research: dict[str, str],
        feedback: list[str],
    ) -> str:
        feedback_text = json.dumps(feedback, ensure_ascii=False, indent=2)
        base_prompt = self._prompt(profile, research)
        return (
            f"{base_prompt}\n\n"
            "[Agent B 검수 피드백]\n"
            f"{feedback_text}\n\n"
            "위 피드백을 반드시 반영해 일정안을 다시 작성하라."
        )

    def _parse_json(self, result: Any) -> dict[str, Any]:
        text = str(result).strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"여행 초안 결과를 JSON으로 파싱하지 못했습니다.\n{text}") from exc

        return TravelPlan.model_validate(parsed).model_dump()

    def generate_plan(
        self,
        profile: TravelerProfile,
        feedback: list[str] | None = None,
    ) -> dict[str, Any]:
        research = self._research(profile)
        prompt = (
            self._prompt_with_feedback(profile, research, feedback)
            if feedback
            else self._prompt(profile, research)
        )
        result = self.llm.call(prompt)
        return self._parse_json(result)

    def build_agent(self) -> Agent:
        return Agent(
            role="Creative Planner",
            goal="검색 기반으로 여행 초안을 설계한다.",
            backstory="최신 여행 정보와 예산을 반영해 초안 일정을 만드는 플래너",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
        )

    def build_task(self, profile: TravelerProfile) -> Task:
        research = self._research(profile)
        return Task(
            description=self._prompt(profile, research),
            expected_output="TravelPlan 스키마를 만족하는 JSON 객체 문자열",
        )
