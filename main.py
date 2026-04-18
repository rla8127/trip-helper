from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from agents.creative_planner import CreativePlannerService
from agents.hanatour_styler import HanatourStylerService
from agents.plan_reviewer import PlanReviewerService
from schemas.travel_schema import TravelerProfile


def _validate_required_env() -> None:
    required_keys = ("OPENAI_API_KEY", "TAVILY_API_KEY")
    missing_keys = [key for key in required_keys if not os.getenv(key)]
    if missing_keys:
        missing_text = ", ".join(missing_keys)
        raise EnvironmentError(
            f"필수 환경변수가 없습니다: {missing_text}. "
            "프로젝트 루트 .env 파일에 값을 설정해주세요."
        )


def main() -> None:
    load_dotenv()
    _validate_required_env()

    profile = TravelerProfile(
        destination="오사카",
        duration_days=3,
        budget=1200000,
        travelers=2,
        travel_style=["맛집", "야경", "도시여행"],
        start_date="2026-05-10",
    )

    planner = CreativePlannerService()
    reviewer = PlanReviewerService()
    styler = HanatourStylerService()

    max_rounds = 3
    min_rounds = 2
    feedback: list[str] = []
    draft_plan = {}
    review = {"approved": False, "issues": [], "suggestions": []}

    for round_no in range(1, max_rounds + 1):
        draft_plan = planner.generate_plan(profile, feedback=feedback)
        review = reviewer.review_plan(profile, draft_plan)

        print(f"[Round {round_no}] Agent A Draft Plan")
        print(json.dumps(draft_plan, ensure_ascii=False, indent=2))
        print()
        print(f"[Round {round_no}] Agent B Review Result")
        print(json.dumps(review, ensure_ascii=False, indent=2))
        print()

        feedback = list(
            dict.fromkeys(
                [
                    *(review.get("issues", [])),
                    *(review.get("suggestions", [])),
                ]
            )
        )

        if review["approved"] and round_no >= min_rounds and not feedback:
            break

    if not review["approved"]:
        print(
            f"[Final] max_rounds={max_rounds} 내 승인 실패. "
            "마지막 초안/검수 결과를 기준으로 수동 조정이 필요합니다."
        )

    styled_result = styler.style_plan(profile, draft_plan, review)
    print()
    print("[Agent C] HanaTour Styled Result")
    print(json.dumps(styled_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
