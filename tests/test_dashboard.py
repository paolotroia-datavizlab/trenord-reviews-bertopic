# tests/test_dashboard.py
#
# Smoke tests for dashboard/app.py with Streamlit's AppTest, which runs the script without a
# browser and gives access to the elements it drew.
# Run from the repository root: pytest tests/

from pathlib import Path

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
    assert titles == ["What users complain about", "How it changed", "Explore a topic", "About this analysis"]


def test_four_kpis_show_values():
    at = run_app()
    # The first four metrics are the key numbers; the explorer adds four more below them
    kpis = at.metric[:4]
    labels = [kpi.label for kpi in kpis]
    assert labels[0] == "Reviews analysed"
    assert labels[1].startswith("Average rating in ")
    assert labels[2].startswith("Developer reply rate in ")
    assert labels[3] == "Labels checked by hand"
    for kpi in kpis:
        assert kpi.value.strip() != ""
    # The number of reviews is the number of rows of the labeled file
    n_italian = len(pd.read_csv(DATA_DIR / "trenord_reviews_labeled.csv", encoding="utf-8-sig"))
    assert kpis[0].value == f"{n_italian:,}"


def test_topic_options_sorted_by_share():
    at = run_app()
    assert at.selectbox(key="topic").options == TOPICS


@pytest.mark.parametrize("topic", TOPICS)
def test_explore_topic(topic):
    at = run_app()
    at.selectbox(key="topic").set_value(topic).run()
    assert_no_exception(at)
    # The explorer metrics follow the four key numbers; the first is the number of reviews
    assert at.metric[4].value == f"{REVIEWS_PER_TOPIC[topic]:,}"


def test_expanders_open_with_content():
    at = run_app()
    expanders = at.expander
    # The full table, then one expander per upvoted review of the selected topic
    assert expanders[0].label == "Show the full table"
    assert len(expanders[0].dataframe) == 1
    assert len(expanders[0].dataframe[0].value) == len(TOPICS)
    assert len(expanders) > 1
    for review_expander in expanders[1:]:
        assert len(review_expander.markdown) >= 1
