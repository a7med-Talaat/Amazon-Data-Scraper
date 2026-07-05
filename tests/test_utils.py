"""Tests for the retry_with_backoff decorator."""

import pytest

from amazon_scraper.utils import retry_with_backoff


class TestRetryWithBackoff:
    def test_returns_result_on_first_success(self):
        calls = {"n": 0}

        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def flaky():
            calls["n"] += 1
            return "ok"

        assert flaky() == "ok"
        assert calls["n"] == 1

    def test_retries_then_succeeds(self):
        calls = {"n": 0}

        @retry_with_backoff(max_retries=3, backoff_factor=0.01)
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError("transient")
            return "ok"

        assert flaky() == "ok"
        assert calls["n"] == 3

    def test_raises_after_exhausting_retries(self):
        calls = {"n": 0}

        @retry_with_backoff(max_retries=2, backoff_factor=0.01)
        def always_fails():
            calls["n"] += 1
            raise ValueError("permanent failure")

        with pytest.raises(ValueError, match="permanent failure"):
            always_fails()
        assert calls["n"] == 2
