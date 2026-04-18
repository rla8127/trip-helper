# Trip Helper (A2A 연습용)

간단한 멀티 에이전트 여행 일정 생성 프로젝트입니다.  
목적은 완성형 서비스보다, A2A 방식으로 에이전트끼리 주고받는 흐름을 연습하는 데 있습니다.

## 구성
- Agent A (`CreativePlannerService`): 여행 일정 초안 생성
- Agent B (`PlanReviewerService`): 일정 검수 후 이슈/수정 제안
- Agent C (`HanatourStylerService`): 최종안을 하나투어 톤으로 정리 + 상품 카테고리 제안

## A2A 흐름
1. A가 초안을 만든다.
2. B가 검수한다.
3. 승인되지 않거나 수정사항이 있으면 A가 피드백 반영해서 다시 생성한다.
4. 마지막에 C가 고객 안내용 문구로 정리한다.

## 실행 방법
프로젝트 루트(`trip-helper`) 기준:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install crewai crewai-tools python-dotenv pydantic
python3 main.py
```

## 환경변수
루트 `.env` 파일에 아래 키가 필요합니다.

```env
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

## 현재 범위
- CLI 실행 기준으로 동작합니다.
- 실제 A2A 네트워크 프로토콜(별도 서버 간 메시지 교환)까지는 구현하지 않았고,
  코드 안에서 에이전트 역할/피드백 루프로 연습하는 구조입니다.
