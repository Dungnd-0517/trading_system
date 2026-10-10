import pytest
from backend.ai_engine.sentiment import (
    SentimentResult,
    analyze_sentiment,
    validate_sentiment,
)


def test_validate_sentiment_bounds():
    res = validate_sentiment(0.45, "MEDIUM", "Summary test")
    assert res.score == 0.45
    assert res.impact == "MEDIUM"
    assert res.summary == "Summary test"

    with pytest.raises(ValueError, match="sentiment score must be between -1 and 1"):
        validate_sentiment(1.5, "MEDIUM", "Test")

    with pytest.raises(ValueError, match="sentiment score must be between -1 and 1"):
        validate_sentiment(-1.2, "MEDIUM", "Test")

    with pytest.raises(ValueError, match="unsupported impact level"):
        validate_sentiment(0.2, "INVALID_LEVEL", "Test")


def test_bullish_gold_headlines():
    # Direct gold rally
    res1 = analyze_sentiment("Gold price rallies as US Dollar retreats")
    assert res1.score > 0.1
    assert "BULLISH" in res1.summary

    # Short covering / bullish momentum
    res2 = analyze_sentiment("Gold: Short covering signals renewed bullish momentum - TD Securities")
    assert res2.score > 0.1
    assert "BULLISH" in res2.summary

    # Rebound as yields and dollar ease
    res3 = analyze_sentiment("Gold, silver rebound as dollar, yields and oil ease - Kitco AM Report")
    assert res3.score > 0.1
    assert "BULLISH" in res3.summary

    # Geopolitical safe haven
    res4 = analyze_sentiment("Safe-haven demand surges as Middle East tensions escalate", impact_stars=3)
    assert res4.score > 0.2
    assert res4.impact == "HIGH_RISK_HALT"


def test_bearish_gold_headlines():
    # Direct gold tumble with dollar surge
    res1 = analyze_sentiment("Gold price tumbles as US Dollar rallies to two-month highs")
    assert res1.score < -0.1
    assert "BEARISH" in res1.summary

    # Yields jump and selling pressure
    res2 = analyze_sentiment("Treasury yields surge, gold slumps under heavy selling pressure")
    assert res2.score < -0.1
    assert "BEARISH" in res2.summary

    # Hawkish Fed / rate hikes
    res3 = analyze_sentiment("Fed hawkish stance: Higher for longer interest rates loom over gold")
    assert res3.score < -0.1
    assert "BEARISH" in res3.summary


def test_macro_consumer_sentiment_for_gold():
    # Falling consumer sentiment increases rate cut expectations, supporting Gold
    res = analyze_sentiment(
        "Gold price trades near high after preliminary Consumer Sentiment falls to 46.3, inflation expectations rise",
        impact_stars=2,
    )
    assert res.score > 0.1
    assert "BULLISH" in res.summary
    assert res.impact == "MEDIUM"


def test_neutral_and_balanced_headlines():
    res = analyze_sentiment("Federal Reserve calendar of upcoming events for next quarter")
    assert -0.1 <= res.score <= 0.1
    assert "NEUTRAL" in res.summary
    assert res.impact == "LOW"


def test_negation_reverses_or_dampens():
    pos = analyze_sentiment("Gold rallies to record levels")
    neg = analyze_sentiment("Gold fails to rally despite weaker greenback")
    assert pos.score > 0
    assert neg.score < pos.score


def test_high_impact_risk_halt_classification():
    res = analyze_sentiment("US CPI inflation surges unexpectedly, FOMC rate decision imminent", impact_stars=3)
    assert res.impact == "HIGH_RISK_HALT"
    assert "CẢNH BÁO BIẾN ĐỘNG CAO" in res.summary
