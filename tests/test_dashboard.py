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

# Number of key number cards at the top of the page
N_KPIS = 3

# The feature request themes the table should show: requests for something new with an estimate,
# read from the same file the dashboard uses, highest lower end of the interval first
feature_requests = pd.read_csv(DATA_DIR / "feature_request_themes.csv", encoding="utf-8-sig")
NOT_NEW_REQUEST_THEMES = [
    "Fix something that does not work",
    "Complaints and support in the app",
    "Too vague to classify",
]
table_requests = feature_requests[
    ~feature_requests["theme"].isin(NOT_NEW_REQUEST_THEMES) & feature_requests["estimated_requests"].notna()
].sort_values("estimated_low", ascending=False)
REQUEST_THEMES = table_requests["theme"].tolist()
# The example reviews of notebook 09, one per theme that has one
request_examples = pd.read_csv(DATA_DIR / "feature_request_examples.csv", encoding="utf-8-sig")
EXAMPLES_LABEL = "See a real review for each theme"


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


def test_feature_requests_section_shows_its_table():
    at = run_app()
    assert_no_exception(at)
    # The title names the theme with the highest lower end of the interval
    titles = [element.value for element in at.markdown]
    assert f"##### The clearest request: {REQUEST_THEMES[0]}" in titles
    # The section is one table: one row per theme, in the order of the lower end, none of the
    # three themes that are not new requests, and each estimate written in words
    assert len(at.table) == 1
    table = at.table[0].value
    assert table.columns.tolist() == ["Theme", "What users ask for", "Estimated reviews"]
    assert table["Theme"].tolist() == REQUEST_THEMES
    for theme in NOT_NEW_REQUEST_THEMES:
        assert theme not in table["Theme"].tolist()
    for i, (_, row) in enumerate(table_requests.iterrows()):
        expected = (f"about {row['estimated_requests']:.0f}, "
                    f"between {row['estimated_low']:.0f} and {row['estimated_high']:.0f}")
        assert table["Estimated reviews"].iloc[i] == expected
        assert table["What users ask for"].iloc[i] != ""
    # The caption gives the number of reviews checked by hand, computed from the CSV
    n_checked = int(table_requests["sample_flagged"].sum())
    captions = [caption.value for caption in at.caption]
    expected_caption = (f"Estimated from {n_checked} reviews I checked by hand. "
                        "A wide range means the estimate is uncertain.")
    assert expected_caption in captions


def test_feature_request_examples_expander():
    at = run_app()
    examples_expanders = [expander for expander in at.expander if expander.label == EXAMPLES_LABEL]
    assert len(examples_expanders) == 1
    blocks = [element.value for element in examples_expanders[0].markdown]
    # First the note on the language, then one block per theme of the table that has an example,
    # in the order of the table, each starting with the theme name in bold
    assert blocks[0] == "Reviews are in Italian, as written by users."
    themes_with_example = []
    for theme in REQUEST_THEMES:
        if theme in request_examples["theme"].tolist():
            themes_with_example.append(theme)
    assert len(blocks) == 1 + len(themes_with_example)
    for block, theme in zip(blocks[1:], themes_with_example):
        assert block.startswith(f"**{theme}**")


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
    # The full table, the example reviews of the feature requests, then one expander per upvoted
    # review of the selected topic
    assert expanders[0].label == "Show the full table"
    assert len(expanders[0].dataframe) == 1
    full_table = expanders[0].dataframe[0].value
    assert len(full_table) == len(TOPICS)
    # The recent share column is named after the last two complete years and holds no empty value
    recent_columns = [column for column in full_table.columns if column.startswith("Share 20")]
    assert len(recent_columns) == 1
    assert full_table[recent_columns[0]].notna().all()
    # The reviews of the explorer are the expanders after the full table and the examples
    review_expanders = [expander for expander in expanders[1:] if expander.label != EXAMPLES_LABEL]
    assert len(review_expanders) > 0
    for review_expander in review_expanders:
        assert len(review_expander.markdown) >= 1
