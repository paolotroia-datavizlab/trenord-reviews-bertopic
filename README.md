# Trenord App Reviews: Topic Modeling with BERTopic

[![tests](https://github.com/paolotroia-datavizlab/trenord-reviews-bertopic/actions/workflows/tests.yml/badge.svg)](https://github.com/paolotroia-datavizlab/trenord-reviews-bertopic/actions/workflows/tests.yml)

What do users complain about, and what do they appreciate, in the Trenord train app? This project collects
the app's public Google Play reviews, pseudonymizes them, groups the Italian reviews into topics with BERTopic,
and publishes the results in an interactive Streamlit dashboard.

![Dashboard overview](reports/figures/dashboard_overview.png)

- **Dashboard:** https://trenord-review-analysis.streamlit.app
- **Technical documentation:** [docs/architecture.md](docs/architecture.md)
- **Glossary:** [docs/glossary.md](docs/glossary.md)
- **Data dictionary:** [columns of the published CSVs](docs/architecture.md#13-data-dictionary)

## Key findings

- **Ratings have collapsed:** the yearly average of Italian reviews fell from 3.54★ in 2015 to 1.52★ in 2025.
- **Developer replies stopped:** Trenord answered 83–100% of reviews each year until 2020, and less than 4% since 2022.
- **Top problems:** real-time train information (1,530 reviews), ticket purchase failures (1,119) and subscription
  issues (654).
- **Mostly complaints:** 84.5% of the 6,046 informative reviews fall in Problem topics.
- **What users like:** ease of use is the largest Praise topic (500 reviews, 4.53★).

## Tech stack

Python 3.13 · pandas · spaCy · lingua · BERTopic (sentence-transformers, UMAP, HDBSCAN) · matplotlib · Streamlit · Plotly

## Repository structure

```
.github/          GitHub Actions workflow that runs the tests
dashboard/        Streamlit app and its stopword list
data/processed/   published CSVs read by the dashboard
docs/             technical documentation and glossary
notebooks/        pipeline: scraping → anonymization → cleaning → analysis → topic modeling
reports/figures/  charts from the analysis and the dashboard screenshot
tests/            dashboard smoke tests (Streamlit AppTest)
```

## Quick start

```bash
python -m venv venv_trenord
venv_trenord\Scripts\activate        # macOS / Linux: source venv_trenord/bin/activate
pip install -r requirements.txt
streamlit run dashboard/app.py
```

To run the tests: `pip install pytest`, then `pytest tests/` from the repository root.

To run the full pipeline, see [Reproducibility in docs/architecture.md](docs/architecture.md#10-reproducibility).

## Data and privacy

Reviews come from an unofficial scraper and cover only part of the store's reviews (about 43% of its ratings).
Author names are removed, review ids are pseudonymized with a keyed hash, and the raw data is not published.
Details: [Privacy and data handling](docs/architecture.md#11-privacy-and-data-handling).

## License

The code is MIT-licensed ([LICENSE](LICENSE)); the license does not cover the review data, whose rights remain
with their authors and the platform.

## Author

Paolo Troia

- LinkedIn: [LINKEDIN_URL]
- Blog: [BLOG_URL]
