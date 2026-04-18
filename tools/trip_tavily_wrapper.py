from __future__ import annotations

import json
import os
from typing import Iterable, Optional

from dotenv import load_dotenv
from crewai_tools import TavilySearchTool

load_dotenv()

TRAVEL_PRIORITY_DOMAINS = [
    "tripadvisor.com",
    "google.com",
    "klook.com",
    "kkday.com",
    "agoda.com",
    "booking.com",
    "visitjapan.or.jp",
    "jnto.go.jp",
]

class TripTavilySearch:
    """
    Trip-Tailor 전용 검색 래퍼.
    CrewAI Tool 자체를 감싸서 여행 검색 품질을 일정하게 유지한다.
    """
    
    def __init__(
        self,
        max_results: int = 5,
        timeout: int = 20,
    ) -> None:
        if not os.getenv("TAVILY_API_KEY"):
            raise EnvironmentError("TAVILY_API_KEY가 설정되어 있지 않습니다.")

        self.max_results = max_results
        self.timeout = timeout
        self.tool = TavilySearchTool(
            search_depth="advanced",
            topic="general",
            max_results=max_results,
            include_answer=True,
            include_raw_content=False,
            include_images=False,
            timeout=timeout,
        )

    def _build_tool(
        self,
        *,
        topic: str = "general",
        time_range: Optional[str] = None,
        include_domains: Optional[Iterable[str]] = None,
        exclude_domains: Optional[Iterable[str]] = None,
    ) -> TavilySearchTool:
        return TavilySearchTool(
            search_depth="advanced",
            topic=topic,
            time_range=time_range,
            max_results=self.max_results,
            include_domains=list(include_domains) if include_domains else TRAVEL_PRIORITY_DOMAINS,
            exclude_domains=list(exclude_domains) if exclude_domains else None,
            include_answer="advanced",
            include_raw_content=False,
            include_images=False,
            timeout=self.timeout,
        )

    def _run_and_format(self, tool: TavilySearchTool, query: str) -> str:
        raw_result = tool.run(query=query)

        # CrewAI Tavily tool returns a JSON string with escaped Unicode by default.
        # Re-serialize with ensure_ascii=False so Korean text prints naturally.
        try:
            parsed_result = json.loads(raw_result)
        except json.JSONDecodeError:
            return raw_result

        return json.dumps(parsed_result, ensure_ascii=False, indent=2)

    def search_places(
        self,
        destination: str,
        query: str,
        include_domains: Optional[Iterable[str]] = None,
        exclude_domains: Optional[Iterable[str]] = None,
    ) -> str:

        full_query = (
            f"{destination} 여행 정보. "
            f"{query}. "
            "최신 운영시간, 가격, 위치, 이동 동선에 도움이 되는 정보 중심으로 정리. "
            "Return the answer in Korean. "
            "응답은 반드시 자연스러운 한국어로 작성하고, 핵심 정보 위주로 간단명료하게 정리."
        )

        tool = self._build_tool(
            topic="general",
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        return self._run_and_format(tool, full_query)

    def search_news(
        self,
        destination: str,
        query: str,
        time_range: str = "month",
    ) -> str:
        full_query = (
            f"{destination} 여행 관련 최신 이슈. "
            f"{query}. "
            "관광 제한, 운영 변경, 축제, 시즌 이벤트, 물가 변동 중심. "
            "Return the answer in Korean. "
            "응답은 반드시 자연스러운 한국어로 작성하고 최신 변동사항을 우선 정리."
        )

        tool = self._build_tool(
            topic="news",
            time_range=time_range,
        )
        return self._run_and_format(tool, full_query)
