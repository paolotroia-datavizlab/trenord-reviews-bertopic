# dashboard/app.py
#
# One scrolling page about the Google Play reviews of the Trenord app.
# The page goes from the most important message to the details: header, three key numbers,
# what users write about, how things changed over time, what users ask for, a topic explorer
# and a short note on the method. Every number is computed here from the files in data/processed,
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
    page_title="Trenord App Reviews - What Users Say",
    page_icon="🚆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# The wide layout stretches the page over the whole screen, and on a large monitor a line of
# text becomes much longer than about 90 characters, which is hard to read: the eye loses the
# start of the next line. This small CSS rule keeps the main content at most 1200 pixels wide
# and centred. stMainBlockContainer is the name Streamlit gives to the box that holds the page.
st.markdown(
    """
    <style>
    [data-testid="stMainBlockContainer"] {
        max-width: 1200px;
        margin: 0 auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# PATHS, LINKS AND COLOURS
# Paths start from this file, so the app works from any working directory.
# ─────────────────────────────────────────────────────────────

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data" / "processed"

LINKEDIN_URL = "https://www.linkedin.com/in/paolotroia/"
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
# st.badge accepts only a few named colours, so each category uses the named colour closest to
# its colour above. A category missing from this dictionary gets a grey badge.
CATEGORY_BADGE_COLORS = {
    "App Issue": "red",
    "Praise": "green",
    "Rail Service": "violet",
    "App Updates": "blue",
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

# The two years named in the title of the trend chart: the last year with replies to almost every
# review, and the first year of the lowest ratings. The page checks both sentences against the
# yearly values before writing them.
LAST_REPLY_YEAR = 2020
FIRST_LOW_RATING_YEAR = 2023

# The label of the reviews set aside in notebook 07, because they only give a generic verdict
EXCLUDED_LABEL = "EXCLUDE"
# The category that holds the problems with the app, used in the second key number card
APP_ISSUE_CATEGORY = "App Issue"

# The feature request themes left out of the table of what users ask for. The first is for
# reports of something broken and the last for wishes too vague to name a feature, so neither is
# a request for something new; notebook 09 also found that the complaints theme almost never
# holds a real request.
NOT_NEW_REQUEST_THEMES = [
    "Fix something that does not work",
    "Complaints and support in the app",
    "Too vague to classify",
]
# What users ask for in each theme, in a few plain words. I wrote these phrases after reading the
# requests of each theme; the theme names come from notebook 09. A theme missing from this
# dictionary still gets its row in the table, with an empty phrase.
REQUEST_PHRASES = {
    "Train information": "Platform, cause of delays and cancellations shown clearly",
    "Notifications": "Alerts for my trains, at times I choose",
    "Subscriptions and passes": "Buying, renewing and digitising passes and cards in the app",
    "Ticket purchase": "More ticket types and an easier way to buy them",
    "Payments and invoices": "More payment methods, saved cards and invoices",
    "Usability and design": "A simpler, clearer app, also in English",
    "Tickets and QR codes": "Downloading, sharing or printing tickets and QR codes",
    "Login and account": "Staying logged in, biometric login, editing the profile",
    "Favourites, widgets and trip planning": "Widgets, favourite routes and a better search",
}


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
# One row per feature request theme, with the estimated number of real requests and its
# interval, written by notebook 09. It holds counts and shares only, no review text.
feature_requests = load_table("feature_request_themes.csv")
# One real review per theme, chosen in notebook 09 with a fixed rule: theme, text, rating,
# thumbs up and year
request_examples = load_table("feature_request_examples.csv")


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
    """One row per topic: reviews, share of the topic reviews and average rating with its
    interval. Sorted from the largest topic to the smallest."""
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


def recent_topic_shares(reviews, recent_years):
    """Share of each topic among the topic reviews of the recent years, as in the recency check of
    notebook 07. A topic with no review in those years gets 0."""
    recent_reviews = reviews[reviews["year"].isin(recent_years)]
    shares = {}
    for label in reviews["topic_label"].unique():
        shares[label] = (recent_reviews["topic_label"] == label).mean() * 100
    return shares


def new_request_numbers(requests):
    """The feature request themes for the table: only requests for something new, and only the
    themes with an estimate. A theme with too few reviews checked by hand has an empty estimate in
    the file, which pandas reads as NaN, so notna() keeps the others. Sorted by the lower end of
    the interval, highest first: the firmest estimates come first, not the largest."""
    is_new = ~requests["theme"].isin(NOT_NEW_REQUEST_THEMES)
    has_estimate = requests["estimated_requests"].notna()
    chosen = requests[is_new & has_estimate]
    return chosen.sort_values("estimated_low", ascending=False).reset_index(drop=True)


def format_estimate(row):
    """The estimate and its 95% interval in words, each rounded once to a whole number of reviews,
    for example "about 107, between 81 and 111"."""
    return (f"about {row['estimated_requests']:.0f}, "
            f"between {row['estimated_low']:.0f} and {row['estimated_high']:.0f}")


def escape_markdown(text):
    """A review is written by a user, so it can hold characters that Markdown reads as formatting:
    a * would end the italics early, and a $ would start a formula. A backslash in front of each
    one makes Markdown show it as it is. A line break would also end the italics, so it becomes a
    space."""
    escaped = text.replace("\\", "\\\\")
    for character in "*_`$#[]<>|~":
        escaped = escaped.replace(character, "\\" + character)
    return escaped.replace("\n", " ")


def format_stars(value):
    return f"{value:.2f} stars"


def star_symbols(rating):
    """A rating as five stars, filled up to the rating: 3 gives ★★★☆☆."""
    return "★" * int(rating) + "☆" * (5 - int(rating))


last_complete_year = find_last_complete_year(all_reviews)
# Month and year of the first and the last review, for the subtitle. month_name() gives the
# month in English whatever the language of the computer.
first_review_date = all_reviews["date"].min()
last_review_date = all_reviews["date"].max()
first_review_month = f"{first_review_date.month_name()} {first_review_date.year}"
last_review_month = f"{last_review_date.month_name()} {last_review_date.year}"

# Years used for the trends: complete years with enough reviews
years = yearly_numbers(all_reviews, last_complete_year)
trend_years = years[years["complete"] & years["enough_reviews"]].reset_index(drop=True)
first_year_row = trend_years.iloc[0]
last_year_row = trend_years.iloc[-1]
first_year = int(first_year_row["year"])
last_year = int(last_year_row["year"])

# The incomplete last year is shown only if it has enough reviews
incomplete_years = years[~years["complete"] & years["enough_reviews"]]

# The months covered by the partial year, for example "Jan-Aug 2026": the month of its first
# review and the month of its last one. month_name()[:3] gives the short English month name
# whatever the language of the computer. partial_year_text stays empty if there is no partial year.
partial_year_text = ""
if not incomplete_years.empty:
    partial_year = int(incomplete_years["year"].iloc[-1])
    partial_dates = all_reviews.loc[all_reviews["year"] == partial_year, "date"]
    first_month = partial_dates.min().month_name()[:3]
    last_month = partial_dates.max().month_name()[:3]
    if first_month == last_month:
        partial_year_text = f"{last_month} {partial_year}"
    else:
        partial_year_text = f"{first_month}-{last_month} {partial_year}"

# The year of the key number cards: the partial year, if it already has enough reviews, so the
# cards show the newest data; otherwise the last full year. card_year_text says which, and goes
# into the labels and the help texts.
if incomplete_years.empty:
    card_year_row = last_year_row
    card_year_text = f"{last_year}"
else:
    card_year_row = incomplete_years.iloc[-1]
    card_year_text = partial_year_text

topics = topic_numbers(topic_reviews)
n_italian = len(all_reviews)
n_topic_reviews = len(topic_reviews)
n_excluded = int((all_reviews["topic_label"] == EXCLUDED_LABEL).sum())
excluded_share = n_excluded / n_italian * 100
app_issue_share = topics[topics["category"] == APP_ISSUE_CATEGORY]["share"].sum()

# The recent period of notebook 07: the last two complete years, for example 2024 and 2025.
# The column name of the full table is written from the same two years.
recent_years = [last_complete_year - 1, last_complete_year]
recent_shares = recent_topic_shares(topic_reviews, recent_years)
recent_share_column = f"Share {recent_years[0]}-{recent_years[1]} (%)"

new_requests = new_request_numbers(feature_requests)


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
    """Horizontal bars, one per topic, largest at the top, coloured by category. The share is
    written next to each bar, so the colour is never needed to read it, and the x axis with its
    grid lines is left out: with every value written, it would only add lines to read past.
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
            bar_texts.append(f"{row['share']:.1f}%")
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
    fig.update_yaxes(categoryorder="array", categoryarray=topic_order, showticklabels=False)
    for label in topic_order:
        fig.add_annotation(x=0, y=label, text=label, showarrow=False, xanchor="left",
                           yanchor="bottom", yshift=11, font=dict(size=FONT_SIZE))
    fig.update_layout(bargap=0.55)
    style_figure(fig, height=640)
    # These axis settings come after style_figure, because style_figure turns the grid on.
    # No x axis and no vertical grid lines. The range ends just after the longest bar, with room
    # for its label: 18% more than the bar is enough for "25.0%" on a phone screen.
    fig.update_xaxes(visible=False, showgrid=False, range=[0, topics["share"].max() * 1.18])
    # No horizontal grid lines either: they would run through the topic names above the bars.
    fig.update_yaxes(showgrid=False)
    return fig


def trend_chart(trend_years, incomplete_years, partial_year_text):
    """Average rating and reply rate per year, in two panels with the same year axis.
    partial_year_text names the partial year in the legend, for example "Jan-Aug 2026"."""
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.12,
        subplot_titles=["Average rating per year", "Reviews with a reply, per year"],
    )
    # The values are written above the peak, the first, the last and the lowest year
    rating_texts = point_texts(trend_years["avg_rating"], lambda value: f"{value:.2f}★")
    # The reply rates have one decimal, like the key number cards
    reply_texts = point_texts(trend_years["reply_rate"], lambda value: f"{value:.1f}%")
    # The legend says only "Year": the first year, 2015, starts in May, so it is not a full year
    # either. The dashed line of the last year names its months in the legend.
    complete_label = "Year"
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

    # The incomplete last year: a dashed segment from the last complete year. The legend names
    # the months it covers, and its value is written under the point, away from the last full year.
    # The segment starts at the last full year, so the hover names each point with customdata:
    # the year for the first point, the months of the partial year for the second.
    if not incomplete_years.empty:
        partial = pd.concat([trend_years.tail(1), incomplete_years])
        hover_names = [f"{int(partial['year'].iloc[0])}", partial_year_text]
        partial_rating_texts = ["", f"{partial['avg_rating'].iloc[-1]:.2f}★"]
        partial_reply_texts = ["", f"{partial['reply_rate'].iloc[-1]:.1f}%"]
        fig.add_trace(go.Scatter(
            x=partial["year"], y=partial["avg_rating"], mode="lines+markers+text",
            text=partial_rating_texts, textposition="bottom center",
            line=dict(color=INCOMPLETE_COLOR, width=2, dash="dash"), marker=dict(size=8),
            name=partial_year_text, legendgroup="partial", customdata=hover_names,
            hovertemplate="%{customdata}: %{y:.2f} stars<extra></extra>",
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=partial["year"], y=partial["reply_rate"], mode="lines+markers+text",
            text=partial_reply_texts, textposition="bottom center",
            line=dict(color=INCOMPLETE_COLOR, width=2, dash="dash"), marker=dict(size=8),
            name=partial_year_text, legendgroup="partial", showlegend=False, customdata=hover_names,
            hovertemplate="%{customdata}: %{y:.1f}% of reviews<extra></extra>",
        ), row=2, col=1)

    fig.update_yaxes(title_text="Stars (1 to 5)", range=[1, 5], row=1, col=1)
    # Room under 0% for the value of the partial year
    fig.update_yaxes(title_text="Reviews with a reply (%)", range=[-20, 115], tickvals=[0, 20, 40, 60, 80, 100],
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
    fig.update_yaxes(title_text="Share of reviews (%)", ticksuffix="%",
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
# st.markdown with unsafe_allow_html=True accepts plain HTML. I use it only where Streamlit has no
# element of its own: the width rule above, this green banner and the footer at the end of the page.
# The colours come from the Trenord site, see above.
# ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="background-color:{TRENORD_GREEN}; border-bottom:6px solid {TRENORD_RED};
                border-radius:8px; padding:22px 26px; margin-bottom:16px; color:white;">
      <div style="font-size:2rem; font-weight:700; line-height:1.2;">Trenord App Reviews - What Users Say</div>
      <div style="font-size:1.1rem; margin-top:6px;">
        {n_italian:,} Google Play reviews in Italian, {first_review_month} to {last_review_month}
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# KEY NUMBERS
# st.columns splits the row into side by side columns; on a phone they stack one under the other.
# st.metric shows a big number with a label. The delta under it gives the context, here a
# reference value, and help adds a tooltip with the details.
# delta_color="off" and delta_arrow="off" make the delta a plain grey note without an arrow: it is
# a value to compare with, not a change to colour as good or bad.
# Each number is rounded once into a variable, and both the value and the note use it, so the
# number on the card and the number in a sentence can never disagree by a rounding.
# ─────────────────────────────────────────────────────────────

rating_now = round(card_year_row["avg_rating"], 2)
rating_then = round(first_year_row["avg_rating"], 2)
app_issue_share_shown = round(app_issue_share, 1)
reply_now = round(card_year_row["reply_rate"], 1)
reply_then = round(first_year_row["reply_rate"], 1)

kpi_1, kpi_2, kpi_3 = st.columns(3)
with kpi_1:
    st.metric(
        label=f"Average rating, {card_year_text}",
        value=f"{rating_now:.2f} stars",
        delta=f"{rating_then:.2f} in {first_year}",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help=f"Average stars given in reviews written in {card_year_text}.",
    )
with kpi_2:
    st.metric(
        label="Reviews about app problems",
        value=f"{app_issue_share_shown:.1f}%",
        delta=f"excludes {n_excluded:,} generic reviews",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help=(
            "Share of reviews that describe a problem with the app. "
            "Generic reviews like 'great' or 'terrible' are left out."
        ),
    )
with kpi_3:
    st.metric(
        label=f"Reviews with a reply, {card_year_text}",
        value=f"{reply_now:.1f}%",
        delta=f"{reply_then:.1f}% in {first_year}",
        delta_color="off",
        delta_arrow="off",
        border=True,
        help=f"Share of reviews written in {card_year_text} that got a reply.",
    )

# ─────────────────────────────────────────────────────────────
# WHAT USERS WRITE ABOUT
# ─────────────────────────────────────────────────────────────

st.subheader("What users write about")
st.markdown(
    f"Each review was assigned to one of {len(topics)} topics. The bars show each topic's share of the "
    f"{n_topic_reviews:,} reviews about a specific topic."
)

# The title turns the share of the largest topic into "1 review in n", which is easier to picture
# than a percentage: 25% becomes 1 review in 4. n is the inverse of the share, rounded.
largest_topic = topics.iloc[0]
one_in_n = round(100 / largest_topic["share"])
chart_title(f"{largest_topic['topic_label']} is the most common topic: 1 review in {one_in_n}")
show_chart(topic_share_chart(topics))
st.caption(
    f"Another {n_excluded:,} reviews ({excluded_share:.1f}% of the {n_italian:,} Italian reviews) only give "
    "a generic verdict, such as a word of praise or blame, and were set aside. The average rating of "
    "each topic is in the full table."
)

# st.expander hides content behind a click, so the full table is there for whoever wants it
# without making the page longer
# The table has no reply rate. One rate over all years would mix the years with replies to almost
# every review and the years after 2020 with almost none, so it would describe no real year.
with st.expander("Show the full table"):
    table_rows = []
    for _, row in topics.iterrows():
        table_rows.append({
            "Topic": row["topic_label"],
            "Category": row["category"],
            "Reviews": row["reviews"],
            "Share (%)": row["share"],
            recent_share_column: recent_shares[row["topic_label"]],
            "Average rating (stars)": row["avg_rating"],
            "95% interval (stars)": f"{row['ci_low']:.2f} to {row['ci_high']:.2f}",
        })
    st.dataframe(
        pd.DataFrame(table_rows),
        hide_index=True,
        width="stretch",
        column_config={
            "Reviews": st.column_config.NumberColumn(format="%d"),
            "Share (%)": st.column_config.NumberColumn(format="%.1f%%"),
            recent_share_column: st.column_config.NumberColumn(format="%.1f%%"),
            "Average rating (stars)": st.column_config.NumberColumn(format="%.2f"),
        },
    )
    st.caption(
        f"The share {recent_years[0]}-{recent_years[1]} is the topic's share of the reviews about a topic "
        "written in the last two complete years. "
        "The 95% interval is the range in which the true average rating of a topic most likely lies, "
        "given how many reviews it has (t distribution). Wide intervals mean few reviews."
    )

# ─────────────────────────────────────────────────────────────
# HOW IT CHANGED
# ─────────────────────────────────────────────────────────────

st.subheader("How it changed")
st.markdown("Average rating and share of reviews with a reply, year by year.")

# The title makes two claims, so each one is checked against the yearly values first, on every
# year with enough reviews, the partial year included. A sentence goes into the title only if its
# check is true, so new data can never make the title say something false.
shown_years = years[years["enough_reviews"]]
# Replies: every year after LAST_REPLY_YEAR has a lower reply rate than LAST_REPLY_YEAR itself
reply_rate_then = shown_years.loc[shown_years["year"] == LAST_REPLY_YEAR, "reply_rate"]
reply_rates_after = shown_years.loc[shown_years["year"] > LAST_REPLY_YEAR, "reply_rate"]
replies_dropped = (
    len(reply_rate_then) == 1
    and len(reply_rates_after) > 0
    and (reply_rates_after < reply_rate_then.iloc[0]).all()
)
# Ratings: the best year from FIRST_LOW_RATING_YEAR on is still below the worst year before it
ratings_before = shown_years.loc[shown_years["year"] < FIRST_LOW_RATING_YEAR, "avg_rating"]
ratings_from = shown_years.loc[shown_years["year"] >= FIRST_LOW_RATING_YEAR, "avg_rating"]
ratings_lowest = (
    len(ratings_before) > 0
    and len(ratings_from) > 0
    and ratings_from.max() < ratings_before.min()
)
title_sentences = []
if replies_dropped:
    title_sentences.append(f"Replies almost stopped after {LAST_REPLY_YEAR}.")
if ratings_lowest:
    title_sentences.append(f"Ratings have been at their lowest since {FIRST_LOW_RATING_YEAR}.")
if not title_sentences:
    title_sentences.append("Average rating and reviews with a reply per year")
chart_title(" ".join(title_sentences))
show_chart(trend_chart(trend_years, incomplete_years, partial_year_text))
st.caption("The two lines move together, but this does not prove one caused the other.")

# ─────────────────────────────────────────────────────────────
# WHAT USERS ASK FOR
# Notebook 09 found the reviews that ask for something new with an LLM, put each in a theme and
# checked a sample by hand. The LLM also flags many reports of broken features, so the count of
# each theme was multiplied by the share of real requests measured in the sample: the table shows
# that estimate, not the raw count.
# ─────────────────────────────────────────────────────────────

st.subheader("What users ask for")
st.markdown(
    "An LLM found the reviews that ask for something new, and I checked them against my own labels."
)

# The title names the clearest request: the theme with the highest lower end of the interval.
# Even in the least favourable case it keeps more real requests than any other theme, although
# another theme may have a larger estimate. new_requests is sorted by that lower end, so the
# clearest request is its first row.
clearest = new_requests.iloc[0]
chart_title(f"The clearest request: {clearest['theme']}")

# A table, not a chart: the phrases say what users want, and the ranges are easier to read as
# words than as error bars. st.table draws a static table whose long cells wrap onto more lines,
# so it fits a phone screen; st.dataframe would cut them. hide_index hides the row numbers.
request_rows = []
for _, row in new_requests.iterrows():
    request_rows.append({
        "Theme": row["theme"],
        "What users ask for": REQUEST_PHRASES.get(row["theme"], ""),
        "Estimated reviews": format_estimate(row),
    })
st.table(pd.DataFrame(request_rows), hide_index=True)

# The reviews checked by hand behind these estimates: the flagged reviews of my coded sample
# that fall in these themes
n_checked = int(new_requests["sample_flagged"].sum())
st.caption(
    f"Estimated from {n_checked} reviews I checked by hand. A wide range means the estimate is uncertain."
)

# One real review per theme, in the order of the table. dict(zip(...)) pairs each theme with the
# row number of its example; a theme with no example is skipped.
example_row_by_theme = dict(zip(request_examples["theme"], request_examples.index))
with st.expander("See a real review for each theme"):
    st.markdown("Reviews are in Italian, as written by users.")
    for theme_name in new_requests["theme"]:
        if theme_name not in example_row_by_theme:
            continue
        example = request_examples.loc[example_row_by_theme[theme_name]]
        # Two spaces before a line break keep the three lines in one paragraph: the theme in
        # bold, the review in italics, then its stars and year
        st.markdown(
            f"**{theme_name}**  \n"
            f"*{escape_markdown(example['text'])}*  \n"
            f"{star_symbols(example['rating'])} · {int(example['year'])}"
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
    # st.badge draws the category as a small coloured label, in the named colour closest to the
    # colour of the category in the charts
    selected_category = selected_row["category"]
    st.badge(selected_category, color=CATEGORY_BADGE_COLORS.get(selected_category, "gray"))

    # Three metrics. There is no reply rate here: one rate over all years would mix the years
    # with replies to almost every review and the years after 2020 with almost none.
    metric_1, metric_2, metric_3 = st.columns(3)
    metric_1.metric("Reviews", f"{selected_row['reviews']:,}")
    metric_2.metric("Share of the reviews about a topic", f"{selected_row['share']:.1f}%")
    metric_3.metric(
        "Average rating",
        format_stars(selected_row["avg_rating"]),
        help=f"95% confidence interval: {selected_row['ci_low']:.2f} to {selected_row['ci_high']:.2f} stars.",
    )

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
        if topic_years.empty:
            # With no year to show, idxmax and min would fail on an empty table, so the page
            # shows a short message instead of the chart and its caption
            st.info("Not enough reviews per year to show how the share of this topic changed.")
        else:
            peak_row = topic_years.loc[topic_years["share"].idxmax()]
            chart_title(f"Highest share in {int(peak_row['year'])}: {peak_row['share']:.1f}%")
            show_chart(topic_share_by_year_chart(topic_years, selected_color))
            # The shares leave out the generic reviews, and their share is not the same every year,
            # so the caption gives its lowest and highest yearly value
            excluded_shares = excluded_share_per_year(all_reviews, topic_years["year"])
            st.caption(
                f"Generic reviews left out vary by year ({min(excluded_shares):.1f}% to "
                f"{max(excluded_shares):.1f}%), so compare years with care."
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
            stars = star_symbols(row["rating"])
            date = row["date"].strftime("%Y-%m-%d")
            # The first review is open, so the section never looks empty
            with st.expander(f"{int(row['thumbs_up'])} upvotes · {stars} · {date}", expanded=(position == 0)):
                st.write(row["text"])
            position += 1

# ─────────────────────────────────────────────────────────────
# ABOUT THIS ANALYSIS
# Three short paragraphs: what was done, the limits, where to find the rest. Every number is read
# from the data files, so the text stays right if the data change.
# ─────────────────────────────────────────────────────────────

# The weighted agreement estimates the agreement on all reviews: each group of the sample counts
# as much as its size in the data
weighted = validation.loc["weighted_agreement"]
st.subheader("About this analysis")
st.markdown(
    f"{n_italian:,} Italian reviews from Google Play, grouped into {len(topics)} topics with BERTopic "
    f"and named by hand. {n_excluded:,} generic reviews like \"great\" or \"terrible\" are left out. "
    f"A manual check of {int(weighted['sample_size'])} reviews agrees with the topics in "
    f"{weighted['value'] * 100:.1f}% of cases. "
    "Feature requests were found with an LLM and checked against a sample I labelled myself."
)
st.markdown(
    "Google Play only. Unhappy users write more, so the shares describe reviewers, not all users."
)
st.markdown(f"Code and full method on [GitHub]({REPO_URL}).")

# ─────────────────────────────────────────────────────────────
# FOOTER
# One small centred line with my name and two links, at the very end of the page.
# Markdown cannot centre text, so this is a short piece of HTML too.
# ─────────────────────────────────────────────────────────────

st.markdown(
    f"""
    <div style="text-align:center; font-size:0.85rem; color:#6B6B6B; margin-top:32px;">
      Paolo Troia ·
      <a href="{LINKEDIN_URL}" target="_blank">LinkedIn</a> ·
      <a href="{REPO_URL}" target="_blank">GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
