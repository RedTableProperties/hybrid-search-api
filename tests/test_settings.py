from config.settings import Settings


def test_search_refill_rate_from_minute():
    settings = Settings(SEARCH_RATE_LIMIT="300/minute")
    assert settings.search_refill_rate == 5.0


def test_search_refill_rate_from_second():
    settings = Settings(SEARCH_RATE_LIMIT="10/second")
    assert settings.search_refill_rate == 10.0