from trip_tavily_wrapper import TripTavilySearch

searcher = TripTavilySearch()

print(
    searcher.search_places(
        destination="오사카",
        query="20대 커플이 좋아할 야간 명소와 1인당 예산대"
    )
)

print(
    searcher.search_news(
        destination="도쿄",
        query="벚꽃 시즌 혼잡도와 주요 행사"
    )
)