# dashboard/app.py

# ─────────────────────────────────────────────────────────────
# IMPORTS
# ─────────────────────────────────────────────────────────────

from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from wordcloud import WordCloud

# ─────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# Must be the first Streamlit command in the script.
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Trenord App — Review Analysis",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# PATHS AND SHARED CONSTANTS
# Paths are relative to the repository root, so the app works
# whatever the current working directory is.
# ─────────────────────────────────────────────────────────────

ROOT_DIR       = Path(__file__).parent.parent
DATA_DIR       = ROOT_DIR / "data" / "processed"
STOPWORDS_FILE = Path(__file__).parent / "stopwords_it.txt"

STARS = [1, 2, 3, 4, 5]

# One colour per star rating — red (negative) to green (positive), grey for neutral
RATING_COLORS = {
    1: "#d9534f",
    2: "#e8825a",
    3: "#aaaaaa",
    4: "#7bc67e",
    5: "#4caf50",
}
PRIMARY_COLOR    = "#4a90d9"
INCOMPLETE_COLOR = "#aaaaaa"
SERIES_COLORS    = ["#d9534f", "#e8825a", "#f0c040", "#4a90d9", "#7bc67e"]

# Display style (emoji, badge colour) for known categories.
# The categories themselves are always read from the data.
CATEGORY_STYLES = {
    "Problem": ("🔴", "red"),
    "Praise":  ("🟢", "green"),
    "Other":   ("⚪", "gray"),
}
DEFAULT_CATEGORY_STYLE = ("🔵", "blue")

# Yearly averages and rates are shown only for years with at least this many
# reviews, so that peaks and trends are not driven by a handful of reviews
MIN_REVIEWS_PER_YEAR = 30
THRESHOLD_NOTE = f"Yearly trends use complete years with at least {MIN_REVIEWS_PER_YEAR} reviews."

EMPTY_FILTER_MESSAGE = (
    "No reviews match the current filters. "
    "Widen the year range or select more ratings or categories."
)

# ─────────────────────────────────────────────────────────────
# LOAD DATA
# st.cache_data caches dataframes so they are not reloaded
# on every user interaction.
# ─────────────────────────────────────────────────────────────

@st.cache_data
def load_reviews(file_name):
    df = pd.read_csv(DATA_DIR / file_name)
    df["date"] = pd.to_datetime(df["date"])
    df["year"] = df["date"].dt.year
    return df

@st.cache_data
def load_stopwords():
    # Static export of the spaCy Italian stopword list, written by notebook 02,
    # so the app does not need spaCy. Lines starting with "#" are comments.
    stopwords = set()
    for line in STOPWORDS_FILE.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if word and not word.startswith("#"):
            stopwords.add(word)
    return stopwords

# Informative reviews only — EXCLUDE topics already removed by notebook 04b
df_analysis    = load_reviews("trenord_reviews_analysis.csv")
# Top 5 upvoted reviews per topic — used in Deep Dive tab
df_top_reviews = load_reviews("top_reviews_per_topic.csv")
# All Italian reviews with topic labels — needed for reply rate and rating
# trends, which refer to all reviews and not just the informative topics
df_full        = load_reviews("trenord_reviews_labeled.csv")

# The latest year is incomplete unless the data reaches 31 December
latest_date = df_full["date"].max()
if latest_date.month == 12 and latest_date.day == 31:
    LAST_COMPLETE_YEAR = latest_date.year
else:
    LAST_COMPLETE_YEAR = latest_date.year - 1

# Categories present in the data, with their display labels
ALL_CATEGORIES  = sorted(df_analysis["category"].dropna().unique().tolist())
CATEGORY_LABELS = {}
for cat in ALL_CATEGORIES:
    emoji = CATEGORY_STYLES.get(cat, DEFAULT_CATEGORY_STYLE)[0]
    CATEGORY_LABELS[cat] = f"{emoji} {cat}"

# ─────────────────────────────────────────────────────────────
# CHART AND DATA HELPERS
# ─────────────────────────────────────────────────────────────

def complete_years(df):
    """Rows from complete years only — used for all yearly trends."""
    return df[df["year"] <= LAST_COMPLETE_YEAR]

def reliable_years(df):
    """Rows from complete years with at least MIN_REVIEWS_PER_YEAR reviews in df."""
    complete    = complete_years(df)
    year_counts = complete.groupby("year").size()
    kept_years  = year_counts[year_counts >= MIN_REVIEWS_PER_YEAR].index
    return complete[complete["year"].isin(kept_years)]

def rating_distribution_chart(df):
    """Bar chart with the number of reviews per star rating."""
    rating_counts = df["rating"].value_counts().reindex(STARS, fill_value=0)
    fig = go.Figure(go.Bar(
        x=[f"{r}★" for r in rating_counts.index],
        y=rating_counts.values,
        marker_color=[RATING_COLORS[r] for r in rating_counts.index],
        text=rating_counts.values,
        textposition="outside"
    ))
    fig.update_layout(
        title="Rating Distribution",
        xaxis_title="Star Rating",
        yaxis_title="Number of Reviews",
        showlegend=False,
        plot_bgcolor="white",
        margin=dict(t=40, b=40)
    )
    return fig

def rating_trend_chart(df, title, color, reference_label):
    """
    Average rating per complete year (years with at least MIN_REVIEWS_PER_YEAR
    reviews), with a dashed reference line at the average of df.
    Returns None when there is no such year to plot.
    """
    yearly_avg = reliable_years(df).groupby("year")["rating"].mean().reset_index()
    if yearly_avg.empty:
        return None

    reference = df["rating"].mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yearly_avg["year"],
        y=yearly_avg["rating"],
        mode="lines+markers+text",
        text=[f"{v:.2f}" for v in yearly_avg["rating"]],
        textposition="top center",
        line=dict(color=color, width=2.5),
        marker=dict(size=8),
        name="Avg Rating"
    ))
    fig.add_hline(
        y=reference,
        line_dash="dash",
        line_color="black",
        opacity=0.4,
        annotation_text=f"{reference_label}: {reference:.2f}"
    )
    fig.update_layout(
        title=title,
        xaxis_title="Year",
        yaxis_title="Average Rating (1-5)",
        yaxis=dict(range=[1, 5]),
        plot_bgcolor="white",
        showlegend=False,
        margin=dict(t=40, b=40)
    )
    return fig

def reply_rate_over_time_chart(df):
    """
    Developer reply rate per year, only for years with at least
    MIN_REVIEWS_PER_YEAR reviews. Complete years are drawn as a solid line;
    the incomplete latest year, if any, as a dashed segment.
    """
    reply_by_year = (
        df
        .groupby("year")
        .agg(reply_rate=("has_reply", "mean"), n_reviews=("has_reply", "size"))
        .reset_index()
    )
    reply_by_year = reply_by_year[reply_by_year["n_reviews"] >= MIN_REVIEWS_PER_YEAR]
    reply_by_year["reply_rate"] = reply_by_year["reply_rate"] * 100

    complete   = reply_by_year[reply_by_year["year"] <= LAST_COMPLETE_YEAR]
    # The dashed segment starts from the last complete year to connect the lines
    incomplete = reply_by_year[reply_by_year["year"] >= LAST_COMPLETE_YEAR]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=complete["year"],
        y=complete["reply_rate"],
        mode="lines+markers+text",
        text=[f"{v:.1f}%" for v in complete["reply_rate"]],
        textposition="top center",
        line=dict(color=PRIMARY_COLOR, width=2.5),
        marker=dict(size=8),
        name="Reply rate"
    ))
    if len(incomplete) > 1:
        fig.add_trace(go.Scatter(
            x=incomplete["year"],
            y=incomplete["reply_rate"],
            mode="lines+markers",
            line=dict(color=INCOMPLETE_COLOR, width=2, dash="dash"),
            marker=dict(size=8),
            name=f"{LAST_COMPLETE_YEAR + 1} (incomplete year)"
        ))
    fig.update_layout(
        xaxis_title="Year",
        yaxis_title="% of Reviews with Reply",
        yaxis=dict(range=[0, 110]),
        plot_bgcolor="white",
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=20, b=60)
    )
    return fig

def topic_summary(df):
    """Number of reviews and average rating per topic."""
    return (
        df
        .groupby(["topic_label", "category"])
        .agg(count=("rating", "size"), avg_rating=("rating", "mean"))
        .reset_index()
    )

# ─────────────────────────────────────────────────────────────
# WORD ANALYSIS HELPERS
# Defined here at module level — used in Tab 4.
# ─────────────────────────────────────────────────────────────

# Domain-specific stopwords — generic words with no insight value
custom_stopwords = load_stopwords() | {
    "app", "applicazione", "trenord", "treno", "treni",
    "fare", "avere", "essere", "tutto", "volta", "volte",
    "anche", "però", "sempre", "ancora", "ogni", "dopo",
    "prima", "quando", "come", "cosa", "questo", "questa",
    "questi", "queste", "molto", "molta", "molti", "molte",
    "bene", "male", "poco", "niente", "nulla", "certo",
    # Generic verbs with no discriminative value
    "dovere", "potere", "dare", "riuscire", "andare",
    "vedere", "sapere", "venire", "trovare", "mettere",
    "dire", "stare", "usare", "volere",
    # Generic words that add no insight
    "neanche", "offrire", "esistere", "chiudere",
    "effettuare", "assurdo",
}

def get_word_freq(texts, top_n=20):
    """
    Calculate most frequent meaningful words from a list of texts.
    Uses lemmatized text — groups singular/plural variants correctly.
    Returns list of (word, count) tuples.
    """
    all_words = []
    for text in texts:
        if not isinstance(text, str):
            continue
        words = [
            w for w in text.lower().split()
            if w not in custom_stopwords
            and len(w) > 3
            and w.isalpha()
        ]
        all_words.extend(words)
    return Counter(all_words).most_common(top_n)

def get_critical_words(neg_texts, pos_texts, top_n=15):
    """
    Extract words that most characterize negative reviews vs positive.

    Method: normalized frequency ratio
        score = (freq_neg / n_neg) / (freq_pos / n_pos + 0.001)

    A high score means the word appears much more often per review
    in negative reviews than positive ones.
    Smoothing (0.001) prevents division by zero.
    Minimum threshold of 10 mentions filters out rare words.
    """
    neg_freq = dict(get_word_freq(neg_texts, top_n=500))
    pos_freq = dict(get_word_freq(pos_texts, top_n=500))
    n_neg    = len([t for t in neg_texts if isinstance(t, str)])
    n_pos    = len([t for t in pos_texts if isinstance(t, str)])

    if n_neg == 0 or n_pos == 0:
        return []

    scores = []
    for word, neg_count in neg_freq.items():
        if neg_count < 10:
            continue
        pos_count = pos_freq.get(word, 0)
        neg_rate  = neg_count / n_neg
        pos_rate  = pos_count / n_pos
        score     = neg_rate / (pos_rate + 0.001)
        scores.append({
            "word":      word,
            "score":     round(score, 2),
            "neg_count": neg_count,
            "pos_count": pos_count,
        })

    return sorted(scores, key=lambda x: x["score"], reverse=True)[:top_n]

# ─────────────────────────────────────────────────────────────
# SIDEBAR — global filters
# ─────────────────────────────────────────────────────────────

st.sidebar.title("🚂 Trenord Reviews")
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔽 Filters")

# Year range slider
min_year = int(df_analysis["year"].min())
max_year = int(df_analysis["year"].max())

year_range = st.sidebar.slider(
    "Year range",
    min_value=min_year,
    max_value=max_year,
    value=(min_year, max_year)
)

# Rating filter — one checkbox per star
st.sidebar.markdown("**Rating**")
selected_ratings = []
rating_cols = st.sidebar.columns(len(STARS))
for star, col in zip(STARS, rating_cols):
    if col.checkbox(f"{star}★", value=True, key=f"rating_{star}"):
        selected_ratings.append(star)

# Fallback — if user unchecks all show all ratings
if not selected_ratings:
    selected_ratings = STARS

# Category filter — one checkbox per category found in the data
st.sidebar.markdown("**Category**")
selected_categories = []
for cat in ALL_CATEGORIES:
    if st.sidebar.checkbox(CATEGORY_LABELS[cat], value=True, key=f"cat_{cat}"):
        selected_categories.append(cat)

# Fallback — if user unchecks all show all categories
if not selected_categories:
    selected_categories = ALL_CATEGORIES

st.sidebar.markdown("---")

# Apply all filters — df_filtered is used by all tabs
df_filtered = df_analysis[
    (df_analysis["year"] >= year_range[0]) &
    (df_analysis["year"] <= year_range[1]) &
    (df_analysis["rating"].isin(selected_ratings)) &
    (df_analysis["category"].isin(selected_categories))
].copy()

# Reviews counter — warning only when filters exclude data
total_reviews = len(df_analysis)
shown_reviews = len(df_filtered)

st.sidebar.metric(
    label="Reviews shown",
    value=f"{shown_reviews:,}"
)

if shown_reviews != total_reviews:
    st.sidebar.caption(f"of {total_reviews:,} total")
    st.sidebar.warning("⚠️ Filters active — some data is excluded.")
else:
    st.sidebar.caption(f"All {total_reviews:,} reviews shown")

# ─────────────────────────────────────────────────────────────
# PAGE TITLE
# ─────────────────────────────────────────────────────────────

st.title("🚂 Trenord App — Review Analysis")
st.markdown(
    f"Google Play Store reviews · Italian · "
    f"{df_full['year'].min()}–{df_full['year'].max()}"
)

# ─────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Overview",
    "🗂️ Topics",
    "🔍 Deep Dive",
    "📚 Words"
])

# ─────────────────────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ─────────────────────────────────────────────────────────────

with tab1:

    # ── Key Findings ──────────────────────────────────────────
    # Computed from the data at every run — not affected by filters.
    # Topics use the informative reviews; rating and reply trends use
    # all Italian reviews and complete years only.
    st.subheader("🔑 Key Findings")
    st.caption(
        f"Computed from the full dataset — not affected by filters. "
        f"{THRESHOLD_NOTE} Last complete year: {LAST_COMPLETE_YEAR}."
    )

    all_topics_summary = topic_summary(df_analysis)
    problem_topics     = all_topics_summary[all_topics_summary["category"] == "Problem"]
    praise_topics      = all_topics_summary[all_topics_summary["category"] == "Praise"]

    yearly_full = reliable_years(df_full).groupby("year").agg(
        avg_rating=("rating", "mean"),
        reply_rate=("has_reply", "mean")
    )
    first_year  = int(yearly_full.index.min())
    last_year   = int(yearly_full.index.max())
    rating_from = yearly_full.loc[first_year, "avg_rating"]
    rating_to   = yearly_full.loc[last_year, "avg_rating"]
    rating_verb = "fell" if rating_to < rating_from else "rose"

    peak_year  = int(yearly_full["reply_rate"].idxmax())
    peak_reply = yearly_full.loc[peak_year, "reply_rate"] * 100
    last_reply = yearly_full.loc[last_year, "reply_rate"] * 100

    kf1, kf2 = st.columns(2)
    with kf1:
        if problem_topics.empty:
            st.info("No Problem topics in the data.")
        else:
            top_problem = problem_topics.loc[problem_topics["count"].idxmax()]
            st.error(
                f"🔴 **Top problem:** {top_problem['topic_label']} — "
                f"{top_problem['count']:,} reviews, avg rating {top_problem['avg_rating']:.2f}★"
            )
        st.error(
            f"🔴 **Average rating {rating_verb}:** from {rating_from:.2f}★ ({first_year}) "
            f"to {rating_to:.2f}★ ({last_year})"
        )
    with kf2:
        st.warning(
            f"🟡 **Developer reply rate:** peaked at {peak_reply:.0f}% ({peak_year}), "
            f"{last_reply:.0f}% in {last_year}"
        )
        if praise_topics.empty:
            st.info("No Praise topics in the data.")
        else:
            top_praise = praise_topics.loc[praise_topics["count"].idxmax()]
            st.success(
                f"🟢 **Largest praise topic:** {top_praise['topic_label']} — "
                f"{top_praise['count']:,} reviews, avg rating {top_praise['avg_rating']:.2f}★"
            )

    st.markdown("---")

    if df_filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
    else:
        # ── KPI Cards + Rating Breakdown ─────────────────────
        # Left: 3 KPI cards with sparklines (complete years only)
        # Right: Rating breakdown compact bar
        st.subheader("📈 Key Metrics")

        col_kpi, col_breakdown = st.columns([3, 2])

        with col_kpi:
            # Counts use every complete year; averages and rates only years
            # with at least MIN_REVIEWS_PER_YEAR reviews
            yearly_counts  = complete_years(df_filtered).groupby("year").size().tolist()
            yearly_avg     = reliable_years(df_filtered).groupby("year")["rating"].mean().tolist()
            # Reply rate refers to all Italian reviews: value and sparkline
            # both ignore the filters, as stated in the help text
            yearly_reply   = reliable_years(df_full).groupby("year")["has_reply"].mean().mul(100).tolist()

            k1, k2, k3 = st.columns(3)

            with k1:
                st.metric(
                    label="Total Reviews",
                    value=f"{len(df_filtered):,}",
                    chart_data=yearly_counts,
                    chart_type="bar",
                    border=True
                )
            with k2:
                st.metric(
                    label="Average Rating",
                    value=f"{df_filtered['rating'].mean():.2f} / 5.0",
                    chart_data=yearly_avg,
                    chart_type="line",
                    border=True
                )
            with k3:
                st.metric(
                    label="Developer Reply Rate",
                    value=f"{df_full['has_reply'].mean() * 100:.1f}%",
                    chart_data=yearly_reply,
                    chart_type="line",
                    border=True,
                    help=f"All Italian reviews — not affected by filters. {THRESHOLD_NOTE}"
                )

        with col_breakdown:
            # Rating breakdown — horizontal stacked bar
            rating_pcts = (
                df_filtered["rating"]
                .value_counts(normalize=True)
                .reindex(STARS, fill_value=0.0)
                .mul(100)
                .round(1)
            )

            fig = go.Figure()
            for star in STARS:
                fig.add_trace(go.Bar(
                    x=[rating_pcts[star]],
                    y=[""],
                    orientation="h",
                    name=f"{star}★",
                    marker_color=RATING_COLORS[star],
                    text=f"{rating_pcts[star]:.0f}%" if rating_pcts[star] > 5 else "",
                    textposition="inside",
                    insidetextanchor="middle",
                    hovertemplate=f"{star}★: {rating_pcts[star]:.1f}%<extra></extra>"
                ))

            fig.update_layout(
                barmode="stack",
                height=80,
                margin=dict(t=0, b=0, l=0, r=0),
                plot_bgcolor="white",
                paper_bgcolor="white",
                showlegend=False,
                xaxis=dict(visible=False, range=[0, 100]),
                yaxis=dict(visible=False),
            )

            st.markdown("**Rating Breakdown**")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

            # Star labels below bar — one column per star
            label_cols = st.columns(len(STARS))
            for star, col in zip(STARS, label_cols):
                with col:
                    st.markdown(
                        f"<div style='text-align:center; margin-top:-16px'>"
                        f"<span style='color:{RATING_COLORS[star]}; font-size:14px'><b>{star}★</b></span><br>"
                        f"<b style='font-size:14px'>{rating_pcts[star]:.0f}%</b>"
                        f"</div>",
                        unsafe_allow_html=True
                    )

        st.markdown("---")

        # ── Rating Analysis ───────────────────────────────────
        st.subheader("⭐ Rating Analysis")
        st.caption(THRESHOLD_NOTE)

        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(rating_distribution_chart(df_filtered), width="stretch")

        with col2:
            fig = rating_trend_chart(
                df_filtered,
                title="Average Rating over Time",
                color=PRIMARY_COLOR,
                reference_label="Overall avg"
            )
            if fig is None:
                st.info(f"No complete year with at least {MIN_REVIEWS_PER_YEAR} reviews in the selected range.")
            else:
                st.plotly_chart(fig, width="stretch")

# ─────────────────────────────────────────────────────────────
# TAB 2 — TOPICS
# ─────────────────────────────────────────────────────────────

with tab2:

    st.subheader("🗂️ Topic Overview")

    if df_filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
    else:
        # ── Pre-compute topic stats ───────────────────────────
        topic_stats = topic_summary(df_filtered).sort_values("avg_rating", ascending=True)

        topic_reply = df_filtered.groupby("topic_label")["has_reply"].mean().mul(100)

        # Yearly rating per topic — only topic-years with enough reviews
        topic_year_rating = (
            complete_years(df_filtered)
            .groupby(["topic_label", "year"])
            .agg(rating=("rating", "mean"), n_reviews=("rating", "size"))
            .reset_index()
        )
        topic_year_rating = topic_year_rating[topic_year_rating["n_reviews"] >= MIN_REVIEWS_PER_YEAR]

        # ── Key Findings (respect filters) ────────────────────
        problems       = topic_stats[topic_stats["category"] == "Problem"]
        most_discussed = topic_stats.loc[topic_stats["count"].idxmax()]
        best_rated     = topic_stats.loc[topic_stats["avg_rating"].idxmax()]
        pct_problems   = len(df_filtered[df_filtered["category"] == "Problem"]) / len(df_filtered) * 100

        kf1, kf2 = st.columns(2)
        with kf1:
            if problems.empty:
                st.info("No Problem topics with the current filters.")
            else:
                most_critical = problems.loc[problems["avg_rating"].idxmin()]
                st.error(f"🔴 **Most critical:** {most_critical['topic_label']} — avg {most_critical['avg_rating']:.2f}★")
            st.error(f"🔴 **{pct_problems:.0f}% of reviews** belong to Problem topics")
        with kf2:
            st.warning(f"🟡 **Most discussed:** {most_discussed['topic_label']} — {most_discussed['count']:,} reviews")
            st.success(f"🟢 **Best rated:** {best_rated['topic_label']} — avg {best_rated['avg_rating']:.2f}★")

        st.markdown("---")

        # ── Topic Priority Table ──────────────────────────────
        st.subheader("📋 Topic Priority Table")
        st.caption(
            f"Ordered by average rating — worst topics first. Click any column header to sort. "
            f"Respects the filters. Rating trend: complete years with at least {MIN_REVIEWS_PER_YEAR} "
            f"reviews in the topic."
        )

        table_rows = []
        for _, row in topic_stats.iterrows():
            topic = row["topic_label"]

            trend_data = (
                topic_year_rating[topic_year_rating["topic_label"] == topic]
                .sort_values("year")["rating"]
                .tolist()
            )

            table_rows.append({
                "Category":     CATEGORY_LABELS.get(row["category"], row["category"]),
                "Topic":        topic,
                "Avg Rating":   round(row["avg_rating"], 2),
                "Reviews":      int(row["count"]),
                "Rating Trend": trend_data,
                "Reply Rate":   round(topic_reply[topic], 1),
            })

        table_df    = pd.DataFrame(table_rows)
        max_reviews = int(topic_stats["count"].max())

        st.dataframe(
            table_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Topic":    st.column_config.TextColumn("Topic", width="large"),
                "Avg Rating": st.column_config.NumberColumn(
                    "Avg Rating", format="%.2f ★",
                    min_value=1.0, max_value=5.0, width="small"
                ),
                "Reviews": st.column_config.ProgressColumn(
                    "Reviews", format="%d",
                    min_value=0, max_value=max_reviews, width="medium"
                ),
                "Rating Trend": st.column_config.LineChartColumn(
                    "Rating Trend (by year)",
                    y_min=1.0, y_max=5.0, width="medium"
                ),
                "Reply Rate": st.column_config.ProgressColumn(
                    "Reply Rate %", format="%.1f%%",
                    min_value=0, max_value=100, width="medium"
                ),
            }
        )

    st.markdown("---")

    # ── Developer Reply Rate over Time ────────────────────────
    st.subheader("💬 Developer Reply Rate over Time")
    st.caption(
        f"All Italian reviews — not affected by filters. "
        f"Only years with at least {MIN_REVIEWS_PER_YEAR} reviews are shown."
    )
    st.plotly_chart(reply_rate_over_time_chart(df_full), width="stretch")

# ─────────────────────────────────────────────────────────────
# TAB 3 — DEEP DIVE
# ─────────────────────────────────────────────────────────────

with tab3:

    st.subheader("🔍 Topic Deep Dive")
    st.caption("Select a topic to explore in detail. All values respect the filters.")

    # Topic selector — local filter, applies only to this tab
    all_topics     = sorted(df_analysis["topic_label"].dropna().unique().tolist())
    selected_topic = st.selectbox("Select a topic", options=all_topics, index=0)

    # Category badge — immediate visual signal
    category = df_analysis.loc[df_analysis["topic_label"] == selected_topic, "category"].iloc[0]
    st.badge(category, color=CATEGORY_STYLES.get(category, DEFAULT_CATEGORY_STYLE)[1])

    # Filter for selected topic — respects sidebar filters
    topic_df = df_filtered[df_filtered["topic_label"] == selected_topic]

    if topic_df.empty:
        st.info("No reviews for this topic with the current filters.")
    else:

        st.markdown("---")

        # ── KPI Cards with sparklines ─────────────────────────
        # Counts use every complete year; averages and rates only years
        # with at least MIN_REVIEWS_PER_YEAR reviews in the topic
        st.caption(THRESHOLD_NOTE)
        reliable_topic = reliable_years(topic_df).groupby("year")
        yearly_rating  = reliable_topic["rating"].mean().tolist()
        yearly_reply   = reliable_topic["has_reply"].mean().mul(100).tolist()
        yearly_count   = complete_years(topic_df).groupby("year").size().tolist()

        col1, col2, col3 = st.columns(3)

        with col1:
            avg_rating   = topic_df["rating"].mean()
            delta_rating = avg_rating - df_filtered["rating"].mean()
            st.metric(
                label="Average Rating",
                value=f"{avg_rating:.2f} / 5.0",
                delta=f"{delta_rating:+.2f} vs overall avg",
                delta_color="normal",
                chart_data=yearly_rating,
                chart_type="line",
                border=True
            )

        with col2:
            pct_of_total = len(topic_df) / len(df_filtered) * 100
            st.metric(
                label="Reviews",
                value=f"{len(topic_df):,}",
                delta=f"{pct_of_total:.1f}% of total",
                delta_color="off",
                chart_data=yearly_count,
                chart_type="bar",
                border=True
            )

        with col3:
            st.metric(
                label="Developer Reply Rate",
                value=f"{topic_df['has_reply'].mean() * 100:.1f}%",
                help="% of reviews in this topic (with the current filters) that received a developer reply",
                chart_data=yearly_reply,
                chart_type="line",
                border=True
            )

        st.markdown("---")

        # ── Charts ────────────────────────────────────────────
        col1, col2 = st.columns(2)

        with col1:
            st.plotly_chart(rating_distribution_chart(topic_df), width="stretch")

        with col2:
            fig = rating_trend_chart(
                topic_df,
                title="Rating Trend over Time",
                color=RATING_COLORS[1],
                reference_label="Topic avg"
            )
            if fig is None:
                st.info("Not enough data to show rating trend.")
            else:
                st.plotly_chart(fig, width="stretch")

        st.markdown("---")

        # ── Most Upvoted Reviews ──────────────────────────────
        st.subheader("📌 Most Upvoted Reviews")

        # Use pre-computed top reviews — fallback to filtered data
        topic_top = df_top_reviews[df_top_reviews["topic_label"] == selected_topic]

        if topic_top.empty:
            topic_top = (
                topic_df[topic_df["thumbs_up"] > 0]
                .sort_values("thumbs_up", ascending=False)
                .head(5)
            )

        if topic_top.empty:
            st.info("No upvoted reviews available for this topic.")
        else:
            for i, (_, row) in enumerate(topic_top.iterrows()):
                upvotes = int(row["thumbs_up"])
                rating  = int(row["rating"])
                date    = str(row["date"])[:10]
                stars   = "★" * rating + "☆" * (5 - rating)

                # First review open by default
                with st.expander(
                    f"👍 {upvotes} upvotes · {stars} · {date}",
                    expanded=(i == 0)
                ):
                    st.write(row["text"])

# ─────────────────────────────────────────────────────────────
# TAB 4 — WORDS
# ─────────────────────────────────────────────────────────────

with tab4:

    st.subheader("🔤 Word Analysis")
    st.caption("Most frequent and critical words extracted from reviews.")

    if df_filtered.empty:
        st.info(EMPTY_FILTER_MESSAGE)
    else:
        # ── Prepare data ──────────────────────────────────────
        # text_lemmatized groups singular/plural variants correctly
        neg_df         = df_filtered[df_filtered["rating"] <= 2]
        pos_df         = df_filtered[df_filtered["rating"] >= 4]
        neg_lemmatized = neg_df["text_lemmatized"].tolist()
        pos_lemmatized = pos_df["text_lemmatized"].tolist()

        # ── Section 1: Top Keywords ───────────────────────────
        # Most frequent words in negative reviews only.
        # Positive keywords excluded — not useful for identifying problems.
        st.subheader("📊 Top Keywords in Negative Reviews")
        st.caption(
            f"Most frequent words in 1-2★ reviews ({len(neg_df):,} reviews) "
            f"— lemmatized to group word variants."
        )

        neg_freq = get_word_freq(neg_lemmatized, top_n=20)

        if len(neg_freq) == 0:
            st.info("No negative reviews with current filters.")
        else:
            col1, col2 = st.columns(2)

            with col1:
                neg_freq_df = pd.DataFrame(neg_freq, columns=["word", "count"])

                fig = go.Figure(go.Bar(
                    x=neg_freq_df["count"],
                    y=neg_freq_df["word"],
                    orientation="h",
                    marker_color=RATING_COLORS[1],
                    text=neg_freq_df["count"],
                    textposition="outside",
                    hovertemplate="%{y}: %{x} mentions<extra></extra>"
                ))
                fig.update_layout(
                    title=f"Top {len(neg_freq_df)} Words by Frequency",
                    xaxis_title="Frequency",
                    yaxis=dict(autorange="reversed"),
                    plot_bgcolor="white",
                    height=550,
                    margin=dict(t=40, b=40, l=0, r=60)
                )
                st.plotly_chart(fig, width="stretch")

            with col2:
                # Stopwords are already removed by get_word_freq
                wc = WordCloud(
                    width=800,
                    height=550,
                    background_color="white",
                    colormap="Reds",
                    max_words=50,
                    prefer_horizontal=0.7,
                    random_state=42
                ).generate_from_frequencies(dict(neg_freq))

                fig_wc, ax = plt.subplots(figsize=(8, 5.5))
                ax.imshow(wc, interpolation="bilinear")
                ax.axis("off")
                ax.set_title("Word Cloud — Top Keywords", fontsize=14, pad=10)
                plt.tight_layout()
                st.pyplot(fig_wc)
                plt.close(fig_wc)

        st.markdown("---")

        # ── Section 2: Critical Words ─────────────────────────
        # Words that appear disproportionately more in negative reviews
        # than positive ones — normalized frequency ratio.
        st.subheader("⚠️ Critical Words")
        st.caption(
            "Words that appear disproportionately more in negative reviews "
            "than positive ones. Score = frequency per review in negative "
            "÷ frequency per review in positive (higher = more critical)."
        )

        critical_words = get_critical_words(neg_lemmatized, pos_lemmatized, top_n=15)

        if len(critical_words) == 0:
            st.info("Not enough data to compute critical words with current filters.")
        else:
            crit_df = pd.DataFrame(critical_words)

            # Bar chart — full width
            fig = go.Figure(go.Bar(
                x=crit_df["score"],
                y=crit_df["word"],
                orientation="h",
                marker_color=RATING_COLORS[2],
                text=[f"{v:.1f}x" for v in crit_df["score"]],
                textposition="outside",
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "Score: %{x:.1f}x more in negative reviews<br>"
                    "Negative mentions: %{customdata[0]}<br>"
                    "Positive mentions: %{customdata[1]}"
                    "<extra></extra>"
                ),
                customdata=crit_df[["neg_count", "pos_count"]].values
            ))
            fig.update_layout(
                title=f"Top {len(crit_df)} Critical Words — Normalized Frequency Ratio",
                xaxis_title="Score (higher = more distinctive of negative reviews)",
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="white",
                height=500,
                margin=dict(t=40, b=40, l=0, r=80)
            )
            st.plotly_chart(fig, width="stretch")

            # Trend chart — full width below bar chart
            st.markdown("**Trend over time — top 5 critical words**")
            st.caption("Mentions per complete year for the 5 most critical words.")

            top5_critical = [row["word"] for row in critical_words[:5]]

            trend_data = []
            for word in top5_critical:
                for year, group in complete_years(df_filtered).groupby("year"):
                    mentions = group["text_lemmatized"].str.contains(
                        rf"\b{word}\b", case=False, na=False
                    ).sum()
                    trend_data.append({
                        "word":     word,
                        "year":     year,
                        "mentions": int(mentions)
                    })

            trend_df = pd.DataFrame(trend_data)

            if trend_df.empty:
                st.info("No complete year in the selected range.")
            else:
                fig = go.Figure()
                for word, color in zip(top5_critical, SERIES_COLORS):
                    word_data = trend_df[trend_df["word"] == word]
                    fig.add_trace(go.Scatter(
                        x=word_data["year"],
                        y=word_data["mentions"],
                        mode="lines+markers",
                        name=word,
                        line=dict(color=color, width=2),
                        marker=dict(size=6),
                        hovertemplate=(
                            f"{word}<br>Year: %{{x}}<br>Mentions: %{{y}}"
                            f"<extra></extra>"
                        )
                    ))

                fig.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Mentions",
                    plot_bgcolor="white",
                    height=400,
                    legend=dict(orientation="h", y=-0.2),
                    margin=dict(t=20, b=60)
                )
                st.plotly_chart(fig, width="stretch")
