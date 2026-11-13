# dashboard/app.py
#
# One scrolling page about the Google Play reviews of the Trenord app.
# The page goes from the most important message to the details: header, four key numbers,
# what users complain about, how things changed over time, a topic explorer and a short
# note on the method. Every number is computed here from the files in data/processed,
# so nothing has to be updated by hand when the data changes.
#
# Run from the repository root: streamlit run dashboard/app.py

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.stats import t

# ─────────────────────────────────────────────────────────────
# PAGE CONFIGURATION
# st.set_page_config sets the browser tab title and the page layout. It must be the first
# Streamlit command of the script, otherwise Streamlit raises an error.
# layout="wide" lets the charts use the whole width of the screen, and the sidebar starts
# collapsed because this page has no sidebar.
# The colours and the font of the page itself (background, text, the active parts of the widgets) are not
# set here but in .streamlit/config.toml, the theme file. Streamlit reads it when it starts, and
# Streamlit Cloud reads the same file from the repository.
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Trenord app reviews: what users say",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# PATHS, LINKS AND COLOURS
# Paths start from this file, so the app works from any working directory.
# ─────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data" / "processed"

LINKEDIN_URL = "https://www.linkedin.com/in/paolotroia/"
BLOG_URL = "https://www.paolotroia.com"
REPO_URL = "https://github.com/paolotroia-datavizlab/trenord-reviews-bertopic"

# Trenord brand colours, used only for the interface (header banner and accents), never for data.
# The green is the background of the header bar on trenord.it (.header-top .background-top in the
# site CSS), the red is the colour of the mark in the Trenord logo image.
TRENORD_GREEN = "#006633"
TRENORD_RED = "#D71920"

# Data colours: the Okabe-Ito palette of notebooks 04 and 07, which stays readable for people
# with colour vision deficiency. One colour per category of topic.
CATEGORY_COLORS = {
    "App Issue": "#D55E00",
    "Praise": "#009E73",
    "Rail Service": "#CC79A7",
    "App Updates": "#0072B2",
}
# One colour per star rating: vermillion and orange for the low ratings, grey for 3 stars,
# light and dark green for the high ratings
RATING_COLORS = {1: "#D55E00", 2: "#E69F00", 3: "#999999", 4: "#66C5AB", 5: "#009E73"}
STARS = [1, 2, 3, 4, 5]

# The yearly lines carry no category, so they are a neutral dark grey. The incomplete last year
# is a lighter grey and dashed, so it does not read as a full year.
LINE_COLOR = "#4A4A4A"
INCOMPLETE_COLOR = "#9B9B9B"
GRID_COLOR = "#E6E6E6"

# The same font sizes in every chart
FONT_SIZE = 13
FONT_FAMILY = "sans-serif"

# Yearly numbers are shown only for years with at least this many reviews, so a year with a
# handful of reviews cannot make a peak on its own
MIN_REVIEWS_PER_YEAR = 30

# The label of the reviews set aside in notebook 07, because they only give a generic verdict
EXCLUDED_LABEL = "EXCLUDE"
# The category that holds the problems with the app, used in the opening sentence
APP_ISSUE_CATEGORY = "App Issue"
# Categories that describe a complaint, used for the title of the topic chart
COMPLAINT_CATEGORIES = ["App Issue", "Rail Service"]


# ─────────────────────────────────────────────────────────────
# LOAD DATA
# st.cache_data keeps the result of a function in memory. Streamlit reruns the whole script
# every time the user changes a widget, and without the cache it would read the CSV files again
# on every click.
# ─────────────────────────────────────────────────────────────

@st.cache_data
def load_reviews(file_name):
    reviews = pd.read_csv(DATA_DIR / file_name, encoding="utf-8-sig")
    reviews["date"] = pd.to_datetime(reviews["date"])
    reviews["year"] = reviews["date"].dt.year
    return reviews


@st.cache_data
def load_table(file_name):
    return pd.read_csv(DATA_DIR / file_name, encoding="utf-8-sig")


# All Italian reviews with their label, the generic ones included: used for ratings and replies
all_reviews = load_reviews("trenord_reviews_labeled.csv")
# Only the reviews about one of the 12 topics: used for the topic shares
topic_reviews = load_reviews("trenord_reviews_analysis.csv")
# The 5 most upvoted reviews of each topic, written by notebook 07
top_reviews = load_reviews("top_reviews_per_topic.csv")
# The 5 most typical words of each topic, written by notebook 07
topic_keywords = load_table("topic_keywords.csv")
# The agreement between the labels and my manual check, written by notebook 08
validation = load_table("validation_summary.csv").set_index("measure")


# ─────────────────────────────────────────────────────────────
# NUMBERS
# Small functions, one for each table the page needs.
# ─────────────────────────────────────────────────────────────

def find_last_complete_year(reviews):
    """The last year with data up to 31 December. The year of the last review is complete
    only if that review was written on 31 December."""
    latest = reviews["date"].max()
    if latest.month == 12 and latest.day == 31:
        return latest.year
    return latest.year - 1


def mean_with_interval(ratings):
    """Average rating and its 95% confidence interval, from the t distribution as in 07.
    The interval says how precise the average is: few reviews give a wide interval."""
    n = len(ratings)
    mean = ratings.mean()
    if n < 2:
        return mean, mean, mean
    margin = t.ppf(0.975, n - 1) * ratings.std() / n ** 0.5
    return mean, mean - margin, mean + margin


def yearly_numbers(reviews, last_complete_year):
    """Reviews, average rating and reply rate per year. Each row says whether the year is
    complete and whether it has enough reviews to be shown."""
    rows = []
    for year, year_reviews in reviews.groupby("year"):
        rows.append({
            "year": year,
            "reviews": len(year_reviews),
            "avg_rating": year_reviews["rating"].mean(),
            "reply_rate": year_reviews["has_reply"].mean() * 100,
            "complete": year <= last_complete_year,
            "enough_reviews": len(year_reviews) >= MIN_REVIEWS_PER_YEAR,
        })
    return pd.DataFrame(rows)


def topic_numbers(reviews):
    """One row per topic: reviews, share of the topic reviews, average rating with its interval
    and reply rate. Sorted from the largest topic to the smallest."""
    rows = []
    for label, label_reviews in reviews.groupby("topic_label"):
        mean, low, high = mean_with_interval(label_reviews["rating"])
        rows.append({
            "topic_label": label,
            "category": label_reviews["category"].iloc[0],
            "reviews": len(label_reviews),
            "share": len(label_reviews) / len(reviews) * 100,
            "avg_rating": mean,
            "ci_low": low,
            "ci_high": high,
            "reply_rate": label_reviews["has_reply"].mean() * 100,
        })
    table = pd.DataFrame(rows)
    return table.sort_values("reviews", ascending=False).reset_index(drop=True)


def excluded_share_per_year(reviews, years):
    """Share of the reviews of each year that were set aside as generic verdicts."""
    shares = []
    for year in years:
        year_reviews = reviews[reviews["year"] == year]
        shares.append((year_reviews["topic_label"] == EXCLUDED_LABEL).mean() * 100)
    return shares


def format_stars(value):
    return f"{value:.2f} stars"


last_complete_year = find_last_complete_year(all_reviews)
first_data_year = int(all_reviews["year"].min())
last_data_year = int(all_reviews["year"].max())

# Years used for the trends: complete years with enough reviews
years = yearly_numbers(all_reviews, last_complete_year)
trend_years = years[years["complete"] & years["enough_reviews"]].reset_index(drop=True)
first_year_row = trend_years.iloc[0]
last_year_row = trend_years.iloc[-1]
first_year = int(first_year_row["year"])
last_year = int(last_year_row["year"])
peak_reply_row = trend_years.loc[trend_years["reply_rate"].idxmax()]
peak_reply_year = int(peak_reply_row["year"])

# The incomplete last year is shown only if it has enough reviews
incomplete_years = years[~years["complete"] & years["enough_reviews"]]

topics = topic_numbers(topic_reviews)
n_italian = len(all_reviews)
n_topic_reviews = len(topic_reviews)
n_excluded = int((all_reviews["topic_label"] == EXCLUDED_LABEL).sum())
excluded_share = n_excluded / n_italian * 100
app_issue_share = topics[topics["category"] == APP_ISSUE_CATEGORY]["share"].sum()
n_model_topics = all_reviews["topic"].nunique()


# ─────────────────────────────────────────────────────────────
# CHART HELPERS
# Every chart goes through style_figure, so they all share the white background, the light grid,
# the font and the margins. The chart titles are written above each chart with st.markdown,
# because text in Markdown wraps on a phone screen and a Plotly title does not.
# ─────────────────────────────────────────────────────────────

def style_figure(fig, height):
    fig.update_layout(
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=FONT_FAMILY, size=FONT_SIZE, color="#262730"),
        margin=dict(t=10, b=10, l=10, r=10),
        hoverlabel=dict(font_size=FONT_SIZE),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, font=dict(size=FONT_SIZE)),
    )
    fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, automargin=True)
    fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, automargin=True)
    return fig


def show_chart(fig):
    # st.plotly_chart draws a Plotly figure as an interactive chart: hovering a bar or a point
    # shows its exact values. width="stretch" makes it as wide as its column.
    # theme=None keeps the style set in style_figure instead of the Streamlit chart theme.
    # The toolbar is hidden because zoom and download buttons get in the way on a phone.
    st.plotly_chart(fig, width="stretch", theme=None, config={"displayModeBar": False})


def chart_title(text):
    st.markdown(f"##### {text}")


def labelled_positions(values):
    """Positions of the yearly points that get a written value: the peak, the first year, the last
    year and the lowest point, in this order. A point next to one already chosen is skipped, so the
    labels never touch on a phone screen. Every other value is shown when hovering."""
    candidates = [values.idxmax(), values.index[0], values.index[-1], values.idxmin()]
    chosen = []
    for position in candidates:
        too_close = False
        for other in chosen:
            if abs(position - other) <= 1:
                too_close = True
        if not too_close:
            chosen.append(position)
    return chosen


def point_texts(values, formatter):
    """The text of each yearly point: the value for the chosen points, nothing for the others."""
    chosen = labelled_positions(values)
    texts = []
    for position, value in values.items():
        if position in chosen:
            texts.append(formatter(value))
        else:
            texts.append("")
    return texts


def topic_share_chart(topics):
    """Horizontal bars, one per topic, largest at the top, coloured by category. Share and
    average rating are written next to each bar, so the colour is never needed to read them.
    The topic name is written above its bar instead of on the axis: long names on the axis
    would leave almost no room for the bars on a phone."""
    fig = go.Figure()
    # One trace per category, so the legend lists the categories
    for category, color in CATEGORY_COLORS.items():
        category_topics = topics[topics["category"] == category]
        if category_topics.empty:
            continue
        bar_texts = []
        for _, row in category_topics.iterrows():
            bar_texts.append(f"{row['share']:.1f}%  ·  {row['avg_rating']:.2f}★")
        fig.add_trace(go.Bar(
            x=category_topics["share"],
            y=category_topics["topic_label"],
            orientation="h",
            name=category,
            marker_color=color,
            text=bar_texts,
            textposition="outside",
            cliponaxis=False,
            constraintext="none",
            customdata=category_topics[["reviews", "avg_rating"]].values,
            hovertemplate=(
                "%{y}<br>" + category + "<br>%{x:.1f}% of the topic reviews"
                "<br>%{customdata[0]:,} reviews<br>Average rating %{customdata[1]:.2f} stars"
                "<extra></extra>"
            ),
        ))
    # Plotly draws the first category at the bottom, so the order is reversed to put the
    # largest topic at the top
    topic_order = topics["topic_label"].tolist()
    topic_order.reverse()
    fig.update_yaxes(categoryorder="array", categoryarray=topic_order, showgrid=False,
                     showticklabels=False)
    for label in topic_order:
        fig.add_annotation(x=0, y=label, text=label, showarrow=False, xanchor="left",
                           yanchor="bottom", yshift=11, font=dict(size=FONT_SIZE))
    # Room on the right for the text next to the longest bar
    fig.update_xaxes(title_text="Share of the reviews about a topic (%)",
                     range=[0, topics["share"].max() * 1.6], ticksuffix="%")
    fig.update_layout(bargap=0.55)
    return style_figure(fig, height=700)


def trend_chart(trend_years, incomplete_years):
    """Average rating and reply rate per year, in two panels with the same year axis."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=["Average rating per year", "Reviews with a reply from the developer, per year"],
    )
    # The values are written above the peak, the first, the last and the lowest year
    rating_texts = point_texts(trend_years["avg_rating"], lambda value: f"{value:.2f}★")
    reply_texts = point_texts(trend_years["reply_rate"], lambda value: f"{value:.0f}%")
    complete_label = f"Complete years with at least {MIN_REVIEWS_PER_YEAR} reviews"
    fig.add_trace(go.Scatter(
        x=trend_years["year"], y=trend_years["avg_rating"], mode="lines+markers+text",
        text=rating_texts, textposition="top center", line=dict(color=LINE_COLOR, width=2),
        marker=dict(size=8), name=complete_label, legendgroup="complete",
        hovertemplate="%{x}: %{y:.2f} stars<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=trend_years["year"], y=trend_years["reply_rate"], mode="lines+markers+text",
        text=reply_texts, textposition="top center", line=dict(color=LINE_COLOR, width=2),
        marker=dict(size=8), name=complete_label, legendgroup="complete", showlegend=False,
        hovertemplate="%{x}: %{y:.1f}% of reviews<extra></extra>",
    ), row=2, col=1)

    # The incomplete last year: a dashed segment from the last complete year. The legend says it
    # is a partial year, and its value is written under the point, away from the last full year.
    if not incomplete_years.empty:
        partial = pd.concat([trend_years.tail(1), incomplete_years])
        partial_year = int(incomplete_years["year"].iloc[-1])
        partial_label = f"{partial_year}, partial year"
        partial_rating_texts = ["", f"{partial['avg_rating'].iloc[-1]:.2f}★"]
        partial_reply_texts = ["", f"{partial['reply_rate'].iloc[-1]:.0f}%"]
        fig.add_trace(go.Scatter(
            x=partial["year"], y=partial["avg_rating"], mode="lines+markers+text",
            text=partial_rating_texts, textposition="bottom center",
            line=dict(color=INCOMPLETE_COLOR, width=2, dash="dash"), marker=dict(size=8),
            name=partial_label, legendgroup="partial",
            hovertemplate="%{x}, partial year: %{y:.2f} stars<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=partial["year"], y=partial["reply_rate"], mode="lines+markers+text",
            text=partial_reply_texts, textposition="bottom center",
            line=dict(color=INCOMPLETE_COLOR, width=2, dash="dash"), marker=dict(size=8),
            name=partial_label, legendgroup="partial", showlegend=False,
            hovertemplate="%{x}, partial year: %{y:.1f}% of reviews<extra></extra>",
        ), row=2, col=1)

    fig.update_yaxes(title_text="Stars (1 to 5)", range=[1, 5], row=1, col=1)
    # Room under 0% for the value of the partial year
    fig.update_yaxes(title_text="Reviews (%)", range=[-20, 115], tickvals=[0, 20, 40, 60, 80, 100],
                     ticktext=["0%", "20%", "40%", "60%", "80%", "100%"], row=2, col=1)
    fig.update_xaxes(title_text="Year", dtick=1, row=2, col=1)
    fig.update_xaxes(dtick=1, row=1, col=1)
    style_figure(fig, height=640)
    # The panel titles are annotations: same font size as the rest of the chart
    fig.update_annotations(font_size=FONT_SIZE)
    fig.update_layout(margin=dict(t=60, b=10, l=10, r=10), legend=dict(y=1.06))
    return fig


def topic_share_by_year_chart(years_table, color):
    """Share of the topic reviews of each year that are about the selected topic."""
    # Values written only on the peak, the first, the last and the lowest year, so they fit on a phone
    bar_texts = point_texts(years_table["share"], lambda value: f"{value:.1f}%")
    fig = go.Figure(go.Bar(
        x=years_table["year"], y=years_table["share"], marker_color=color,
        text=bar_texts, textposition="outside", cliponaxis=False, constraintext="none",
        hovertemplate="%{x}: %{y:.1f}% of the topic reviews<extra></extra>",
    ))
    # Extra room on the left, so the value of the first bar does not touch the axis labels
    first_bar_year = years_table["year"].min()
    last_bar_year = years_table["year"].max()
    fig.update_xaxes(title_text="Year", tickvals=years_table["year"].tolist(), showgrid=False,
                     range=[first_bar_year - 1, last_bar_year + 0.6])
    fig.update_yaxes(title_text="Share of the reviews about a topic (%)", ticksuffix="%",
                     range=[0, years_table["share"].max() * 1.25])
    return style_figure(fig, height=380)


def rating_distribution_chart(ratings):
    """Share of the reviews with each number of stars, with the share written on each bar."""
    shares = ratings.value_counts(normalize=True).reindex(STARS, fill_value=0) * 100
    counts = ratings.value_counts().reindex(STARS, fill_value=0)
    star_names = []
    colors = []
    bar_texts = []
    for star in STARS:
        star_names.append(f"{star}★")
        colors.append(RATING_COLORS[star])
        bar_texts.append(f"{shares[star]:.0f}%")
    fig = go.Figure(go.Bar(
        x=star_names, y=shares.values, marker_color=colors,
        text=bar_texts, textposition="outside", cliponaxis=False, constraintext="none",
        customdata=counts.values,
        hovertemplate="%{x}: %{y:.1f}% (%{customdata:,} reviews)<extra></extra>",
    ))
    fig.update_xaxes(title_text="Rating (stars)", showgrid=False)
    fig.update_yaxes(title_text="Reviews (%)", ticksuffix="%", range=[0, shares.max() * 1.25])
    return style_figure(fig, height=380)


# ─────────────────────────────────────────────────────────────
# HEADER
# st.markdown with unsafe_allow_html=True accepts plain HTML. I use it only for the green banner,
# which Streamlit has no element for. The colours come from the Trenord site, see above.
# ─────────────────────────────────────────────────────────────

link_style = "color:white; text-decoration:underline;"
st.markdown(
    f"""
    <div style="background-color:{TRENORD_GREEN}; border-bottom:6px solid {TRENORD_RED};
                border-radius:8px; padding:22px 26px; color:white;">
      <div style="font-size:2rem; font-weight:700; line-height:1.2;">Trenord app reviews: what users say</div>
      <div style="font-size:1.1rem; margin-top:6px;">
        Google Play reviews in Italian, {first_data_year} to {last_data_year}
      </div>
      <div style="font-size:0.95rem; margin-top:12px;">
        An independent analysis by Paolo Troia ·
        <a href="{LINKEDIN_URL}" target="_blank" style="{link_style}">LinkedIn</a> ·
        <a href="{BLOG_URL}" target="_blank" style="{link_style}">Blog</a> ·
        <a href="{REPO_URL}" target="_blank" style="{link_style}">GitHub</a>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.caption("Not affiliated with or endorsed by Trenord.")

# One sentence with the main message, before the numbers
st.markdown(
    f"Users rated the app {last_year_row['avg_rating']:.2f} out of 5 stars on average in {last_year}, "
    f"down from {format_stars(first_year_row['avg_rating'])} in {first_year}. "
    f"{app_issue_share:.0f}% of the reviews about a specific topic describe a problem with the app itself, "
    f"and in {last_year} the developer replied to {last_year_row['reply_rate']:.1f}% of the reviews."
)

# ─────────────────────────────────────────────────────────────
# KEY NUMBERS
# st.columns splits the row into side by side columns; on a phone they stack one under the other.
# st.metric shows a big number with a label. The delta under it gives the context (a comparison
# with an earlier year or a reference value), and help adds a tooltip with the details.
# delta_color="off" and delta_arrow="off" make the delta a plain grey note when it is context,
# not a change.
# ─────────────────────────────────────────────────────────────

rating_change = last_year_row["avg_rating"] - first_year_row["avg_rating"]
reply_change = last_year_row["reply_rate"] - peak_reply_row["reply_rate"]
weighted = validation.loc["weighted_agreement"]
kappa = validation.loc["cohens_kappa"]

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
with kpi_1:
    st.metric(
        label="Reviews analysed",
        value=f"{n_italian:,}",
        delta=f"{n_topic_reviews:,} about a specific topic",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help=(
            f"All Google Play reviews written in Italian, {first_data_year} to {last_data_year}. "
            f"{n_topic_reviews:,} of them are about one of the {len(topics)} topics; the other "
            f"{n_excluded:,} only give a generic verdict and are left out of the topic shares."
        ),
    )
with kpi_2:
    st.metric(
        label=f"Average rating in {last_year}",
        value=format_stars(last_year_row["avg_rating"]),
        delta=f"{rating_change:+.2f} stars vs {first_year}",
        border=True,
        help=(
            f"Average of all Italian reviews written in {last_year}, from 1 to 5 stars, compared with "
            f"{first_year}, the first year with at least {MIN_REVIEWS_PER_YEAR} reviews."
        ),
    )
with kpi_3:
    st.metric(
        label=f"Developer reply rate in {last_year}",
        value=f"{last_year_row['reply_rate']:.1f}%",
        delta=f"{reply_change:+.1f} percentage points vs {peak_reply_year}",
        border=True,
        help=(
            f"Share of the Italian reviews of {last_year} that got a reply from the developer. "
            f"The peak was {peak_reply_row['reply_rate']:.1f}% in {peak_reply_year} "
            f"(years with at least {MIN_REVIEWS_PER_YEAR} reviews)."
        ),
    )
with kpi_4:
    st.metric(
        label="Labels checked by hand",
        value=f"{weighted['value'] * 100:.1f}%",
        delta=f"agree with a manual check of {int(weighted['sample_size'])} reviews",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help=(
            f"I labelled {int(weighted['sample_size'])} reviews myself without seeing the topic. "
            f"Weighted by topic size, my label and the topic match for {weighted['value'] * 100:.1f}% "
            f"of the reviews (95% interval {weighted['ci_low'] * 100:.1f}% to {weighted['ci_high'] * 100:.1f}%). "
            f"Cohen's kappa, the agreement left after removing what chance alone would give, is "
            f"{kappa['value']:.3f} (95% interval {kappa['ci_low']:.3f} to {kappa['ci_high']:.3f})."
        ),
    )

# ─────────────────────────────────────────────────────────────
# WHAT USERS COMPLAIN ABOUT
# ─────────────────────────────────────────────────────────────

st.subheader("What users complain about")
st.markdown(
    f"The reviews were grouped into {len(topics)} topics found automatically and checked by hand. "
    "This shows what people write about most, and how they rate the app when they do."
)

complaint_topics = topics[topics["category"].isin(COMPLAINT_CATEGORIES)]
top_complaint = complaint_topics.iloc[0]
chart_title(
    f"{top_complaint['topic_label']} is the most common complaint, "
    f"in {top_complaint['share']:.1f}% of the reviews about a topic"
)
show_chart(topic_share_chart(topics))
st.caption(
    f"Each bar shows the share of the {n_topic_reviews:,} reviews about a specific topic, followed by "
    f"the average rating of those reviews. Another {n_excluded:,} reviews ({excluded_share:.1f}% of the "
    f"{n_italian:,} Italian reviews) only give a generic verdict, such as a word of praise or blame, "
    "and were set aside."
)

# st.expander hides content behind a click, so the full table is there for whoever wants it
# without making the page longer
with st.expander("Show the full table"):
    table_rows = []
    for _, row in topics.iterrows():
        table_rows.append({
            "Topic": row["topic_label"],
            "Category": row["category"],
            "Reviews": row["reviews"],
            "Share (%)": row["share"],
            "Average rating (stars)": row["avg_rating"],
            "95% interval (stars)": f"{row['ci_low']:.2f} to {row['ci_high']:.2f}",
            "Reply rate (%)": row["reply_rate"],
        })
    st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Reviews": st.column_config.NumberColumn(format="%d"),
            "Share (%)": st.column_config.NumberColumn(format="%.1f%%"),
            "Average rating (stars)": st.column_config.NumberColumn(format="%.2f"),
            "Reply rate (%)": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )
    st.caption(
        "The 95% interval is the range in which the true average rating of a topic most likely lies, "
        "given how many reviews it has (t distribution). Wide intervals mean few reviews."
    )

# ─────────────────────────────────────────────────────────────
# HOW IT CHANGED
# ─────────────────────────────────────────────────────────────

st.subheader("How it changed")
st.markdown(
    "Ratings and developer replies per year, on all Italian reviews, show whether the app "
    "got better or worse for its users and how the developer reacted."
)

rating_verb = "fell" if last_year_row["avg_rating"] < first_year_row["avg_rating"] else "rose"
chart_title(
    f"Average rating {rating_verb} from {format_stars(first_year_row['avg_rating'])} in {first_year} "
    f"to {format_stars(last_year_row['avg_rating'])} in {last_year}, and replies went from "
    f"{peak_reply_row['reply_rate']:.1f}% at their peak in {peak_reply_year} to "
    f"{last_year_row['reply_rate']:.1f}%"
)
show_chart(trend_chart(trend_years, incomplete_years))
st.caption(
    f"Complete years with at least {MIN_REVIEWS_PER_YEAR} reviews; a partial year, if shown, is dashed. "
    "The two lines move together, but this does not show that one caused the other."
)

# ─────────────────────────────────────────────────────────────
# EXPLORE A TOPIC
# st.selectbox is a dropdown. When the user picks a topic, Streamlit reruns the script from the top
# and selected_topic holds the new choice, so everything below is drawn again for that topic.
# The key gives the widget a fixed name, which the tests use to find it.
# ─────────────────────────────────────────────────────────────

st.subheader("Explore a topic")
st.markdown(
    "Pick a topic to see how big it is, how it is rated, the words that define it and the "
    "reviews other users found most useful."
)

topic_options = topics["topic_label"].tolist()  # already sorted by share, largest first
selected_topic = st.selectbox("Topic", options=topic_options, index=0, key="topic")

selected_row = topics[topics["topic_label"] == selected_topic].iloc[0]
selected_reviews = topic_reviews[topic_reviews["topic_label"] == selected_topic]
selected_color = CATEGORY_COLORS.get(selected_row["category"], LINE_COLOR)

# st.container(border=True) draws a frame around everything about the selected topic,
# so it is clear which part of the page changes with the dropdown
with st.container(border=True):
    st.markdown(f"Category: {selected_row['category']}")

    metric_1, metric_2, metric_3, metric_4 = st.columns(4)
    metric_1.metric("Reviews", f"{selected_row['reviews']:,}")
    metric_2.metric("Share of the reviews about a topic", f"{selected_row['share']:.1f}%")
    metric_3.metric(
        "Average rating",
        format_stars(selected_row["avg_rating"]),
        delta=f"95% interval {selected_row['ci_low']:.2f} to {selected_row['ci_high']:.2f} stars",
        delta_color="off",
        delta_arrow="off",
        help="The range in which the true average most likely lies, given how many reviews the topic has.",
    )
    metric_4.metric("Developer reply rate", f"{selected_row['reply_rate']:.1f}%")

    selected_keywords = topic_keywords[topic_keywords["topic_label"] == selected_topic]
    selected_keywords = selected_keywords.sort_values("rank")["keyword"].tolist()
    st.markdown(f"Most typical words (in Italian): {', '.join(selected_keywords)}")

    # Share of the topic reviews per year, for complete years with enough topic reviews.
    # The share is used instead of the count, because the number of reviews changes a lot by year.
    topic_years = []
    for year in trend_years["year"]:
        year_reviews = topic_reviews[topic_reviews["year"] == year]
        if len(year_reviews) < MIN_REVIEWS_PER_YEAR:
            continue
        year_share = (year_reviews["topic_label"] == selected_topic).mean() * 100
        topic_years.append({"year": year, "share": year_share})
    topic_years = pd.DataFrame(topic_years)

    chart_left, chart_right = st.columns(2)
    with chart_left:
        peak_row = topic_years.loc[topic_years["share"].idxmax()]
        chart_title(f"Its share peaked at {peak_row['share']:.1f}% of the reviews about a topic in {int(peak_row['year'])}")
        show_chart(topic_share_by_year_chart(topic_years, selected_color))
        excluded_shares = excluded_share_per_year(all_reviews, topic_years["year"])
        st.caption(
            f"Complete years with at least {MIN_REVIEWS_PER_YEAR} reviews about a topic. The share of "
            f"reviews set aside as generic changes by year ({min(excluded_shares):.1f}% to "
            f"{max(excluded_shares):.1f}%), so year to year comparisons need care."
        )
    with chart_right:
        star_shares = selected_reviews["rating"].value_counts(normalize=True) * 100
        top_star = int(star_shares.idxmax())
        chart_title(f"{star_shares.max():.0f}% of these reviews give {top_star} star{'s' if top_star > 1 else ''}")
        show_chart(rating_distribution_chart(selected_reviews["rating"]))

    st.markdown("##### Most upvoted reviews")
    st.caption("The reviews of this topic that other users marked as helpful most often, as written.")
    selected_top = top_reviews[top_reviews["topic_label"] == selected_topic]
    if selected_top.empty:
        # Fallback if the file has no reviews for this topic: the most upvoted ones in the data
        selected_top = selected_reviews[selected_reviews["thumbs_up"] > 0]
        selected_top = selected_top.sort_values("thumbs_up", ascending=False).head(5)

    if selected_top.empty:
        st.info("No upvoted reviews for this topic.")
    else:
        position = 0
        for _, row in selected_top.iterrows():
            stars = "★" * int(row["rating"]) + "☆" * (5 - int(row["rating"]))
            date = row["date"].strftime("%Y-%m-%d")
            # The first review is open, so the section never looks empty
            with st.expander(f"{int(row['thumbs_up'])} upvotes · {stars} · {date}", expanded=(position == 0)):
                st.write(row["text"])
            position += 1

# ─────────────────────────────────────────────────────────────
# ABOUT THIS ANALYSIS
# Technical terms appear only here, each explained in one sentence.
# ─────────────────────────────────────────────────────────────

raw = validation.loc["raw_agreement"]
st.subheader("About this analysis")
st.markdown(
    f"I collected the public Google Play reviews of the Trenord app and kept the "
    f"{n_italian:,} written in Italian. BERTopic, a method that turns each review into a vector of its "
    f"meaning with a language model and groups reviews whose vectors are close, found {n_model_topics} "
    f"groups. I read each group with its most typical words (c-TF-IDF, a score of how much more often "
    f"a word appears in one group than in the others), named it and joined groups about the same "
    f"theme, ending with {len(topics)} topics. Reviews that only give a generic verdict "
    f"({n_excluded:,} reviews) were set aside."
)
st.markdown(
    f"To check the labels, I labelled a sample of {int(raw['sample_size'])} reviews myself, "
    f"without seeing their topic. The sample was stratified, which means the same number of reviews "
    f"was drawn from each group, so small topics are checked as well as large ones. My label and the "
    f"topic match for {raw['value'] * 100:.1f}% of the sample (95% interval {raw['ci_low'] * 100:.1f}% "
    f"to {raw['ci_high'] * 100:.1f}%), and for {weighted['value'] * 100:.1f}% "
    f"({weighted['ci_low'] * 100:.1f}% to {weighted['ci_high'] * 100:.1f}%) once each group is weighted "
    f"by its size, which estimates the agreement on all reviews. Cohen's kappa, the agreement left after "
    f"removing what chance alone would give, is {kappa['value']:.3f} ({kappa['ci_low']:.3f} to "
    f"{kappa['ci_high']:.3f}). I also trained the model again with other random seeds for UMAP, the step "
    f"that compresses the meaning vectors before grouping them, and most reviews kept their label."
)
st.markdown(
    f"The analysis has limits. The reviews come from Google Play only, not from the App Store. Unhappy users write "
    f"reviews more often than happy ones, so the shares describe what reviewers write, not the "
    f"experience of every user. The {excluded_share:.1f}% of reviews that only give a generic verdict "
    f"are not in the topics. The labels were checked by one person, me, so the check measures "
    f"agreement with one reader."
)
st.markdown(f"Code, notebooks and full method: [GitHub repository]({REPO_URL}).")
st.caption("Not affiliated with or endorsed by Trenord.")
