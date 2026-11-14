# tests/test_dashboard.py
#
# Smoke tests for dashboard/app.py with Streamlit's AppTest, which runs the script without a
# browser and gives access to the elements it drew.
# Run from the repository root: pytest tests/

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).parent.parent
APP_FILE = ROOT_DIR / "dashboard" / "app.py"
DATA_DIR = ROOT_DIR / "data" / "processed"

TIMEOUT = 180  # seconds; the first run loads the CSV files

# The 12 topics and their number of reviews, read from the same file the dashboard uses
analysis_df = pd.read_csv(DATA_DIR / "trenord_reviews_analysis.csv", encoding="utf-8-sig")
REVIEWS_PER_TOPIC = analysis_df["topic_label"].value_counts()
TOPICS = REVIEWS_PER_TOPIC.index.tolist()  # largest first, as in the dropdown

# Number of key number cards at the top of the page
N_KPIS = 3

# The feature request themes the chart should show: requests for something new with an estimate,
# read from the same file the dashboard uses, largest estimate first
feature_requests = pd.read_csv(DATA_DIR / "feature_request_themes.csv", encoding="utf-8-sig")
NOT_NEW_REQUEST_THEMES = [
    "Fix something that does not work",
    "Complaints and support in the app",
    "Too vague to classify",
]
chart_requests = feature_requests[
    ~feature_requests["theme"].isin(NOT_NEW_REQUEST_THEMES) & feature_requests["estimated_requests"].notna()
].sort_values("estimated_requests", ascending=False)
REQUEST_THEMES = chart_requests["theme"].tolist()


def run_app():
    at = AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT)
    at.run()
    return at


def assert_no_exception(at):
    errors = [e.value for e in at.exception]
    assert not errors, errors


def test_page_renders():
    at = run_app()
    assert_no_exception(at)
    titles = [element.value for element in at.subheader]
    assert titles == [
        "What users write about", "How it changed", "What users ask for", "Explore a topic", "About this analysis",
    ]


def plotly_values(value):
    """Plotly writes a numeric array either as a plain list or, for numpy and pandas data, as binary
    data in base64 text: {"dtype": "f8", "bdata": "..."}. This turns both forms into a list."""
    if isinstance(value, dict) and "bdata" in value:
        raw_bytes = base64.b64decode(value["bdata"])
        return np.frombuffer(raw_bytes, dtype=value["dtype"]).tolist()
    return list(value)


def find_request_chart(at):
    """The Plotly chart of the feature requests, found by its theme names. AppTest has no reader of
    its own for Plotly charts, so get("plotly_chart") gives the raw elements, and each one holds its
    figure as JSON text in proto.spec."""
    for element in at.get("plotly_chart"):
        figure = json.loads(element.proto.spec)
        for trace in figure["data"]:
            if trace.get("type") == "bar" and set(trace.get("y", [])) == set(REQUEST_THEMES):
                return trace
    return None


def test_feature_requests_section_shows_its_chart():
    at = run_app()
    assert_no_exception(at)
    trace = find_request_chart(at)
    assert trace is not None, "No chart with the feature request themes"
    # One bar per theme, in the order of the estimates, and no theme that is not a new request
    assert trace["y"] == REQUEST_THEMES
    for theme in NOT_NEW_REQUEST_THEMES:
        assert theme not in trace["y"]
    # The bars are the estimates, and the error bars give the two ends of each interval
    estimate_by_theme = dict(zip(chart_requests["theme"], chart_requests["estimated_requests"]))
    low_by_theme = dict(zip(chart_requests["theme"], chart_requests["estimated_low"]))
    high_by_theme = dict(zip(chart_requests["theme"], chart_requests["estimated_high"]))
    error = trace["error_x"]
    assert error["symmetric"] is False
    bars = plotly_values(trace["x"])
    right_lengths = plotly_values(error["array"])
    left_lengths = plotly_values(error["arrayminus"])
    for i, theme in enumerate(trace["y"]):
        assert bars[i] == pytest.approx(estimate_by_theme[theme])
        assert bars[i] + right_lengths[i] == pytest.approx(high_by_theme[theme])
        assert bars[i] - left_lengths[i] == pytest.approx(low_by_theme[theme])
    # The caption gives the number of reviews checked by hand behind the chart
    n_checked = int(chart_requests["sample_flagged"].sum())
    captions = [caption.value for caption in at.caption]
    assert f"Estimated from {n_checked} checked reviews; themes with few checked reviews have wide intervals." in captions


def test_three_kpis_show_values():
    at = run_app()
    # The first three metrics are the key numbers; the explorer adds four more below them
    kpis = at.metric[:N_KPIS]
    labels = [kpi.label for kpi in kpis]
    # The year in the labels is computed, so only the start of the label is fixed
    assert labels[0].startswith("Average rating, ")
    assert labels[1] == "Reviews about app problems"
    assert labels[2].startswith("Reviews with a reply, ")
    for kpi in kpis:
        assert kpi.value.strip() != ""
    # The share of app problems is computed from the analysis file, with one decimal as on the card
    app_issue_share = (analysis_df["category"] == "App Issue").mean() * 100
    assert kpis[1].value == f"{app_issue_share:.1f}%"


def test_topic_options_sorted_by_share():
    at = run_app()
    assert at.selectbox(key="topic").options == TOPICS


@pytest.mark.parametrize("topic", TOPICS)
def test_explore_topic(topic):
    at = run_app()
    at.selectbox(key="topic").set_value(topic).run()
    assert_no_exception(at)
    # The explorer metrics follow the key numbers; the first is the number of reviews
    assert at.metric[N_KPIS].value == f"{REVIEWS_PER_TOPIC[topic]:,}"


def test_expanders_open_with_content():
    at = run_app()
    expanders = at.expander
    # The full table, then one expander per upvoted review of the selected topic
    assert expanders[0].label == "Show the full table"
    assert len(expanders[0].dataframe) == 1
    full_table = expanders[0].dataframe[0].value
    assert len(full_table) == len(TOPICS)
    # The recent share column is named after the last two complete years and holds no empty value
    recent_columns = [column for column in full_table.columns if column.startswith("Share 20")]
    assert len(recent_columns) == 1
    assert full_table[recent_columns[0]].notna().all()
    assert len(expanders) > 1
    for review_expander in expanders[1:]:
        assert len(review_expander.markdown) >= 1
