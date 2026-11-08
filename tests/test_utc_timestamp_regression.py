"""Keep the metrics timestamp compatible without deprecated UTC APIs."""

from datetime import datetime, timezone
import warnings

from note_filler.metrics import calculate_polaris_metrics


def test_metrics_timestamp_is_naive_utc_without_deprecation_warning():
    before = datetime.now(timezone.utc).replace(tzinfo=None)
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        timestamp = calculate_polaris_metrics({}).calculated_at
    after = datetime.now(timezone.utc).replace(tzinfo=None)

    parsed = datetime.fromisoformat(timestamp)
    assert parsed.tzinfo is None
    assert before <= parsed <= after
