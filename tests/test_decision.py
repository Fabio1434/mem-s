import pytest

from gnn_sdn_apt.decision import decide_action


def test_alert_only_is_the_default_for_suspicious_score():
    result = decide_action("10.0.0.1", 0.99)
    assert result["suspicious"] is True
    assert result["action"] == "alert"


def test_block_requires_explicit_mitigation_enablement():
    assert decide_action("10.0.0.1", 0.99, mitigation_enabled=True)["action"] == "block_source"
    assert decide_action("10.0.0.1", 0.5, mitigation_enabled=True)["action"] == "observe"


@pytest.mark.parametrize("score,threshold", [(-0.1, 0.5), (1.1, 0.5), (0.5, -0.1), (0.5, 1.1)])
def test_invalid_score_or_threshold_is_rejected(score, threshold):
    with pytest.raises(ValueError):
        decide_action("10.0.0.1", score, threshold)
