# tests/test_dashboard.py
#
# Smoke tests for dashboard/app.py with Streamlit's AppTest.
# Each scenario sets the filters, reruns the app and checks that it
# raises no exception and renders all 4 tabs.
# Run from the repository root: pytest tests/

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).parent.parent
APP_FILE = ROOT_DIR / "dashboard" / "app.py"
DATA_DIR = ROOT_DIR / "data" / "processed"

TIMEOUT = 180  # seconds; the first run loads the CSVs and builds the charts

# Deep Dive topics, read from the same file the dashboard uses
TOPICS = sorted(
    pd.read_csv(DATA_DIR / "trenord_reviews_analysis.csv", encoding="utf-8-sig")["topic_label"]
    .dropna()
    .unique()
    .tolist()
)


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def run_app(setup=None):
    """Run the app once, apply the widget changes in setup, then rerun."""
    at = AppTest.from_file(str(APP_FILE), default_timeout=TIMEOUT)
    at.run()
    if setup:
        setup(at)
        at.run()
    return at


def assert_renders(at):
    errors = [e.value for e in at.exception]
    assert not errors, errors
    assert len(at.tabs) == 4


def uncheck_ratings(at, keep):
    for star in [1, 2, 3, 4, 5]:
        if star not in keep:
            at.sidebar.checkbox(key=f"rating_{star}").uncheck()


def uncheck_categories(at, keep):
    for box in at.sidebar.checkbox:
        if box.key.startswith("cat_") and box.key != f"cat_{keep}":
            box.uncheck()


# ─────────────────────────────────────────────────────────────
# SCENARIOS
# ─────────────────────────────────────────────────────────────

def test_default_filters():
    assert_renders(run_app())


@pytest.mark.parametrize("topic", TOPICS)
def test_deep_dive_topic(topic):
    assert_renders(run_app(lambda at: at.selectbox[0].set_value(topic)))


def test_zero_rows():
    # 2015, 1★, Other: a combination with no reviews
    def setup(at):
        at.sidebar.slider[0].set_value((2015, 2015))
        uncheck_ratings(at, keep=[1])
        uncheck_categories(at, keep="Other")
    assert_renders(run_app(setup))


def test_incomplete_year_only():
    def setup(at):
        max_year = at.sidebar.slider[0].max
        at.sidebar.slider[0].set_value((max_year, max_year))
    assert_renders(run_app(setup))


def test_praise_only():
    # No Problem topics, so no negative-review words
    assert_renders(run_app(lambda at: uncheck_categories(at, keep="Praise")))


def test_five_stars_only():
    # No negative reviews
    assert_renders(run_app(lambda at: uncheck_ratings(at, keep=[5])))
