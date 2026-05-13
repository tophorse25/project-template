from urllib.parse import quote_plus


def build_reddit_search_url(query: str, sort: str = "relevance") -> str:
    encoded_query = quote_plus(query)
    return f"https://www.reddit.com/search/?q={encoded_query}&sort={sort}"