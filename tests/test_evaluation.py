import json

import pytest

from gnn_sdn_apt.evaluation import compare_model_reports, summarize_mitigation_events


def test_compare_model_reports_writes_csv(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "baseline_metrics.json").write_text(json.dumps({
        "model": "RandomForest", "split_method": "temporal", "threshold": 0.9,
        "accuracy": 0.9, "precision": 0.8, "recall": 0.7, "f1": 0.75,
        "false_positive_rate": 0.1, "false_negative_rate": 0.2, "test_observations": 20,
    }), encoding="utf-8")
    output = reports / "comparison.csv"

    rows = compare_model_reports(reports, output)
    assert rows[0]["model"] == "RandomForest"
    assert output.exists()


def test_mitigation_latency_summary(tmp_path):
    event_file = tmp_path / "events.jsonl"
    event_file.write_text(
        '{"source_ip":"10.0.0.1","decision_action_latency_seconds":0.5}\n'
        '{"source_ip":"10.0.0.2","decision_action_latency_seconds":1.5}\n',
        encoding="utf-8",
    )
    result = summarize_mitigation_events(event_file)
    assert result["events"] == 2
    assert result["unique_sources"] == 2
    assert result["mean_decision_action_latency_seconds"] == 1.0


def test_compare_without_reports_fails_clearly(tmp_path):
    with pytest.raises(FileNotFoundError):
        compare_model_reports(tmp_path)
