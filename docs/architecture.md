# Trenord App Reviews: Topic Modeling with BERTopic

This document explains how the project is built and why. It is a study guide to read side by side with the
notebooks, and a technical source for a future article.

- Parameters are copied from the code; numbers come from the final pipeline run.
- The data snapshot is the scrape whose latest review is dated 2026-08-04.
- No review texts or author names appear here.
- Technical terms link to [glossary.md](glossary.md) the first time they appear.

**Cell numbers** count every cell of a notebook from the top, markdown cells included, starting at 1.

---

## 1. Overview

### Goal and research question

The Trenord app (`it.nordcom.app`) is the official app of Lombardy's regional railway operator. It is used to check
train status, buy tickets and renew subscriptions. The project asks:

> **What do users of the Trenord app complain about and what do they appreciate, how has their satisfaction
> evolved over time, and how has the operator responded?**

The study uses the public Google Play Store reviews:
- ratings and developer replies are analysed over time;
- the Italian review texts are grouped into topics with [BERTopic](glossary.md#bertopic);
- each topic gets a label and one of four [categories](glossary.md#category): App Issue, Praise, Rail Service and
  App Updates.

### Data flow

```mermaid
flowchart TD
    PS["Google Play Store<br/>it.nordcom.app"] -->|"google-play-scraper, Sort.NEWEST"| N01["01 scraping"]
    N01 --> RAW[("trenord_reviews_raw.csv<br/>local only")]
    RAW --> N02["02 anonymization"]
    ENV[".env with PSEUDO_KEY<br/>local only"] -.-> N02
    N02 --> ANON[("trenord_reviews_anon.csv<br/>local only")]
    ANON --> N03["03 cleaning"]
    N03 --> CLEAN[("trenord_reviews_clean.csv<br/>local only")]
    CLEAN --> N04["04 exploratory analysis"]
    N04 --> PNG["six charts in reports/figures"]
    CLEAN --> N05["05 model selection"]
    N05 --> TABLES["metric tables, no files"]
    CLEAN --> N06["06 training"]
    N06 --> TOPICS[("trenord_reviews_topics.csv<br/>local only")]
    N06 --> MODEL[("bertopic_model_trained<br/>local only")]
    TOPICS --> N07["07 labeling and export"]
    MODEL --> N07
    N07 --> LAB[("trenord_reviews_labeled.csv")]
    N07 --> ANA[("trenord_reviews_analysis.csv")]
    N07 --> TOP[("top_reviews_per_topic.csv")]
    N07 --> FINAL[("bertopic_model_merged<br/>local only")]
    N07 --> PNG2["four charts in reports/figures"]
    N07 --> KW[("topic_keywords.csv")]
    CLEAN --> N08["08 label validation"]
    LAB --> N08
    N08 --> STAB["stability and agreement tables"]
    N08 --> SAMPLE[("validation_sample.xlsx, validation_key.csv,<br/>validation_disagreements.csv<br/>labeling/, local only")]
    N08 --> PNG3["chart_label_confusion.png<br/>reports/figures"]
    N08 --> VS[("validation_summary.csv")]
    LAB --> DASH["dashboard/app.py, Streamlit"]
    ANA --> DASH
    TOP --> DASH
    KW --> DASH
    VS --> DASH
```

### Produced files

All files are in `data/processed/` unless stated otherwise. Row counts are in [Key numbers](#2-key-numbers). The
notebooks themselves start with a one-sentence header only, so the input and output files of each notebook are listed
in its section below.

| File | Producer | Published |
|---|---|---|
| `data/raw/trenord_reviews_raw.csv` | 01 | no (gitignored) |
| `trenord_reviews_anon.csv` | 02 | no |
| `trenord_reviews_clean.csv` | 03 | no |
| six charts in `reports/figures/` (§6) | 04 | yes |
| `reports/figures/dashboard_overview.png` (dashboard screenshot) | - | yes |
| none (metric tables in the notebook only) | 05 | - |
| `trenord_reviews_topics.csv` | 06 | no |
| `bertopic_model_trained/` | 06 | no |
| `trenord_reviews_labeled.csv`, `trenord_reviews_analysis.csv`, `top_reviews_per_topic.csv` | 07 | yes |
| `topic_keywords.csv` (top 5 keywords of each topic, for the dashboard) | 07 | yes |
| `bertopic_model_merged/` | 07 | no |
| `reports/figures/chart_reviews_per_topic.png`, `chart_avg_rating_per_topic.png`, `chart_keywords_per_topic.png`, `chart_topic_priority.png` | 07 | yes |
| `labeling/validation_sample.xlsx`, `labeling/validation_key.csv` (written only once, §10) | 08 | no (gitignored, contain review texts) |
| `labeling/validation_disagreements.csv` (written again on every run, §10) | 08 | no (gitignored, contains review texts) |
| `reports/figures/chart_label_confusion.png` | 08 | yes |
| `validation_summary.csv` (agreement numbers, for the dashboard) | 08 | yes |

All CSVs are written with `encoding="utf-8-sig"` and `index=False`.

There are two BERTopic models. `bertopic_model_trained/` is trained by 06 and read by 07. `bertopic_model_merged/` is the
same model after the merges in 07, saved for reuse; no other step reads it (§9).

---

## 2. Key numbers

This table is the single source of numbers for the article. **All languages** figures come from notebook 04.
**Italian only** figures come from `trenord_reviews_labeled.csv` (07), the file the dashboard reads. Yearly figures
use complete years (up to 2025), except the row for Jan-Aug 2026, the partial year shown by the dashboard.

### Data and coverage

| Measure | Value |
|---|---|
| Store ratings at scraping time / reviews collected | 16,787 / 7,329 (coverage **43.7%**) |
| Raw → anon → clean (rows × columns) | 7,329 × 10 → 7,329 × 9 → 7,329 × 17 |
| Language split | Italian 6,951 · unknown 363 · other languages 15 |
| Topics file / labeled / analysis / top reviews | 6,951 × 18 / 6,951 × 21 / 5,998 × 21 / 60 × 6 |

### Ratings and replies

| Measure | All languages (04) | Italian only (07 output) |
|---|---|---|
| Reviews | 7,329 | 6,951 |
| Average rating | **2.26** | **2.17** |
| Average rating, first → last complete year | 3.56 (2015) → 1.57 (2025) | 3.54 (2015) → 1.52 (2025) |
| Developer [reply rate](glossary.md#reply-rate), overall | 41.6% (3,052 reviews) | 41.1% |
| Reply rate 2015-2020 | 83-100% each year | 83-100% each year (peak 100%, 2016) |
| Reply rate 2021 → 2025 | 32.5% → 1.6% (below 4% every year from 2022) | 32.1% → 1.7% (below 4% every year from 2022) |
| Average rating and reply rate, Jan-Aug 2026 | - | 1.49 and 3.5% (dashboard cards) |

### Topics

| Measure | Value |
|---|---|
| Model settings chosen in 05 | `min_cluster_size=30`, `min_df=5` |
| Topics found by the model | 30 (1,601 [outliers](glossary.md#outlier) reassigned) |
| Topics after [merging](glossary.md#topic-merge) / final labels | 21 / 12 |
| Excluded | 9 topics, 953 reviews (**13.7%** of Italian reviews) |
| Analysis set | 5,998 reviews |
| Category split | App Issue 5,090 (84.9%) · Praise 740 (12.3%) · Rail Service 87 (1.5%) · App Updates 81 (1.4%) |
| Bias check: average rating | excluded 3.66 · analysed 1.93 · all Italian 2.17 |
| Bias check: rating shares, excluded | 1★ 27.5% · 2★ 2.0% · 3★ 2.8% · 4★ 12.5% · 5★ 55.2% |
| Bias check: rating shares, analysed | 1★ 62.3% · 2★ 12.0% · 3★ 6.9% · 4★ 7.8% · 5★ 11.0% |
| Bias check: share excluded per year | from 7.4% (2017) to 23.8% (2020), peak in 2019-2021 (18.6%, 23.8%, 17.3%) |

### Label validation

| Measure | Value |
|---|---|
| Reviews that keep their label with UMAP seeds 0, 1, 2, 3 | 94.6%, 94.1%, 93.6%, 79.1% |
| Blind coding sample | 196 reviews, 14 per stratum: the 13 labels of the time it was drawn and EXCLUDE |
| Cohen's kappa, sample | **0.812** (95% CI 0.763 to 0.862) |
| Raw agreement, sample | 82.7% (95% CI 78.1% to 87.2%) |
| Weighted agreement, all reviews | **86.6%** (95% CI 81.7% to 91.2%) |
| Precision per label | from 50.0% (App Not Working) to 100.0% (four labels) |

---

## 3. Notebook 01 - Scraping

**In plain words.** This notebook downloads the public reviews of the Trenord app from the Google Play Store and
saves them in a file, exactly as received. Nothing is changed at this stage, so every later step can be traced back
to the original data.

### Input and output
- Input: Google Play Store, app id `it.nordcom.app`, through the unofficial `google-play-scraper` library (version
  1.2.7).
- Output: `data/raw/trenord_reviews_raw.csv` with the columns
  `review_id, author, rating, text, thumbs_up, app_version, date, has_reply, reply_text, reply_date`.

### Method
1. Set the configuration: `APP_ID = "it.nordcom.app"`, `LANGUAGE = "it"`, `COUNTRY = "it"`, `BATCH_SIZE = 200`,
   `MAX_REVIEWS = 16000` (cell 3).
2. Fetch the app metadata with `app(APP_ID, lang=LANGUAGE, country=COUNTRY)`. At scraping time the app had a
   1.82 rating, 1,000,000+ installs and version 4.16.7 (cell 4).
3. Download page by page with
   `reviews(APP_ID, lang=LANGUAGE, country=COUNTRY, sort=Sort.NEWEST, count=min(BATCH_SIZE, remaining), continuation_token=continuation_token)`,
   pausing `time.sleep(0.5)` between pages. The [continuation token](glossary.md#continuation-token) links the
   pages. The loop stops when the target is reached, a page is empty or the token is `None`; here it stopped after
   batch 38, when no more reviews were available (cell 5).
4. Compute coverage against the store's rating count (cell 6).
5. Map `reviewId, userName, score, content, thumbsUpCount, appVersion, at, replyContent, repliedAt` to the ten
   columns; `has_reply` is `replyContent is not None` (cell 8).
6. Save the raw file (cell 9).

### Parameters

| Parameter | Value | Why |
|---|---|---|
| `sort` | `Sort.NEWEST` | Time-contiguous sample with a well-defined order. |
| `BATCH_SIZE` | 200 | Largest page size the library supports reliably (notebook comment). |
| `MAX_REVIEWS` | 16000 | Set by hand, well above the 7,329 reviews the endpoint actually served, so in practice the endpoint's own limit decided the sample size. |

### Design decisions
- **Newest first, not "most relevant".** `Sort.MOST_RELEVANT` was rejected: its ranking is opaque and changes over time.
- **Raw immutability.** The raw file is written once and never modified. Only 02 reads it, and it works on a copy.
- **`utf-8-sig`.** The [BOM](glossary.md#bom-byte-order-mark) lets Excel read accented characters and emoji correctly.

### Validation
- Coverage is computed and printed.
- The loop ended on the endpoint's "no more reviews" condition, not on the target.
- The outputs saved in notebook 01 come from the scrape behind the current data snapshot. The notebook is not rerun,
  because that would rescrape; the dataframe cell (cell 8) has no saved output because it was edited after that run.

### Known limitations
- The scraper is unofficial: the endpoint can change, and it serves only a subset of the store's reviews.
- The sample reflects what the endpoint serves, so older periods may be under-represented relative to the store total.
- Ratings without text cannot be retrieved, so coverage is measured against ratings, not written reviews.
- Rerunning 01 produces a new snapshot and overwrites the raw file.
- Google Play is the only source. Reviews on other stores or channels are not included, so the results describe
  only the users who review the app on Google Play.

---

## 4. Notebook 02 - Anonymization

**In plain words.** This notebook removes the reviewers' names and replaces each review's original identifier with
a code that cannot be traced back without a secret key. It is the only step that touches the original file, so
everything after it works on protected data.

### Input and output
- Input: `data/raw/trenord_reviews_raw.csv` (read only), plus the [secret key](glossary.md#secret-key) `PSEUDO_KEY`
  from `.env`.
- Output: `data/processed/trenord_reviews_anon.csv`, with the raw columns minus `author`.

### The secret key
- **Generation.** 64 hexadecimal characters (256 random bits), generated in the project venv with
  `python -c "import secrets; print(secrets.token_hex(32))"`.
- **Storage.** Only in `.env` at the repository root, which is gitignored. `.env.example` is the tracked template:
  it explains the variable and holds the placeholder `change_me`.
- **Loading.** `find_dotenv(usecwd=True)` searches for `.env` from the working directory (`notebooks/`) upwards, and
  `load_dotenv()` adds its variables to the environment, where `os.getenv("PSEUDO_KEY")` reads them.
- **Key check.** The notebook stops before hashing if the key is missing, empty or still `change_me`: ids hashed
  with a known key could be recomputed by anyone from the public store ids.
- **Rotation.** The key was rotated on 2026-11-02 and the pipeline rerun (§12). Every published `review_id` changed;
  nothing else did.

### Method
1. Load the key and the raw file, and run the key check. The key is encoded to bytes once, as `KEY_BYTES`, instead
   of at every call of `pseudonymize_id` (cell 2).
2. Replace `review_id` with an [HMAC](glossary.md#hmac):
   `hmac.new(KEY_BYTES, message_bytes, hashlib.sha256).hexdigest()[:12]` (cell 3).
3. Mask ticket-like codes in `text` as `[CODE]`: first mixed letter-and-digit strings of 8 or more characters,
   then runs of 8 or more digits (cell 4).
   - `MIXED_CODE_PATTERN = r"\b(?=[A-Za-z0-9]*\d)(?=[A-Za-z0-9]*[A-Za-z])[A-Za-z0-9]{8,}\b"`
   - `DIGIT_CODE_PATTERN = r"(?<!\d)\d{8,}(?!\d)"`
4. Drop `author` (cell 5).
5. Run the checks; the output is saved only if all of them pass (cells 6-7).
6. Preview the first rows of `review_id, rating, thumbs_up, app_version, date, has_reply` (cell 8). Text and reply
   columns are left out because notebook outputs are published.

`reply_text`, the developer's public reply, is kept exactly as in the raw file.

### Parameters

| Parameter | Value | Why |
|---|---|---|
| Hash | HMAC-SHA256 | Keyed: stable across runs with the same key, but not recomputable without it. |
| Key | 64 hex characters (`secrets.token_hex(32)`) | 256 random bits from Python's cryptographically secure generator. |
| Truncation | 12 hex characters (48 bits) | Short, yet the chance of any collision among ~7,300 ids is about 1 in 10 million (notebook comment); uniqueness is also checked. |
| Code length | 8+ characters | Typical length of ticket, order and card numbers; set by hand, not tuned. |

### Design decisions
- **Keyed HMAC instead of a plain hash.** A plain SHA-256 of a public review id can be recomputed by anyone who knows
  the id, which would re-identify the row. This is the core of the [pseudonymization](glossary.md#pseudonymization).
- **Single point of contact with raw data.** Every later step starts from the anonymised file.
- **Reply text left intact.** An earlier version also removed reviewer names from `reply_text`. That step was
  dropped: the reply is kept identical to the text published on the store, and this is verified row by row.

### Validation (final run)

| Check | Result |
|---|---|
| Same row count as raw | PASS |
| `author` column absent | PASS |
| `review_id` unique | PASS |
| No original `review_id` present | PASS |
| `reply_text` identical to raw for every row | PASS (0 rows different; 3,052 non-null replies in both) |
| `[CODE]` replacements in `text` | 5 |
| Compared with the run before the rotation | every `review_id` different, no id shared; all other columns identical |
| Rerun with the same key (2026-11-03) | `trenord_reviews_anon.csv` identical to the previous run, ids unchanged |

### Known limitations
- Reviewers may write personal information in the text; only ticket-like codes are masked.
- `reply_text` is published unchanged, so it can greet the reviewer by first name, as on the store.
- Pseudonymised ids can be reproduced only with the same key. Ids made with different keys cannot be joined.

---

## 5. Notebook 03 - Cleaning

**In plain words.** This notebook prepares the reviews for analysis. It works out the language of each review,
removes symbols and links from the text, and reduces words to their basic form, so that "bought" and "buying"
count as the same word.

### Input and output
- Input: `trenord_reviews_anon.csv`.
- Output: `trenord_reviews_clean.csv`, which adds
  `year, month, day_of_week, year_month, language, text_clean, word_count, text_lemmatized`.

### Method
1. Load the anonymised file (cell 2).
2. Derive date features from `date`. The range is 2015-05-05 to 2026-08-04 (cell 3).
3. Detect the language with `lingua` (`LanguageDetectorBuilder.from_all_languages().build()`) (cell 4):
   - Italian as the top language is accepted at any [confidence](glossary.md#language-detection-confidence);
   - any other language needs `CONFIDENCE_THRESHOLD = 0.5`, otherwise the review is labeled `unknown`.
4. Clean the text into `text_clean`: lowercase, remove URLs (`http\S+|www\.\S+`), replace characters outside
   `[a-zàèéìíòóùú\s]` with spaces, collapse whitespace. Count words on the original text (cell 5).
5. Check duplicates on the Italian reviews: rows, distinct `review_id`, distinct `text_clean`, reviews that share
   their `text_clean` with another review and the number of such groups, and the median length in words of the
   shared texts and of all Italian reviews. Counts only (cell 6). A markdown cell explains the result (cell 7).
6. [Lemmatize](glossary.md#lemmatization) with spaCy `it_core_news_lg` into `text_lemmatized`. A token is kept if it
   is alphabetic, is not one of the [stopwords](glossary.md#stopwords) and has a lemma longer than 2 characters (cell 8).
7. Save (cell 9).

### Parameters

| Parameter | Value | Why |
|---|---|---|
| Italian acceptance | any confidence | Inspection found 921 short Italian reviews ("pessima", "ottima") detected as Italian with low confidence. |
| `CONFIDENCE_THRESHOLD` (other languages) | 0.5 | A conventional midpoint between accepting and rejecting; not tuned. |
| Minimum lemma length | > 2 characters | Removes very short words ("va", "fa") with little meaning; set by hand. |

### Design decisions
- **Two-level language detection.** A single threshold was rejected: a strict one discards short Italian reviews,
  and a loose one admits other languages at low confidence.
- **Two text versions.** `text_clean` keeps natural word order for the [embeddings](glossary.md#embedding) (05, 06);
  `text_lemmatized` groups word variants. The dashboard used it for its word analysis until 2026-11-13; no later
  step reads it now, and the column stays in the published files.

### Validation (final run)
- The language split is in Key numbers.
- 10 reviews are empty after cleaning, none of them Italian.
- 135 reviews are empty after lemmatization.
- The original text has 19.9 words per review on average.
- Duplicate check on the 6,951 Italian reviews: 6,951 distinct `review_id`, so no review was collected twice, and
  6,341 distinct `text_clean`. 743 reviews share their cleaned text with at least one other review, in 133 groups.
  Their median length is 2 words, against 14 for all Italian reviews. They are kept, because each one is a separate
  review with its own rating and date.
- Rerun of 2026-11-13 in a fresh kernel, 69 s, after the cell that exported the stopword list for the dashboard
  was removed, with its import: `trenord_reviews_clean.csv` is byte-identical to the previous run.

### Known limitations
- The 378 non-Italian or undetermined reviews are not analysed further.
- The character filter removes digits and emoji, so "10 minutes late" loses the number.

---

## 6. Notebook 04 - Exploratory analysis

**In plain words.** This notebook describes the reviews as a whole: how many stars people give, how this changed
over the years, and how often the company answered. It produces six charts.

### Input and output
- Input: `trenord_reviews_clean.csv` (all languages).
- Output: six charts in `reports/figures/`, saved with `dpi=150`:
  - `chart_rating_distribution.png`
  - `chart_reviews_per_year.png`
  - `chart_avg_rating_over_time.png`
  - `chart_reply_rate_overall.png`
  - `chart_reply_rate_by_rating.png`
  - `chart_reply_rate_over_time.png`

### Method and results
Overall figures are in Key numbers (all languages column).
1. Overview: median rating 1.0, 20 words per review on average (cell 3).
2. Rating distribution: 1★ 4,075 · 2★ 745 · 3★ 454 · 4★ 654 · 5★ 1,401 (cell 5).
3. Reviews per year: the peak is in 2019 (1,086 reviews); 2026 is incomplete (326 reviews) (cell 6).
4. Average rating over time, with the y axis fixed at 1-5. The chart annotates the most recent yearly drop of at
   least 0.5★, computed from the data: 2022 → 2023, −0.78 (cell 7).
5. Reply rate overall (cell 9) and by rating: it rises from 29.0% (1★) to 70.9% (4★), then falls to 60.1% at 5★
   (cell 10).
6. Reply rate over time; the yearly values are in Key numbers (cell 11).
7. Most upvoted reviews, shown as metadata only: upvotes, rating, date, length (cell 13).

### Design decisions
- **Line charts for averages and rates.** Bars would suggest a zero baseline. The y axis covers the full 1-5 scale.
- **Incomplete year in grey and dashed**, so it is not read as a real decline.
- **[Okabe-Ito](glossary.md#okabe-ito-palette) colours**, which stay distinct for readers with colour vision
  deficiency: blue `#0072B2` for single series, vermillion `#D55E00` for annotations, and a 1-5 star scale
  `#D55E00`, `#E69F00`, `#999999`, `#66C5AB`, `#009E73`. The dashboard uses the same colours.
- **The star rating is the main sentiment signal.** It is available for every review and given by the author. A
  sentiment analysis of the text is planned as a later step, to check the ratings and find the reviews where text
  and rating disagree.

### Validation
The charts are regenerated from the data at every run; no number in them is hardcoded.

### Known limitations
- This notebook covers all languages, while the topic analysis covers Italian only, so values differ slightly
  (see the two columns in Key numbers).
- That the reply collapse and the rating decline happen together is a description, not a proof of cause.
- Ratings are ordinal: 1 to 5 stars are in order, but the step from one star to the next is not necessarily the
  same size, so averages of ratings are an approximation.

---

## 7. Notebook 05 - Model selection

**In plain words.** Before training the final model, this notebook tries several settings and measures how good
the resulting topics look. It checks two choices: how big a group of reviews must be to count as a topic, and how
many topics a keyword must appear in to be kept. Then, with those settings fixed, it looks at four more things: a
second HDBSCAN setting, the random seed of UMAP, the embedding model and the way keywords are chosen. It saves no
model and no file.

### Input and output
- Input: `trenord_reviews_clean.csv`, filtered to `language == "it"`. The notebook reads no other file.
- Output: tables of metrics in the notebook only.

### Method
05 trains the same pipeline that 06 later uses, with the values chosen here. It does not read anything produced
by 06.

1. Load the Italian reviews with the same filter, order and empty-text handling that 06 uses (cell 3).
2. Compute the sentence embeddings once, time the encoding and reuse the embeddings in every run that uses the
   current embedding model (cell 4).
3. Split every review with the same analyzer that produces the keywords (Italian stopwords removed, single words and
   bigrams) and build a gensim `Dictionary` for coherence. The cell prints the tokens of a made-up sentence as an
   example (cell 5).
4. Define `train_topic_model(min_cluster_size, min_df, ...)`, which trains the pipeline (UMAP, HDBSCAN,
   CountVectorizer, MMR, outlier reduction, `update_topics`) with fresh model objects and returns the model and the
   topics before and after outlier reduction (cell 6). Optional parameters (`run_embeddings`, `run_embedding_model`,
   `umap_random_state`, `min_samples`, `extra_stopwords`, `representation_model`) are used only by the last four
   comparisons; at their default values the function trains exactly the setup of 06. Outliers are reduced only when
   there are some.
5. Draw the reviews reduced to 2 dimensions with UMAP for `n_neighbors` 5, 15 and 50, as an illustration of that
   setting (cell 7).
6. Train one trial model with `min_cluster_size=30` and `min_df=5`, and print its topic 0 keywords and outlier
   counts (cell 8).
7. Define one function per metric and try each on the trial model:
   - outliers before reduction (cell 9);
   - size of the largest topic after reduction (cell 10);
   - the top 10 words of each topic, without empty strings, used by the next two metrics (cell 11);
   - [topic coherence](glossary.md#topic-coherence) c_v with gensim `CoherenceModel(..., coherence="c_v", processes=1)`
     (cell 12);
   - [topic diversity](glossary.md#topic-diversity): distinct top words divided by all top words (cell 13).
8. `compute_metrics` combines the four metrics with two counts: topic words not found in any single review, and
   empty keyword slots, which BERTopic adds when a topic has fewer than 10 keywords (cell 14).
9. Compare `min_cluster_size` 20, 25, 30, 40 and 50 with `min_df=5` (cells 15-16).
10. Compare `min_df` 1, 2 and 5 with `min_cluster_size=30` (cells 19 and 21), check that every review keeps the same
    topic (cell 20) and show the top 5 keywords of five topics side by side (cell 23). The five topics were chosen
    so that no keyword shown is a personal name or a code.
11. Compare `min_samples` 5, 10, 15 and 30 with `min_cluster_size=30` and `min_df=5` (cells 25-29).
12. Compare UMAP seeds 42, 0, 1, 2 and 3 with the current settings, check that seed 42 gives the same topics as the
    `min_cluster_size=30` run of the first table and compute the adjusted Rand index against seed 42 (cells 30-34).
13. Compare three embedding models with the current settings (cells 35-39).
14. Compare four keyword settings on the current assignments, check that no review changes topic, and show the top
    5 keywords of the same five topics (cells 40-45).
15. Write the choices made from the four comparisons (cell 46).

### Results: `min_cluster_size` (`min_df=5`)

| `min_cluster_size` | Topics | Outliers before reduction | Largest topic | Coherence c_v | Diversity | Words not found | Empty slots |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 20 | 55 | 26.5% | 14.8% | 0.416 | 0.703 | 0 | 5 |
| 25 | 37 | 17.8% | 28.6% | 0.421 | 0.684 | 0 | 0 |
| 30 | 30 | 23.0% | 17.5% | 0.419 | 0.783 | 0 | 0 |
| 40 | 8 | 1.7% | 85.9% | 0.348 | 0.212 | 0 | 14 |
| 50 | 6 | 1.8% | 85.9% | 0.497 | 0.192 | 0 | 34 |

### Results: [`min_df`](glossary.md#min_df) (`min_cluster_size=30`)

| `min_df` | Coherence c_v | Diversity | Empty slots | Words not found |
|---:|---:|---:|---:|---:|
| 1 | 0.385 | 0.887 | 0 | 49 |
| 2 | 0.409 | 0.863 | 0 | 20 |
| 5 | 0.419 | 0.783 | 0 | 0 |

The three `min_df` values give the same topic to every review, and `min_df=5` gives the same topics as the
`min_cluster_size=30` run of the first table.

### What `min_df` counts
BERTopic fits the [CountVectorizer](glossary.md#countvectorizer) on one joined text per topic, not on the reviews
(this is how [c-TF-IDF](glossary.md#c-tf-idf) works). So `min_df=5` means "the keyword must appear in at least 5
topics", not in 5 reviews, and it changes only the keywords: clustering works on the embeddings, and outlier
reduction on the topic embeddings.

### The fake bigram finding
With `min_df` 1 and 2, 49 and 20 of the top keywords appear in no single review. Joining the reviews of a topic
into one text creates [bigrams](glossary.md#bigram) across review boundaries: the last word of one review followed
by the first word of the next. Short reviews like "ottima" make this common, which gives keywords such as "ottima
ottima", "ottimo ottimo" and "perfetto ottima"; these three were checked and occur in no review. A joined pair like
this rarely appears in five topics, so `min_df=5` removes it. The higher diversity of `min_df` 1 and 2 comes largely
from these pairs and from rare variants, which count as different strings.

### Choice
- **`min_cluster_size=30`.** Coherence is as high as with 20 and 25, diversity is the highest, there are no empty
  keyword slots and no topic holds more than a fifth of the reviews.
  - 25 is the closest alternative: fewer outliers (17.8%), but one topic holds 28.6% of the reviews and more keywords
    repeat between topics.
  - 20 splits the reviews into 55 topics with more repeated words.
  - 40 and 50 collapse: 85.9% of the reviews end up in one topic. The 0.497 coherence of 50 comes from a few generic
    words shared by a handful of topics, not from better topics.
- **`min_df=5`.** The keywords are words that really occur in reviews, and coherence is the highest.
  - The cost: a word found in fewer than five topics is dropped even when it is the most specific one, such as
    "password" for the login topic.
  - With few topics, as with 40 and 50, the same threshold is too strict: a word must then appear in 5 of only 8 or 6
    topics, which leaves empty keyword slots. If the number of topics is reduced a lot, `min_df` should go down too.

### Results: `min_samples` (`min_cluster_size=30`, `min_df=5`)

06 does not set `min_samples`, so HDBSCAN uses `min_cluster_size` and the effective value is 30. In the
`min_cluster_size` table above, `min_samples` therefore changed together with `min_cluster_size`. Here only
`min_samples` changes (cells 25-29). `min_samples=30` gives the same topic for every review as the run without it.

| `min_samples` | Topics | Outliers before reduction | Largest topic | Coherence c_v | Diversity | Words not found | Empty slots |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 54 | 32.6% | 8.1% | 0.436 | 0.681 | 0 | 0 |
| 10 | 45 | 27.4% | 13.8% | 0.430 | 0.696 | 0 | 0 |
| 15 | 38 | 17.7% | 18.6% | 0.438 | 0.721 | 0 | 0 |
| 30 | 30 | 23.0% | 17.5% | 0.419 | 0.783 | 0 | 0 |

The number of topics falls as `min_samples` grows. The outlier share does not move in one direction: it is highest
with 5 and lowest with 15.

### Results: UMAP seed (current settings)

The current settings trained with five UMAP [seeds](glossary.md#random-seed) on the same embeddings (cells 30-34).
The [adjusted Rand index](glossary.md#adjusted-rand-index-ari) compares the final assignments of each seed with those
of seed 42. Seed 42 gives the same topic for every review as the `min_cluster_size=30` run of the first table,
which has the same settings (cell 32).

| UMAP seed | Topics | Outliers before reduction | Largest topic | Coherence c_v | Diversity | ARI vs seed 42 |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 30 | 23.0% | 17.5% | 0.419 | 0.783 | 1.000 |
| 0 | 33 | 29.1% | 10.1% | 0.434 | 0.767 | 0.667 |
| 1 | 27 | 18.2% | 19.3% | 0.415 | 0.756 | 0.885 |
| 2 | 31 | 22.5% | 17.1% | 0.418 | 0.735 | 0.793 |
| 3 | 27 | 14.2% | 32.6% | 0.426 | 0.726 | 0.515 |

With the seed as the only change, the number of topics goes from 27 to 33, the largest topic from 10.1% to 32.6%,
and the ARI against seed 42 from 0.515 to 0.885.

### Results: embedding models (`min_cluster_size=30`, `min_df=5`, seed 42)

Three multilingual models, with the embeddings computed once per model and kept only in memory (cells 35-39). The
two paraphrase models take the text as it is. The `intfloat/multilingual-e5-base` model card asks for the prefix
`"query: "` on every text for tasks such as clustering and normalizes the embeddings in its example, so both are done.
MMR, which also uses the embedding model to compare keywords, passes the words without prefix.

| Embedding model | Size | Encoding time | Topics | Outliers before reduction | Largest topic | Coherence c_v | Diversity | Words not found | Empty slots | ARI vs current |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `paraphrase-multilingual-mpnet-base-v2` (current) | 768 | 272 s | 30 | 23.0% | 17.5% | 0.419 | 0.783 | 0 | 0 | 1.000 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 59 s | 30 | 13.2% | 24.3% | 0.407 | 0.695 | 0 | 2 | 0.431 |
| `intfloat/multilingual-e5-base` | 768 | 233 s | 7 | 0.0% | 95.4% | - | - | - | - | 0.016 |

- e5 gives 7 topics and no outliers. With 7 topics no word appears in at least 5 of them, so `min_df=5` leaves no
  keyword and BERTopic stops with "After pruning, no terms remain". The cell trains it again with `min_df=1`, which
  does not move any review; its keyword columns are left empty because they would not be comparable.
- With no outliers, `reduce_outliers` would stop with an error, so `train_topic_model` reduces outliers only when
  there are some. Every other run has outliers, so this does not change them.
- The encoding times are from the last run of 2026-11-05 on the project computer. Over four runs that day the
  encoding of the current model took 238 s, 180 s, 177 s and 272 s. During the last run the test suite was running
  on the same computer for part of the time.

### Results: keyword settings (current assignments)

Four keyword settings on the current model (cells 40-45). All four give the same topic for every review as the
current model (cell 42). The extra stopwords are "app" and "applicazione".
[KeyBERTInspired](glossary.md#keybertinspired) keeps the c-TF-IDF candidates closest to a few representative reviews
of the topic, while [MMR](glossary.md#mmr-maximal-marginal-relevance) balances relevance and variety.

| Keyword setting | Coherence c_v | Diversity | Words not found | Empty slots |
|---|---:|---:|---:|---:|
| MMR 0.3 (current) | 0.419 | 0.783 | 0 | 0 |
| MMR 0.3 + extra stopwords | 0.429 | 0.757 | 4 | 0 |
| KeyBERTInspired | 0.407 | 0.770 | 0 | 0 |
| KeyBERTInspired + extra stopwords | 0.389 | 0.723 | 4 | 0 |

| topic | MMR 0.3 | MMR 0.3 + extra stopwords | KeyBERTInspired | KeyBERTInspired + extra stopwords |
|---:|---|---|---|---|
| 5 | login, account, accesso, errore, mail | login, account, accesso, errore, mail | login, registrarmi, account, accedere, riesco accedere | login, registrarmi, account, accedere, riesco accedere |
| 9 | ottima applicazione, applicazione, utilissima, applicazione utile, efficace | funzionale, utilissima, efficace, ottimo, consigliata | davvero utile, utile, utilissima, funziona utile, ottima applicazione | davvero utile, utile, utilissima, funziona utile, consigliata |
| 10 | ottima, perfetta, perfetto, fantastica, bellissima | ottima ottima, ottima, perfetto, fantastica, bellissima | ottima, ottimo, fantastica, bellissima, bravi | ottima, ottimo, ottima ottima, fantastica, bellissima |
| 14 | ottimo, ottimo servizio, buono, complimenti, servizio | ottimo, ottimo servizio, buono, complimenti, servizio | ottimo, ottima, buono, buona, buon | ottimo, ottima, buono, buona, buon |
| 26 | funziona, accedere, assistenza, accesso, impossibile utilizzare | funziona, accedere, assistenza, accesso, impossibile utilizzare | impossibile utilizzare, inutile, neanche, impossibile, inesistente | impossibile utilizzare, inutile, neanche, impossibile, inesistente |

The 4 words not found with the extra stopwords were checked outside the notebook, for MMR: "ottima ottima" (topics 10
and 23), a pair made by joining the reviews of a topic, and "pessima pessimo" (topics 19 and 25), a pair that
appears inside a review only once "app" is removed. The coherence dictionary of cell 5 is built with the spaCy
stopwords only, so it contains neither.

### Choice: min_samples, seed, embedding model and keywords

The four comparisons above lead to these decisions for 06 (cell 46):
- `min_samples` stays at 30, the value 06 gets without setting it. The coherence differences between 5, 10, 15 and
  30 are small (0.419 to 0.438), and 30 gives the highest diversity (0.783), with fewer topics that share fewer
  keywords.
- Seed stability is moderate. The ARI against seed 42 goes from 0.515 to 0.885, and the number of topics from 27 to
  33. Seed 42 is not an unusually good seed: its coherence (0.419) is within the range of the other seeds (0.415 to
  0.434). The ARI measures the 30 topics, not the 12 labels given in 07. Whether the labeled themes stay stable
  across seeds will be measured in notebook 08.
- The embedding model stays `paraphrase-multilingual-mpnet-base-v2`. MiniLM has lower coherence (0.407 against
  0.419) and lower diversity (0.695 against 0.783), and `multilingual-e5-base` collapses into 7 topics with 95.4% of
  the reviews in one. The UMAP and HDBSCAN settings were chosen for the current model, so this comparison favours
  it. This is a limit of the comparison.
- The keywords stay MMR with diversity 0.3, without extra stopwords. The extra stopwords raise coherence only
  slightly (0.429 against 0.419) and bring back a pair made by joining reviews ("ottima ottima"). KeyBERTInspired is
  lower on both coherence (0.407 against 0.419) and diversity (0.770 against 0.783).

Notebook 08 has since measured the stability of the labeled themes (§10).

### Validation
- Seed 42 with the current settings gives the same topic for every review as the `min_cluster_size=30` run of the
  first table (cell 32), so the check stays inside the notebook. The same run was also compared with
  `trenord_reviews_topics.csv`, the output of 06, and gave the same topic for every review: once outside the
  notebook (2026-11-02) and once in a cell of 05 (2026-11-05) that was then removed, so that 05 reads only
  `trenord_reviews_clean.csv`.
- `min_samples=30` gives the same topic for every review as the run without `min_samples` (cell 27), and the four
  keyword settings give the same topics as the current model (cell 42).
- Rerun of 2026-11-05 in a fresh kernel, 1,087 s: the tables of cells 1-24 are identical to the previous run. Cell 4
  now also prints the encoding time.
- Rerun of 2026-11-05 after the seed 42 check was moved inside the notebook, 1,442 s: every table is identical
  to the previous run. Only the encoding times changed.
- The notebook prints only counts, metrics, keywords and the tokens of one made-up sentence, no review texts.

### Known limitations
- Coherence c_v is a proxy. It also rewards near-synonyms and generic words, so the metrics do not replace reading
  the topics. The labels in 07 come from reading the reviews.
- UMAP `n_neighbors`, `n_components` and `min_dist`, and HDBSCAN settings other than `min_cluster_size` and
  `min_samples`, were not compared.
- The seed comparison uses five seeds, and the embedding and keyword comparisons use seed 42 only.
- The keyword metrics of e5 are missing, because `min_df=5` leaves it no keyword.
- Seed stability is moderate: the ARI against seed 42 goes from 0.515 to 0.885 and the number of topics from 27 to
  33. It measures the 30 topics, not the 12 labels. Notebook 08 measures the labels: 93.6% to 94.6% of the
  reviews keep their label with seeds 0, 1 and 2, and 79.1% with seed 3 (§10).
- The UMAP and HDBSCAN settings were chosen for the current embedding model, so the embedding comparison favours
  it.

---

## 8. Notebook 06 - Topic model training

**In plain words.** This notebook reads the Italian reviews and lets an algorithm group together the reviews that
talk about similar things, without being told the themes in advance. It shows how the groups are named and how
similar they are, checks the result and saves the model and the group of each review. In the recorded environment,
training again gives exactly the same groups.

### Input and output
- Input: `trenord_reviews_clean.csv`, filtered to `language == "it"`.
- Output:
  - `trenord_reviews_topics.csv`: the clean columns plus `topic`.
  - `bertopic_model_trained/`, saved with `serialization="safetensors"`, `save_ctfidf=True`,
    `save_embedding_model="paraphrase-multilingual-mpnet-base-v2"` ([safetensors](glossary.md#safetensors)).

### Method (parameters verbatim)
1. Load the data: 7,329 reviews, 6,951 of them in Italian (cell 2).
2. Prepare the `text_clean` texts of the Italian reviews. Empty or missing texts are replaced by `" "`; there were
   none in this run (cell 3).
3. Configure the model (cell 4):
   - embeddings from the [sentence transformer](glossary.md#sentence-transformer)
     `SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")`;
   - [UMAP](glossary.md#umap): `UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine", random_state=42)`;
   - [HDBSCAN](glossary.md#hdbscan): `HDBSCAN(min_cluster_size=30, metric="euclidean", prediction_data=True)`;
   - CountVectorizer: `CountVectorizer(stop_words=list(italian_stopwords), min_df=5, ngram_range=(1, 2))`, with
     spaCy's Italian stopwords;
   - [MMR](glossary.md#mmr-maximal-marginal-relevance): `MaximalMarginalRelevance(diversity=0.3)`;
   - BERTopic: `top_n_words=10, language="multilingual", calculate_probabilities=False`.
4. Train with `fit_transform(texts)`: 30 topics and 1,601 outliers, which get topic -1 (cell 5).
5. [Reduce outliers](glossary.md#outlier-reduction) with
   `reduce_outliers(texts, topics, strategy="embeddings", threshold=0.0)`, leaving 0 outliers (cell 6).
6. Update the [topic representations](glossary.md#topic-representation), with c-TF-IDF keywords:
   `update_topics(texts, topics=new_topics, vectorizer_model=vectorizer_model, representation_model=representation_model)`
   (cell 7). Both models are passed again on purpose. Without them `update_topics` builds a plain
   `CountVectorizer(ngram_range=(1, 1))`, with no stopwords, no bigrams and no `min_df`, and drops MMR, so the
   keywords would no longer follow the settings of cell 4.
7. Show how BERTopic names the topics (cell 8).
8. Draw the keywords of the largest topics (cells 9-10) and the topic tree (cells 11-12).
9. Check the results before saving (cell 13).
10. Save the model and the topic assignments (cell 14).

### Automatic topic names
`get_topic_info()` returns one row per topic with the columns `Topic`, `Count`, `Name`, `Representation` and
`Representative_Docs`. Cell 8 shows the first 5 rows without `Representative_Docs`, because that column holds real
review texts and notebook outputs are published.

The `Name` column is not chosen by anyone. BERTopic stores it in `topic_labels_`: the topic number followed by its
first 4 keywords, joined with underscores. For topic 0 the 10 keywords start with `treni, treno, ritardi, app`, so its
name is `0_treni_treno_ritardi_app`. The cell rebuilds the same name by hand and prints both. The human labels are
given later, in 07.

### Visualizations and how to read them
- **Keyword bar charts** (`visualize_barchart(top_n_topics=8, n_words=5)`, cell 9). One panel for each of the 8
  largest topics, with its top 5 keywords. A longer bar means a higher c-TF-IDF weight, so a word more typical of
  that topic. The panels shown are topics 0, 1, 2, 3, 4, 5, 6 and 8. Topic 7 (173 reviews) is left out because
  topic 8 has 176.
- **Topic tree** (`visualize_hierarchy()`, cell 11). The 30 topics are the leaves on the left; branches join to the
  right as topics become less similar. Two topics joined close to the leaves are similar. Similarity is computed on
  the c-TF-IDF keywords, not on what users think: topic 12 (praise for buying tickets) sits next to topic 1 (failed
  purchases) because both use words like "biglietti" and "acquisto". The tree places the topics merged in 07 next
  to each other (0, 6 and 29; 5 and 22; 8, 11, 20 and 24), but the merges also rely on ratings and on reading the
  reviews.

Both charts are plotly figures saved in the notebook. With them the notebook is 94,756 bytes.

### Check before saving
Cell 13 stops the notebook with an `assert` before any file is overwritten if:
- the `topic` column is missing, or the table and the texts have a different number of rows;
- any review still has topic -1 after the reduction;
- the table and the model have a different number of topics.

In this run it printed 6,951 reviews, 30 topics, 0 outliers and "All checks passed".

### What safetensors saves
The model is saved in [safetensors](glossary.md#safetensors) format instead of pickle. A pickle file can run code
when it is loaded; safetensors stores only numbers. The folder holds:
- `topics.json`: the topic of every review, the topic sizes, the keywords with their weights and the automatic names;
- `topic_embeddings.safetensors`: one vector per topic;
- `ctfidf.safetensors` and `ctfidf_config.json`: the c-TF-IDF word counts and the vectorizer settings with its
  vocabulary, so 07 can recompute the keywords after merging topics;
- `config.json`: the BERTopic settings and the name of the embedding model.

It does not save the UMAP and HDBSCAN models, the MMR representation model or the weights of the embedding model,
which is reloaded by name. A reloaded model can still assign new reviews by similarity to the topic vectors, but not
with the original clustering. That is enough here, because 07 works only on the reviews already assigned, and it
sets MMR again before merging.

### Parameters

| Parameter | Value | Why |
|---|---|---|
| Embedding model | `paraphrase-multilingual-mpnet-base-v2` | "Best lightweight multilingual model that runs on CPU and handles Italian well" (notebook comment). Compared in 05 with `paraphrase-multilingual-MiniLM-L12-v2` and `intfloat/multilingual-e5-base` (§7). |
| UMAP `n_neighbors` | 15 | BERTopic's default UMAP setting; not tuned. |
| UMAP `n_components` | 5 | BERTopic's default; reduces dimensions before clustering. Not tuned. |
| UMAP `min_dist` | 0.0 | BERTopic's default; packs similar points tightly, which helps clustering. Not tuned. |
| UMAP `metric` | cosine | BERTopic's default; the usual choice for text embeddings. |
| UMAP `random_state` | 42 | Fixed [random seed](glossary.md#random-seed): "without it results change every run" (notebook comment). 05 compares it with seeds 0, 1, 2 and 3 (§7). |
| HDBSCAN `min_cluster_size` | 30 | Smallest group accepted as a topic. Chosen in 05 against 20, 25, 40 and 50 (§7). BERTopic's default is 10. |
| HDBSCAN `min_samples` | not set, so 30 | When it is not set, the hdbscan library (0.8.42) uses `min_cluster_size` instead, so the effective value is 30. It sets how strict the clustering is about dense areas: a review is the core of a dense area only if at least 30 points, itself included, are close to it. It changes which reviews are left out as outliers, so it contributes to the 1,601 outliers. Not tuned: 06 keeps the value it gets without setting it, and 05 compares 5, 10, 15 and 30 (§7). Because it follows `min_cluster_size`, it also changed in the `min_cluster_size` runs of 05. |
| CountVectorizer `min_df` | 5 | A keyword must appear in at least 5 topics, because BERTopic fits the vectorizer on one joined text per topic. Changes only the keywords. Chosen in 05 against 1 and 2 (§7); the library default is 1. |
| CountVectorizer `ngram_range` | (1, 2) | Single words plus bigrams; a common choice for BERTopic keywords. Not tuned. |
| MMR `diversity` | 0.3 | "The value recommended in the official BERTopic documentation" (notebook comment). The library default is 0.1. 05 compares MMR with KeyBERTInspired and with extra stopwords (§7). |
| `top_n_words` | 10 | BERTopic's default. |
| `reduce_outliers` strategy / threshold | embeddings / 0.0 | Outliers were inspected and judged valid reviews, so all are reassigned by [cosine similarity](glossary.md#cosine-similarity). 0 is the library default threshold; the strategy was chosen over the default `distributions`. |

### Design decisions
- **HDBSCAN, not K-Means.** HDBSCAN finds the number of topics from the data and accepts groups of any shape.
  K-Means needs the number of topics fixed in advance and puts every review in a group. With HDBSCAN the isolated
  reviews stay out while the topics form, and are reassigned only afterwards.
- **`text_clean`, not `text_lemmatized`.** Transformer embeddings are trained on natural text. Lemmatized,
  stopword-free text was rejected because it loses the context they rely on.
- **Reassign every outlier.** Noise is handled afterwards by the exclusion rule in 07, not by leaving reviews
  without a topic.
- **MMR** reduces redundant keywords, such as the singular and plural of the same word.
- **Training separated from labeling.** An earlier single notebook (19 final topics) was replaced by separate
  training and labeling notebooks, so the labels can be checked against the exact model they were written for.
- **Retrained in a recorded environment.** After the venv was rebuilt on 2026-11-02, retraining with the same code
  and data gave a different clustering from the earlier model:
  - 6,428 of 6,951 rows had a different topic id;
  - 92.1% of rows agreed under the best matching between old and new topics;
  - the adjusted Rand index was 0.81.

  The environment of the earlier model had not been recorded, so it could not be rebuilt. The model was retrained,
  the environment was recorded in a [lock file](glossary.md#lock-file) and the labels in 07 were rebuilt for the
  new topic ids. The earlier model is kept only as a local backup outside the repository.
- **Representative documents are never printed.** They are real review texts, and the notebook outputs are
  published.

### Validation
- 30 topics, with sizes from 52 to 1,214 reviews; 1,601 outliers before reduction, 0 after.
- The check before saving passes.
- **Retraining is reproducible in the locked environment.** Consecutive trainings on 2026-11-02 gave the same topic
  for every review, the same sizes and the same keyword weights. In 05, seed 42 with precomputed embeddings gave
  the same topic for every review as this model, checked on 2026-11-02 and on 2026-11-05 (§7).
- **Rerun of 2026-11-04** in a fresh kernel, after the cells of steps 7-9 were added: same topic for every review,
  same 30 topics with the same sizes, same keywords. `trenord_reviews_topics.csv` and the model files are
  byte-identical to the previous run, except for the order in which the 624 stopwords are listed in
  `ctfidf_config.json`; the vocabulary is the same.

### Known limitations
- Each review gets one topic, although many mention several issues.
- Retraining is reproducible only in the locked environment. A different environment can number and size the
  topics differently, which the keyword check of the label map in 07 catches.
- Some topics are dominated by short, generic reviews (see the exclusion rule in 07).
- The topic tree measures how similar the keywords are, not how similar the opinions are.
- The topics depend partly on the UMAP seed: in 05 other seeds give 27 to 33 topics, with an ARI of 0.515 to 0.885
  against seed 42 (§7). In 08, 93.6% to 94.6% of the reviews keep their label with seeds 0, 1 and 2, and 79.1%
  with seed 3, where Subscription & Payment Failures and Login & Account Issues are absorbed by Ticket Purchase
  Failures (§10).
- The embedding model was compared with two others using UMAP and HDBSCAN settings chosen for it, which favours
  it (§7).

---

## 9. Notebook 07 - Topic labeling and export

**In plain words.** In 06 the model grouped the Italian reviews into 30 topics, each identified only by a number.
This notebook reads every topic, gives it a short name and a category, or sets it aside when its reviews say nothing
specific. It merges topics with the same name, draws four charts, checks how much the excluded reviews change the
picture, and saves the files used by the dashboard after checking that no personal data has slipped through. It ends
with the results and a short list of recommendations.

### Input and output
- Input: `trenord_reviews_topics.csv` and `bertopic_model_trained/`, both from 06. `trenord_reviews_clean.csv` is used only
  in the final privacy check.
- Output:
  - `trenord_reviews_labeled.csv`: adds `topic_label`, `category`, `topic_merged`.
  - `trenord_reviews_analysis.csv`: EXCLUDE rows removed.
  - `top_reviews_per_topic.csv` (`topic_label, category, rating, thumbs_up, date, text`): the 5 most upvoted reviews
    with at least one upvote, for each of the 12 topics.
  - `topic_keywords.csv` (`topic_label, rank, keyword`): the top 5 keywords of each of the 12 topics, from the
    merged model, the same words as `chart_keywords_per_topic.png`. The dashboard reads them, because it does not
    load the model. Keywords only, no review texts.
  - `bertopic_model_merged/`: the model after the merges.
  - Four charts in `reports/figures/`, saved with `dpi=150`: `chart_reviews_per_topic.png`,
    `chart_avg_rating_per_topic.png`, `chart_keywords_per_topic.png`, `chart_topic_priority.png`.

### Categories
The categories are the project's own, chosen after reading the topics:
- **App Issue**: something in the app does not work, works badly or stopped working;
- **Praise**: what users like about the app;
- **Rail Service**: complaints about the trains and the company, not about the app;
- **App Updates**: reviews about how the app got better or worse with an update, and how it could improve.

No topic is made mostly of requests for new features: requests exist in the reviews, but they are spread across
topics.

### Method
1. Load the reviews and the model. Every review must be Italian (cell 3).
2. Check that the file and the model agree: the topic of every review in `topics.csv` must equal the one stored in
   the model, otherwise one of the two was replaced after 06 (cell 4).
3. Build the topic overview table, the evidence behind the labels (cell 5).
4. Write the label map, with two [identifying keywords](glossary.md#identifying-keywords) per topic (cell 6), and
   check it (cell 7).
5. Apply the labels with `map()` (cell 8).
6. Derive the merge list from the labels (cell 9), merge (cell 10) and check the merge (cell 11).
7. Build the final topics table with 95% confidence intervals and the category table (cell 12).
8. Draw the four charts, each followed by how to read it (cells 13-20).
9. Run the two bias checks (cells 21-22), read in cell 23.
10. Save the outputs (cell 24) and check the saved files (cells 25-26).
11. Save the keywords for the dashboard and check them (cell 27). The results are summarised in cell 28 and the
    recommendations in cell 29.

### Topic overview table
One row per 06 topic with what was looked at to label it. Review texts are not shown, because notebook outputs are
published; the reading itself was done outside the notebook (`labeling/`, gitignored).

| Column | Meaning |
|---|---|
| `reviews` | number of reviews in the topic |
| `avg rating` | average star rating |
| `1-2 stars (%)`, `4-5 stars (%)` | share of negative and positive reviews |
| `5 words or fewer (%)` | share of very short reviews, the measure behind the exclusion rule |
| `top keywords` | the first 5 keywords of the topic |

For example topic 10 has 164 reviews, 99.4% of them with 5 words or fewer and 100.0% with 4-5 stars, while topic 1
has 1,143 reviews, 1.7% short and 88.9% with 1-2 stars.

### Label map and keyword check
`TOPIC_LABELS` maps each of the 30 topic ids of the 06 model to `(label, category, identifying keywords)`. The
label is `EXCLUDE` for the topics set aside, which have no category. The comment above each entry says what the
label covers. Two of them say more than the name: App Not Working also holds generic "it does not work" reviews that
do not say what fails, and topics 7 and 28 share Station Issues because the two were hard to tell apart.

| Topic | Label | Category | Identifying keywords |
|---:|---|---|---|
| 0 | Inaccurate Train Info | App Issue | treni, ritardi |
| 1 | Ticket Purchase Failures | App Issue | biglietti, errore |
| 2 | Subscription & Payment Failures | App Issue | pagamento, abbonamenti |
| 3 | Poor Usability | App Issue | lenta, difficile |
| 4 | App Not Working | App Issue | aggiornamento, android |
| 5 | Login & Account Issues | App Issue | login, account |
| 6 | Inaccurate Train Info | App Issue | ritardi, ritardi cancellazioni |
| 7 | Station Issues | App Issue | stazioni, stazioni preferite |
| 8 | Ease of Use | Praise | app comoda, app facile |
| 9 | EXCLUDE | - | ottima applicazione, utilissima |
| 10 | EXCLUDE | - | ottima, perfetta |
| 11 | Ease of Use | Praise | facile, intuitivo |
| 12 | Easy Purchases | Praise | biglietti, facile |
| 13 | QR Code Failures | App Issue | codice, metro |
| 14 | EXCLUDE | - | ottimo, complimenti |
| 15 | App Not Working | App Issue | aggiornamento, bug |
| 16 | EXCLUDE | - | funziona funziona, funzionante |
| 17 | Easy Purchases | Praise | pagamento, rapido |
| 18 | Improvement Feedback | App Updates | migliorata, migliorare |
| 19 | Train Service Complaints | Rail Service | servizio pessimo, azienda |
| 20 | Ease of Use | Praise | efficiente, rapida |
| 21 | EXCLUDE | - | dovere, sufficiente |
| 22 | Login & Account Issues | App Issue | registrare, profilo |
| 23 | EXCLUDE | - | ottima app, buona app |
| 24 | Ease of Use | Praise | facile veloce, semplice veloce |
| 25 | EXCLUDE | - | pessima pessima, negativa |
| 26 | EXCLUDE | - | funziona, impossibile utilizzare |
| 27 | EXCLUDE | - | pessima pessima, disastrosa |
| 28 | Station Issues | App Issue | milano, alcune stazioni |
| 29 | Inaccurate Train Info | App Issue | ritardi, app aggiornata |

Cell 7 checks that the map has exactly the topics of the model, and that both identifying keywords of every topic
are still among its top 10 keywords. If the model is retrained and its topics change, some keyword is missing and the
notebook stops with the list of what was not found. In this run all 30 topics were found and 0 keywords were
missing. Two keywords are used because one common word, such as "app", could appear in many topics by chance; two
specific words together are much less likely to survive in a topic that has changed.

Cell 8 then gives every review the label and category of its topic. `map()` looks up each topic number in a
dictionary and returns its value, so all reviews of topic 6 get "Inaccurate Train Info". 12 labels besides
EXCLUDE, 5,998 reviews kept and 953 excluded, a share of 13.7%.

### Merges
Topics with the same label are merged. The merge list is built from the label map, so the two cannot disagree:

| Label | Topics merged |
|---|---|
| Inaccurate Train Info | 0, 6, 29 |
| App Not Working | 4, 15 |
| Login & Account Issues | 5, 22 |
| Station Issues | 7, 28 |
| Ease of Use | 8, 11, 20, 24 |
| Easy Purchases | 12, 17 |

MMR (`diversity=0.3`) is set again, because the saved model does not keep it, and
`merge_topics(texts, topics_to_merge)` is called. It changes only the model: its topic of every review, sizes,
keywords and topic vectors. The labels stay attached to the original 06 ids in `topic`, and the new numbers, which
BERTopic assigns by size, go in their own column, `topic_merged`. After the merge the model has 21 topics: the 12
labels plus the 9 excluded topics, which are left as they are. Cell 11 checks that every merged topic holds one label,
that every kept label is one merged topic, and that the number of merged topics is the number of labels plus the
excluded topics.

### Final topics

| Label | Category | Topic ids | Reviews | Share | Avg ★ | 95% CI |
|---|---|---|---:|---:|---:|---|
| Inaccurate Train Info | App Issue | 0, 6, 29 | 1,501 | 25.0% | 1.78 | 1.72-1.84 |
| Ticket Purchase Failures | App Issue | 1 | 1,143 | 19.1% | 1.41 | 1.36-1.46 |
| App Not Working | App Issue | 4, 15 | 655 | 10.9% | 1.61 | 1.53-1.69 |
| Subscription & Payment Failures | App Issue | 2 | 641 | 10.7% | 1.44 | 1.37-1.51 |
| Poor Usability | App Issue | 3 | 499 | 8.3% | 1.43 | 1.35-1.51 |
| Ease of Use | Praise | 8, 11, 20, 24 | 463 | 7.7% | 4.54 | 4.45-4.62 |
| Login & Account Issues | App Issue | 5, 22 | 289 | 4.8% | 1.40 | 1.31-1.49 |
| Easy Purchases | Praise | 12, 17 | 277 | 4.6% | 3.98 | 3.82-4.14 |
| Station Issues | App Issue | 7, 28 | 244 | 4.1% | 1.73 | 1.58-1.88 |
| QR Code Failures | App Issue | 13 | 118 | 2.0% | 1.59 | 1.42-1.76 |
| Train Service Complaints | Rail Service | 19 | 87 | 1.5% | 1.17 | 1.02-1.33 |
| Improvement Feedback | App Updates | 18 | 81 | 1.4% | 3.63 | 3.35-3.91 |

Excluded topic ids: 9, 10, 14, 16, 21, 23, 25, 26, 27. Category and exclusion totals are in Key numbers.

**Confidence intervals.** For each label the notebook computes the [standard error](glossary.md#standard-error) of
the average rating, `ratings.std() / np.sqrt(n)`, and the 95% margin `t.ppf(0.975, n - 1) * standard_error` from
the [t distribution](glossary.md#t-distribution); the [confidence interval](glossary.md#confidence-interval) is the
average plus or minus the margin. Ratings are treated as independent. They are ordinal (1 to 5 stars), and the mean
is used as is common for star ratings. The intervals show that the App Issue averages overlap, while the two Praise
topics and Improvement Feedback are clearly above them.

### Charts and how to read them
All four use the [Okabe-Ito palette](glossary.md#okabe-ito-palette) for the categories: App Issue `#D55E00`, Praise
`#009E73`, Rail Service `#CC79A7`, App Updates `#0072B2`.
- **`chart_reviews_per_topic.png`** (cell 13). Horizontal bars, largest topic at the top, with the number of reviews
  and the share of the analysis set at the end of each bar. App Issue covers 8 of the 12 topics and 84.9% of the
  reviews.
- **`chart_avg_rating_per_topic.png`** (cell 15). A dot for each average with its 95% interval as a horizontal line,
  on the full 1-5 axis, and a dashed line for the average of all analysed reviews (1.93). Dots are used instead of
  bars because a bar suggests a value that starts from zero, while ratings start from 1. A short line means a precise
  average; Improvement Feedback (81 reviews) has the longest.
- **`chart_keywords_per_topic.png`** (cell 17). One panel per final topic with its top 5 keywords from the merged
  model, in a grid of 4 rows and 3 columns. Bar length is the c-TF-IDF weight. It can be compared within a panel, not
  between panels, so the axis has no numbers. The legend at the bottom gives the category colours, and its title says
  what the bar length means. Singular and plural appear as separate words ("biglietti" and "biglietto") because the keywords come from
  the text without lemmatization. The top word of Poor Usability is "funziona", which confirms that topic 3 is
  borderline. Station Issues has "stazioni", "stazione" and "milano" at the top, and "stazioni preferite" from
  topic 7 next to place names from topic 28. The top words of App Not Working are generic ("app", "aggiornamento",
  "applicazione").
- **`chart_topic_priority.png`** (cell 19). One dot per topic, with its share of the analysed reviews on the x axis
  and its average rating on the y axis, the 95% interval as a vertical line, the full 1-5 scale and a dashed line at
  the average of all analysed reviews (1.93). Each name sits next to its dot. The positions are set by hand in
  `LABEL_POSITIONS`, and the cell checks that no two names overlap (0 overlaps). Problems sit low and praise high.
  Among the problems the averages are close (1.40 to 1.78) and the intervals overlap, so what separates them is how
  often they are mentioned, from 25.0% for Inaccurate Train Info to 2.0% for QR Code Failures.

![Share and average rating per topic](../reports/figures/chart_topic_priority.png)

### Bias checks
- **Ratings of excluded and analysed reviews** (cell 21). The excluded reviews average 3.66 stars, the analysed ones
  1.93, all Italian reviews 2.17. The excluded reviews are short verdicts at both ends of the scale: 55.2% have 5
  stars and 27.5% have 1 star. The analysed ones are mostly negative: 62.3% have 1 star. The full shares are in Key
  numbers. Removing the excluded reviews makes the analysis set more negative than all Italian reviews, an
  [exclusion bias](glossary.md#exclusion-bias): the topics describe what users write about when they say something
  specific, not overall satisfaction.
- **Share excluded per year** (cell 22). It goes from 7.4% in 2017 to 23.8% in 2020, with a peak between 2019 and
  2021 (18.6%, 23.8%, 17.3%). Overall rating trends use all reviews and are not affected. Trends of single topics over
  time use only the analysed reviews, so in 2019-2021 they rest on a smaller part of each year's reviews.

### Output checks

| Check | Result |
|---|---|
| Every review in `topics.csv` is Italian | PASS |
| Same topic for every review in `topics.csv` and in the model | PASS |
| The label map has exactly the 30 topics of the model | PASS |
| Both identifying keywords of every topic among its top 10 keywords | PASS (0 missing) |
| No review without a label | PASS |
| Merged topics | 21 (12 labels and 9 excluded); each holds one label, and each kept label is one merged topic |
| No `author` column in any output | PASS |
| `review_id` pseudonymised (12 hex characters) for every row | PASS |
| Every review found in clean.csv, `reply_text` identical | PASS |
| 12 labels and the 4 categories in analysis.csv, no EXCLUDE rows | PASS |
| No two topic names overlap on `chart_topic_priority.png` | PASS (0 overlaps) |
| Every keyword of `topic_keywords.csv` made of letters only, so no code | PASS (60 keywords) |
| No keyword is a personal name (read by hand: words such as "treni", "biglietti", "milano", "italia") | PASS |

### Recommendations

Cell 29 turns the results into five recommendations. They come from what reviewers write. People who are unhappy
tend to write more, so the shares describe what reviewers complain about, not the experience of every user. All App
Issue topics have average ratings between 1.40 and 1.78 stars with overlapping confidence intervals, so the order
follows how often each problem is mentioned, not how severe it is. Once topics over time are analysed, the order
should be checked against which problems are recent.

1. Fix the train information first. Inaccurate Train Info is the largest topic (25.0% of the analysed reviews).
   Reviewers describe an app that shows a train on time while the station board shows a delay or a cancellation. It
   is also the most reliable label: the manual coding confirmed all 14 sampled reviews, and at least 93.5% of its
   reviews keep this label in every seed tested (§10).
2. Make buying and using a ticket reliable. Ticket Purchase Failures (19.1%), Subscription & Payment Failures
   (10.7%) and QR Code Failures (2.0%) together are 31.7% of the reviews (1,902 of 5,998). They describe the same
   journey, from paying to showing the ticket at the gate. With one of the seeds tested, the model merges the
   subscription reviews into Ticket Purchase Failures, so these topics are best treated as one area.
3. Improve stability and usability: App Not Working (10.9%), Poor Usability (8.3%), Login & Account Issues
   (4.8%) and Station Issues (4.1%). About half of the sampled App Not Working reviews (6 of 14 in the manual coding)
   only say that the app does not work, without details.
4. Start replying to reviews again. Trenord replied to 83% to 100% of Italian reviews every year until 2020, and
   to fewer than 4% every year since 2022. Ratings fell in the same years, but this analysis does not show that one
   caused the other.
5. Keep what users like. Ease of Use and Easy Purchases are 12.3% of the reviews. Changes to the app should not
   break them.

### The two models
- **`bertopic_model_trained/`** is trained and saved by 06 and read by 07. Its topic ids are the ones the label map refers
  to.
- **`bertopic_model_merged/`** is saved by 07 after the merges, in the same format. It has 21 topics and the
  keywords of the merged topics, the ones shown in chart 3. It is kept for reuse, for example to look at the merged
  topics again, and no other step of the pipeline reads it.

Both are local only and gitignored.

### Design decisions
- **Label map keyed on the 06 topic ids.** `merge_topics()` renumbers all topics by size.
  - An earlier version keyed its labels on post-merge ids of an earlier model. After the 2026-09-01 rescrape and
    retraining, those labels pointed to the wrong topics without any error.
  - Ids from 06 plus the identifying keywords turn that silent failure into an explicit error.
- **Identifying keywords instead of fixed topic sizes.** The check compares what a topic is about, not how many
  reviews it has, so it catches a changed model even if the sizes happen to be similar.
- **Merge list derived from the labels.** It cannot disagree with the label map.
- **Exclusion rule.** A topic is excluded when it consists mostly of very short reviews (about five words or fewer)
  with generic sentiment and no indication of what works or fails.
- **Topic 3 kept as Poor Usability.** It is borderline: 51.9% of its reviews have 5 words or fewer, and many are
  generic. It is kept because it is the only topic about clarity, complexity and slowness; excluding it would remove
  that dimension and make the excluded set even more positive.
- **Topics 7 and 28 merged into Station Issues.** Topic 7 is about favourite stations that get lost and a station
  search that does not work, topic 28 about stations removed from the app or missing from its list, often after an
  update. The two were hard to tell apart, so they share one label. Both are App Issues: something that worked and
  stopped working. A few fare and route complaints are mixed into topic 28.
- **Topics 0, 6 and 29 merged into Inaccurate Train Info.** All three are about delays and cancellations shown
  late, wrong or not at all.
- **App Not Working includes generic complaints.** Next to crashes and problems after an update, topics 4 and 15
  hold reviews that only say the app does not work, without saying what fails. They are kept in the label because
  they are not separated from the others in the model.
- **Topic 23 excluded.** Its reviews say "ottima app" and nothing else, while the Ease of Use topics name a specific
  quality.
- **No category for feature requests.** Requests are scattered across topics and dominate none of them.
- **Labels renamed on 2026-11-12.** After the blind coding of 08, eight of the 13 labels got a new name, and two
  of them now share one:
  Unreliable Train Status became Inaccurate Train Info, Subscription Purchase Failures became Subscription & Payment
  Failures, App Crashes & Freezes became App Not Working, Station & Favorites Bugs and Missing Stations became
  Station Issues, Easy Purchase & Payment became Easy Purchases, Rail Service Complaints became Train Service
  Complaints, and Version Comparisons became Improvement Feedback. The topic ids, the identifying keywords and the
  categories did not change, so the label of each review changed only in its name, apart from the join.
- **Text inspection kept out of the notebook.** The manual review notes contain review texts and stay local
  (`labeling/`, gitignored). The notebook prints only counts, aggregates and keywords.
- **Dots for averages, one palette everywhere.** Ratings start from 1, so averages are dots on a 1-5 axis. The
  Okabe-Ito colours stay distinct for readers with colour vision deficiency and are the same in notebook 04 and in
  the dashboard.

### Known limitations
- The labels, the categories and the exclusion rule were decided by one person.
- The exclusion rule was written after reading the topics, not before.
- The labels were checked against a blind coding of a sample (§10), but by the same person who wrote them, not by
  a second coder.
- App Not Working is partly a catch-all for generic complaints: in 08 only 7 of its 14 sampled reviews are confirmed.
- The analysis set is more negative than the full dataset, and the share excluded changes from year to year.
- The confidence intervals treat ratings as independent and use the mean of an ordinal scale.
- Poor Usability includes many short, generic complaints.

---

## 10. Notebook 08 - Label validation

08 checks the 12 labels of 07 in three parts. Part 1 trains the model of 06 again with other UMAP seeds and
measures how many reviews keep their label. Part 2 draws a sample of reviews for
[blind coding](glossary.md#blind-coding) by hand. Part 3 compares my coding of the sample with the model labels. It
changes no label. In `data/processed/` it writes only `validation_summary.csv`, the agreement numbers the dashboard
shows.

The sample was drawn and coded when 07 still had 13 labels. Eight of them were renamed afterwards, two of them into
the same name, Station Issues (§9). My coding, the codebook and the key keep the names of that time, and 08 maps them to the
current names in code, without editing the files in `labeling/`.

### Input and output
- Input: `trenord_reviews_clean.csv`, filtered to `language == "it"`, with `text_clean` as in 06, and
  `trenord_reviews_labeled.csv` (from 07), for its `topic` and `topic_label` columns. Cell 3 checks that the two
  files list the same reviews in the same order.
- Part 3 also reads the sheet `coding` of `labeling/validation_sample.xlsx`, with my labels, and
  `labeling/validation_key.csv`.
- Output: the stability and agreement tables in the notebook, `reports/figures/chart_label_confusion.png`, and
  three files in `labeling/` (gitignored, they contain review texts):
  - `validation_sample.xlsx` and `validation_key.csv`, written only if `validation_sample.xlsx` does not exist
    yet, so a rerun never overwrites the coding;
  - `validation_disagreements.csv`, written again on every run from the other two.
- Output for the dashboard: `data/processed/validation_summary.csv`, one row per measure (`raw_agreement`,
  `cohens_kappa`, `weighted_agreement`) with `value`, `ci_low`, `ci_high` and `sample_size`. Numbers only, no labels
  of single reviews and no texts.

### Method
1. Load both files and check that they list the same reviews (cell 3). Prepare the texts as in 06 (cell 4).
2. Compute the embeddings once with `paraphrase-multilingual-mpnet-base-v2` (cell 5). They do not depend on the
   UMAP seed.
3. `train_topic_model(umap_random_state)` trains with the settings of 06 and reduces the outliers as in 06
   (cell 6). Train it for seeds 42, 0, 1, 2 and 3 (cell 7).
4. Check that seed 42 gives every review the topic saved in `trenord_reviews_labeled.csv` (cell 8).
5. Give each topic of the other seeds the current label of most of its reviews, measure the share of reviews that
   keep their label, and show where the reviews of the lost labels go (cells 10-12).
6. Rebuild the strata the sample was drawn from (cell 15): the renamed labels go back to their old name, and
   Station Issues is split again by its 06 topic, 7 for Station & Favorites Bugs and 28 for Missing Stations. Every
   stratum must map back to the current label of its review.
7. Write the codebook (cell 16), draw a [stratified sample](glossary.md#stratified-sample) (cell 17), shuffle it
   (cell 18), write the two files (cell 19) and read them back (cell 20).
8. Load my coding and check it: 196 rows, every `my_label` filled, only the 15 labels of the codebook. A failed
   check raises an error that names only the `sample_id` of the wrong rows (cell 24). Join it with the key on
   `sample_id` (cell 25).
9. Map my labels and the key's labels to the current names with `NEW_LABEL_NAMES`, and keep the key's label as the
   stratum of the review (cell 27).
10. Compute the raw agreement and [Cohen's kappa](glossary.md#cohens-kappa) on the sample (cell 29), and the
    weighted agreement on all reviews (cell 31).
11. Compute 95% intervals for the three numbers with a [bootstrap](glossary.md#bootstrap) (cells 33-34), and save
    the three numbers with their intervals and the sample size to `validation_summary.csv` (cell 35).
12. Compute the [precision](glossary.md#precision) of each label (cell 37), the
    [confusion matrix](glossary.md#confusion-matrix) as a table and a chart (cells 39-40) and the five most frequent
    disagreements (cell 41).
13. Write the disagreements, with their texts, to `labeling/validation_disagreements.csv` (cell 43).

### Parameters
| Parameter | Value |
|---|---|
| UMAP seeds | 42, 0, 1, 2, 3 |
| Model settings | as in 06: UMAP `n_neighbors=15`, `n_components=5`, `min_dist=0.0`, `metric="cosine"`; HDBSCAN `min_cluster_size=30`; `min_df=5`; MMR `diversity=0.3`; outliers reduced with `strategy="embeddings"`, `threshold=0.0` |
| `SAMPLE_PER_LABEL` | 14 |
| `SAMPLE_SEED` | 42, for the sample and for its order |
| `NEW_LABEL_NAMES` | the 8 old label names that changed, each with its current name |
| `STATION_STRATUM_BY_TOPIC` | `{7: "Station & Favorites Bugs", 28: "Missing Stations"}` |
| `BOOTSTRAP_RESAMPLES` | 2000 |
| `BOOTSTRAP_SEED` | 42, for `np.random.default_rng` |

### Results: one model per seed
| Seed | Topics | Outliers before reduction | Labels that are the majority in at least one topic |
|---|---|---|---|
| 42 | 30 | 1,601 | - |
| 0 | 33 | 2,023 | 13 of 13 |
| 1 | 27 | 1,264 | 13 of 13 |
| 2 | 31 | 1,564 | 13 of 13 |
| 3 | 27 | 984 | 11 of 13 |

The labels are the 12 of 07 plus EXCLUDE. Seed 42 gives every review the topic of `trenord_reviews_labeled.csv`:
0 of 6,951 reviews differ (cell 8). No topic of the other seeds has a tie between two labels.

### Stability of the labeled themes
The topics of a new seed have new numbers, so they cannot be matched to the old ones by number. Each new topic
gets the current label (one of the 12, or EXCLUDE) that most of its reviews have now. A review keeps its label if
its new topic carries the label it has now. The table gives, for each label, the share of its reviews that keep
it, and in the last row the share of all reviews (cell 11).

A made-up example: a new topic has 100 reviews, 70 now labeled Ticket Purchase Failures, 20 Subscription & Payment
Failures and 10 EXCLUDE. It gets Ticket Purchase Failures; the 70 keep their label and the other 30 do not. A
label that is the majority in no new topic keeps 0%.

| Label | Reviews | Seed 0 | Seed 1 | Seed 2 | Seed 3 |
|---|---|---|---|---|---|
| Inaccurate Train Info | 1,501 | 98.6% | 97.1% | 95.5% | 93.5% |
| Ticket Purchase Failures | 1,143 | 93.8% | 97.8% | 98.4% | 99.4% |
| EXCLUDE | 953 | 96.2% | 81.3% | 86.6% | 82.9% |
| App Not Working | 655 | 91.3% | 92.4% | 88.2% | 83.7% |
| Subscription & Payment Failures | 641 | 95.6% | 98.3% | 94.4% | 0.0% |
| Poor Usability | 499 | 86.6% | 97.4% | 98.2% | 96.6% |
| Ease of Use | 463 | 96.3% | 96.5% | 98.3% | 95.0% |
| Login & Account Issues | 289 | 94.1% | 95.2% | 91.0% | 0.0% |
| Easy Purchases | 277 | 94.2% | 93.1% | 89.9% | 82.3% |
| Station Issues | 244 | 89.3% | 93.4% | 92.2% | 88.1% |
| QR Code Failures | 118 | 95.8% | 98.3% | 97.5% | 93.2% |
| Train Service Complaints | 87 | 88.5% | 82.8% | 86.2% | 79.3% |
| Improvement Feedback | 81 | 95.1% | 93.8% | 86.4% | 96.3% |
| Overall | 6,951 | 94.6% | 94.1% | 93.6% | 79.1% |

- With seeds 0, 1 and 2, 93.6% to 94.6% of the reviews keep their label, and every label keeps at least 81.3%.
- With seed 3, 79.1%. Subscription & Payment Failures and Login & Account Issues are the majority in no topic:
  98.8% of the subscription reviews and 96.9% of the login reviews end up in topics where Ticket Purchase Failures
  is the majority (cell 12). Seed 3 is also the seed with the lowest ARI against seed 42 in 05 (0.515, §7).
- The two largest labels are the most stable: Inaccurate Train Info keeps 93.5% to 98.6%, Ticket Purchase
  Failures 93.8% to 99.4%.
- Station Issues, which joins two topics of 06, keeps 88.1% to 93.4%.
- Among the labels that never disappear, EXCLUDE (81.3% to 96.2%) and Train Service Complaints (79.3% to 88.5%)
  move the most.

Most themes come back with every seed. The split between ticket, subscription and login problems depends on the
seed: in one seed out of four it is gone.

### The blind coding sample
- 14 reviews from each of the 14 strata, 196 in total, drawn with `random_state=42` (cell 17). The strata are the
  13 labels of the time the sample was drawn and EXCLUDE, rebuilt in cell 15. Station Issues is two strata, Station &
  Favorites Bugs and Missing Stations, so it has 28 reviews in the sample and every other label 14.
- The rows are shuffled with the same seed, and `sample_id` (1 to 196) is given after the shuffle, so neither the
  order nor the id says anything about the label. The longest run of the same stratum in a row is 2 (cell 18). No
  review in the sample has an empty text.
- `validation_sample.xlsx` has two sheets:
  - `coding`: `sample_id`, `text` (the review as written, not `text_clean`, because a person reads it) and an empty
    `my_label` column with a dropdown;
  - `codebook`: one row per label of that time with its category and a one-line definition taken from the comments
    of the label map in 07, plus EXCLUDE (short generic verdict with no specific content) and "None of these" (the
    review fits no label). 15 rows, with the old names.
- The dropdown reads its values from the label column of the codebook sheet. A list written inside the rule would
  pass the 255 characters Excel allows.
- `validation_key.csv` holds `sample_id` and `model_label`: the hidden key, not opened before the coding is done.
- Cell 20 reads both files back and prints only counts: 196 rows in the coding sheet, 15 in the codebook, 196 in
  the key, the same texts and ids as the sample, 14 reviews for each of the 14 labels in the key.

#### Why blind

If the model label is visible while coding, it is easy to agree with it. With the key in a separate
file, my label is given from the text and the codebook only.

#### Why stratified

A simple random sample of 196 would follow the label sizes: mostly Inaccurate Train Info and
Ticket Purchase Failures, and one or two reviews from the smallest strata, Missing Stations (71 reviews, now part of
Station Issues) or Improvement Feedback (81). That is too few to say anything about the small labels. With 14 from
each stratum, every label can be checked.

#### Why a weighted agreement is needed

In the sample every stratum has
the same weight, 14 of 196, while in the data the sizes go from 71 to 1,501 reviews. The plain share of matches in
the sample therefore over-weights the small strata. To estimate the agreement over all reviews, the agreement of each
stratum is weighted by its share of all reviews (a [weighted accuracy](glossary.md#weighted-accuracy), called weighted
agreement in 08). A made-up example with two labels: label A holds 90% of the
reviews and is right 9 times out of 10 in the sample, label B holds 10% and is right 5 times out of 10. The plain
share of matches is 14 of 20, 70%; the weighted accuracy is 0.9 x 90% + 0.1 x 50% = 86%.

### Agreement between my coding and the model
I coded the 196 reviews in `validation_sample.xlsx` without opening the key. Cell 24 found 196 rows, no empty label,
no label outside the codebook, and 15 of the 15 labels used. Cell 25 joined all 196 rows with the key.

Cell 27 maps my labels and the key's labels to the current names; the two station labels both become Station
Issues. The key's label of that time is kept in its own column as the stratum of the review. As a check, the mapped
model label of every review equals its label in `trenord_reviews_labeled.csv` (0 different). After the mapping I
used 14 labels, the model 13, and the reviews come from 14 strata.

The raw agreement is the share of reviews where my label equals the model label. Cohen's kappa corrects it for the
agreement expected by chance, given how often each of us used each label. Both use the 14 labels used by either of
us, None of these included; the model never gives None of these, so those reviews count as disagreements.

The weighted agreement first computes the share of agreement inside each stratum, then averages the 14 shares
weighting each stratum by its number of reviews in `trenord_reviews_labeled.csv`, EXCLUDE included. Station Issues
counts as its two strata, each with its own size. Each stratum then weighs as much as it does in the data, so the
result estimates the agreement on a review drawn at random from all 6,951.

The intervals come from one bootstrap loop (cell 33): 2,000 resamples, each drawn as the sample was, 14 reviews with
replacement inside each stratum, with `np.random.default_rng(42)`. The kappa of each resample uses the same 14
labels. The weights stay fixed, because they come from all reviews. The 95% interval is the 2.5th to 97.5th
percentile of the 2,000 values.

| Measure | Describes | Value | 95% CI |
|---|---|---|---|
| Reviews with the same label | sample | 162 of 196 | - |
| Raw agreement | sample | 82.7% | 78.1% to 87.2% |
| Cohen's kappa | sample | 0.812 | 0.763 to 0.862 |
| Weighted agreement | all 6,951 reviews | 86.6% | 81.7% to 91.2% |

The precision of a label is the share of the sampled reviews the model put in it to which I gave the same label
(cell 37). For 11 labels and EXCLUDE the label is one stratum, and the precision is the simple share of its 14
reviews. Station Issues is two strata with very different sizes, 173 and 71 reviews. A simple share of its 28 reviews
would give the smaller one too much weight, so its precision is the share inside each stratum, weighted by the
number of reviews of that stratum in `trenord_reviews_labeled.csv`. The column "Confirmed" is a plain count for
every label.

| Label | Sampled reviews | Confirmed | Precision |
|---|---|---|---|
| Inaccurate Train Info | 14 | 14 | 100.0% |
| Ticket Purchase Failures | 14 | 12 | 85.7% |
| EXCLUDE | 14 | 13 | 92.9% |
| App Not Working | 14 | 7 | 50.0% |
| Subscription & Payment Failures | 14 | 14 | 100.0% |
| Poor Usability | 14 | 10 | 71.4% |
| Ease of Use | 14 | 13 | 92.9% |
| Login & Account Issues | 14 | 13 | 92.9% |
| Easy Purchases | 14 | 9 | 64.3% |
| Station Issues | 28 | 19 | 78.3% |
| QR Code Failures | 14 | 14 | 100.0% |
| Train Service Complaints | 14 | 10 | 71.4% |
| Improvement Feedback | 14 | 14 | 100.0% |

#### Confusion matrix

![Confusion matrix of my labels and the model labels](../reports/figures/chart_label_confusion.png)

`chart_label_confusion.png` (cell 40): my labels in the rows, the model labels in the columns, both in the order of
the stability table and with the current names, with None of these as the last row: 14 rows and 13 columns. Each
cell counts the sampled reviews with that pair of labels; empty cells are 0. The diagonal holds the 162 agreements;
every cell off the diagonal is a disagreement. The colour goes from white to dark blue as the count grows. Each
column adds up to 14, except Station Issues, which adds up to 28.

| My label → model label | Reviews |
|---|---|
| EXCLUDE → App Not Working | 6 |
| EXCLUDE → Station Issues | 4 |
| Ticket Purchase Failures → Station Issues | 2 |
| EXCLUDE → Poor Usability | 2 |
| Poor Usability → Train Service Complaints | 2 |

The 34 disagreements fall in 22 pairs of labels. The table shows the five most frequent; a sixth pair, None of these
→ Easy Purchases, also has 2 reviews and is left out only by the order of the table (cell 41). 13 disagreements are
reviews I coded EXCLUDE and 5 are reviews I coded None of these.

#### Reading the agreement
- The kappa, 0.812 (0.763 to 0.862), falls in the "almost perfect" band (0.81 to 1.00) of the
  [Landis and Koch](glossary.md#landis-and-koch-scale) (1977) scale, just above its lower edge, and its interval
  reaches down into "substantial" (0.61 to 0.80). The scale is a convention, with bands chosen by judgment, not a
  test.
- The raw agreement and the kappa describe the 196 sampled reviews, where each of the 14 strata weighs the same. The
  weighted agreement estimates the agreement on all 6,951 reviews. It is higher because most reviews are in labels
  with a high precision: Inaccurate Train Info 100.0%, Ticket Purchase Failures 85.7%, EXCLUDE 92.9%. The lowest
  precision, App Not Working with 50.0%, is a large label (655 reviews), so it pulls the weighted number down.
- 13 of the 34 disagreements are reviews I coded EXCLUDE while the model gave them a specific label. The largest
  pair is EXCLUDE → App Not Working, with 6 reviews, so only 7 of the 14 App Not Working reviews are confirmed. This
  fits what the label holds: next to crashes and update problems, generic "it does not work" reviews that I coded as
  verdicts. Most disagreements are about the line between a generic verdict and a specific problem.
- Station Issues joins two topics that were hard to tell apart. Every review I coded as a station issue is a station
  issue for the model too, and 19 of its 28 sampled reviews are confirmed; the other 9 go to five different labels,
  4 of them to EXCLUDE and 2 to Ticket Purchase Failures. Its precision, weighted over its two strata, is 78.3%.
- `validation_disagreements.csv` (cell 43) holds the 34 disagreements with `sample_id`, text, my label and model
  label, to study them. It is not published.

### Design decisions
- The training function is written in 08, not imported from 05: notebooks do not import each other, and 08
  needs only the seed as a parameter.
- The ARI of 05 compares the 30 topics. The results are reported on the 12 labels, so 08
  measures whether the labels come back.
- Each new topic takes the majority label of its reviews. This needs no reading of the new topics, so it can be repeated for every seed.
- The two files are written only once. The Excel file holds my coding, so it is never overwritten. If the data changed, cell
  20 would show `Same texts as the sample: False`.
- The renamed labels are mapped in code, not in the files. My coding stays as I did it, with the names of that
  time, and the mapping is written once, in `NEW_LABEL_NAMES`.
- The strata stay those of the sample: 13 labels of that time and EXCLUDE. The sample was drawn that way, so the
  weights and the bootstrap use them. They are rebuilt from the current label and, for Station Issues, from the 06
  topic, which is the only way to tell its two strata apart.
- The precision of Station Issues is weighted by the size of its two strata, as the weighted agreement is. A simple
  share of its 28 reviews would treat the 71 reviews of topic 28 as if they were as many as the 173 of topic 7.
- Kappa uses every label used by either of us, None of these included. Leaving None of these out would drop 5
  reviews that the model did label, and make the agreement look higher.
- The bootstrap resamples inside each stratum, 14 per stratum, because the sample was drawn that way. A resample
  of 196 from the whole sample would let the number of reviews per stratum vary, which the real sample never does.
- The disagreements file is written again on every run: it is computed from the other two files and holds no work
  of its own.
- Two warnings print a local path, so cell 2 hides them with `warnings.filterwarnings`, before the imports: tqdm
  warns at import that ipywidgets is missing, and openpyxl warns when it reads the coding file, because Excel added
  an extension to the dropdown that openpyxl cannot read. The labels are read anyway.

### Validation
- Rerun of 2026-11-05 in a fresh kernel, 406 s. The two files were created in that run and read back as above.
- Rerun of 2026-11-12 in a fresh kernel with the `venv_trenord` kernel, 395 s, after part 3 was added:
  - seed 42 gives the same topic as `trenord_reviews_labeled.csv` for all 6,951 reviews, and the outputs of part 1
    and part 2, the stability table included, are identical to the previous run;
  - `validation_sample.xlsx` and `validation_key.csv` were not written again: the notebook printed that the Excel
    file already exists, and both files have the same SHA-256 hash before and after the run;
  - the notebook reads 196 coded reviews, and the checks of the coding pass.
- Rerun of 2026-11-12 in a fresh kernel with the `venv_trenord` kernel, 313 s, after the labels of 07 were renamed
  and two joined:
  - seed 42 still gives the same topic as `trenord_reviews_labeled.csv` for all 6,951 reviews (0 differ);
  - every stratum maps back to the current label of its review (cell 15, 0 mismatches), and the sample is the same
    as before (cell 20, same texts and ids);
  - `validation_sample.xlsx` and `validation_key.csv` have the same SHA-256 hash before and after the run;
  - the labels that were only renamed keep the same stability shares as in the previous run.
- Rerun of 2026-11-13 in a fresh kernel with the `venv_trenord` kernel, 447 s, after the cell that saves
  `validation_summary.csv` was added:
  - every output of the previous run is unchanged, the confusion matrix chart is byte-identical, and the three files
    in `labeling/` have the same SHA-256 hash before and after the run;
  - `validation_summary.csv` holds the numbers printed above: 82.7%, 0.812 and 86.6%, with their intervals, on 196
    reviews.
- A first attempt with the kernel named `python3` started the system Python instead of the venv, and seed 42 gave
  different topics. The notebook must run in the `venv_trenord` kernel, the environment of the lock file.
- `labeling/` is gitignored, and none of its files is tracked or staged.
- The saved outputs show only counts, shares and labels: a scan found no key, review text (also as tokens), author
  name or local path.

### Known limitations
- Four seeds are compared with seed 42. Other seeds may split the topics in other ways.
- The majority mapping is generous: each new topic takes the label that fits most of its reviews. It shows whether
  the themes come back, not whether a person reading the new topics would name them the same way.
- The mapping can only use the current labels, so it cannot find a theme that appears only with a new seed.
- The sample was coded by one person, the same who wrote the labels and the codebook, so the comparison checks
  consistency more than independent agreement.
- The coding was blind to the model label of each review, but not to the labeling work of 07, where I read the
  keywords and many reviews of each topic.
- The confidence intervals describe sampling uncertainty only. They do not include the uncertainty of my judgment
  or of the codebook definitions.
- 14 reviews per stratum give only a rough precision for each label, because each review counts for 1 in 14.
- The labels were renamed, and the two station labels joined, after I had coded the sample and seen the
  disagreements. Joining them turned one disagreement into an agreement, so the comparison is not fully independent
  of the labels it checks.
- The sample is drawn by model label, so it measures precision. How many reviews of a theme the model put in another
  label (the recall) is not measured.

---

## 11. Dashboard

The dashboard is one web page, `dashboard/app.py`. It tells the results in order of importance, for a reader who has
never seen the project. Every number on it is computed from the published files when the page loads, so nothing is
copied by hand.

### Layout
`st.set_page_config` sets `layout="wide"`, and a small CSS rule keeps the main content at most 1,200 pixels wide and
centred, so lines of text stay short on a large monitor. From top to bottom:

1. Header. A banner in Trenord green with a red bottom border. Title: "Trenord App Reviews - What Users Say".
   Subtitle, computed from the first and the last review date: "6,951 Google Play reviews in Italian, May 2015 to
   August 2026".
2. Three key number cards, side by side on a computer and one under the other on a phone (see below).
3. What users write about. The sentence "Each review was assigned to one of 12 topics. The bars show each topic's
   share of the 5,998 reviews about a specific topic." Then a horizontal bar chart of the 12 topics, largest first,
   coloured by category, with a legend of the four categories. The topic name is written above each bar and only the
   share is written next to it, with one decimal. The chart has no x axis and no grid lines. A caption says that 953
   reviews (13.7% of the 6,951) only give a generic verdict and were set aside ([generic
   reviews](glossary.md#generic-review)). The expander "Show the full table"
   holds topic, category, reviews, share, average rating and its 95% confidence interval.
4. How it changed. The sentence "Average rating and share of reviews with a reply, year by year.", a checked title
   (see below) and one chart with two panels on the same year axis: "Average rating per year" and "Reviews with a
   reply, per year". The legend has two entries: "Year" and "Jan-Aug 2026". The caption is "The two lines move
   together, but this does not prove one caused the other."
5. Explore a topic. A dropdown with the 12 topics, largest first. Inside a frame: the category as a coloured badge,
   three metrics, the 5 most typical words, the share of the topic per year, its rating distribution and its most
   upvoted reviews (see below).
6. About this analysis. Three short paragraphs (see below).
7. Footer. One small centred line: "Paolo Troia · LinkedIn · GitHub", with links to LinkedIn and to the repository.

### Data files read
Paths are built from `Path(__file__).parent.parent / "data" / "processed"`. Each file is read once and kept in
memory with `st.cache_data`.
- `trenord_reviews_labeled.csv` (07): all 6,951 Italian reviews, the generic ones (`EXCLUDE`) included. Used for
  the subtitle, the yearly rating and reply rate, the cards and the number of generic reviews.
- `trenord_reviews_analysis.csv` (07): the 5,998 reviews of the 12 topics. Used for the topic chart, the full table
  and the explorer.
- `top_reviews_per_topic.csv` (07): the most upvoted reviews of each topic.
- `topic_keywords.csv` (07): the 5 most typical words of each topic (§9).
- `validation_summary.csv` (08): the agreement numbers (§10). The page shows the weighted agreement and the sample
  size, in "About this analysis".

### Years
- The last complete year is the year of the latest review if that review is dated 31 December, otherwise the year
  before. The latest review is dated 2026-08-04, so the last complete year is 2025.
- A year is shown only if it has at least `MIN_REVIEWS_PER_YEAR = 30` reviews. Every year from 2015 to 2025 has
  more (the fewest is 154, in 2016).
- The year after the last complete one is a [partial year](glossary.md#partial-year). It is shown only if it has at least 30 reviews: 2026 has
  314.
- The partial year is named by its months: the month of its first review and the month of its last one, with the
  short English month names. The first review of 2026 is dated 2026-01-03 and the last 2026-08-04, so the page writes
  "Jan-Aug 2026". If both reviews were in the same month, it would write only that month.
- 2015 starts in May, so it is not a full year either. For this reason the legend of the trend chart says "Year",
  not "Full year".

### The three key number cards
Each card is an `st.metric` with a label, a value, a grey note under it and a help text behind the question mark.
The cards use the partial year if there is one, otherwise the last complete year. Each number is rounded once, and
the value and the note use the same rounded number.

| Card | Value | Grey note | Help text |
|---|---|---|---|
| Average rating, Jan-Aug 2026 | mean `rating` of the Jan-Aug 2026 reviews: 1.49 stars | the same for the first year shown: 3.54 in 2015 | "Average stars given in reviews written in Jan-Aug 2026." |
| Reviews about app problems | share of the 5,998 topic reviews in App Issue topics: 84.9% | number of `EXCLUDE` reviews: excludes 953 generic reviews | "Share of reviews that describe a problem with the app. Generic reviews like 'great' or 'terrible' are left out." |
| Reviews with a reply, Jan-Aug 2026 | mean of `has_reply` in Jan-Aug 2026: 3.5% | the same for the first year shown: 87.1% in 2015 | "Share of reviews written in Jan-Aug 2026 that got a reply." |

### The topic chart
- Share of a topic: its reviews divided by the 5,998 topic reviews. From 25.0% (Inaccurate Train Info) to 1.4%
  (Improvement Feedback).
- Title, computed: "Inaccurate Train Info is the most common topic: 1 review in 4". The 4 is 100 divided by the
  share of the largest topic (25.0%), rounded.
- The x range ends 18% after the longest bar, so its label fits on a phone.
- Hovering a bar shows the topic, its category, its share, its number of reviews and its average rating.
- Full table: the average rating of each topic with its 95% confidence interval, mean ± t(0.975, n-1) · s / √n, as
  in 07. For example, Inaccurate Train Info has 1.78 stars (1.72 to 1.84). Reply rates are shown only per year: one rate
  over all years would mix the years with replies to almost every review and the years after 2020 with almost none.

### The trend chart and its checked title
The two panels show the yearly average rating and the yearly share of reviews with a reply, for every year from
2015 to 2025, and Jan-Aug 2026 as a grey dashed segment. Only some points carry their value, so the labels never
touch on a phone: the peak, the first year, the last year and the lowest point, skipping a point next to one already
labelled. The reply values have one decimal, like the cards. Hovering shows every value.

The title is made of two sentences, and each one is written only if a check on the yearly values is true:
- "Replies almost stopped after 2020." Check: every year after 2020 has a lower reply rate than 2020 (98.2%). True:
  32.1% in 2021, then from 1.7% to 3.5% from 2022 to Jan-Aug 2026.
- "Ratings have been at their lowest since 2023." Check: the best year from 2023 on is below the worst year before
  2023. True: the best from 2023 on is 1.52 (2025), the worst before is 1.95 (2018).

The two years are the constants `LAST_REPLY_YEAR = 2020` and `FIRST_LOW_RATING_YEAR = 2023`. If new data made a check
false, its sentence would disappear from the title instead of saying something wrong.

| Year | Reviews | Average rating | Reviews with a reply |
|---|---|---|---|
| 2015 | 186 | 3.54 | 87.1% |
| 2016 | 154 | 3.25 | 100.0% |
| 2017 | 242 | 2.50 | 99.2% |
| 2018 | 452 | 1.95 | 96.7% |
| 2019 | 1,005 | 2.74 | 83.7% |
| 2020 | 731 | 3.08 | 98.2% |
| 2021 | 670 | 2.34 | 32.1% |
| 2022 | 860 | 2.19 | 3.1% |
| 2023 | 929 | 1.50 | 2.7% |
| 2024 | 755 | 1.49 | 2.0% |
| 2025 | 653 | 1.52 | 1.7% |
| Jan-Aug 2026 | 314 | 1.49 | 3.5% |

### The topic explorer
- Category badge: `st.badge` accepts only a few named colours, so each category gets the closest one: App Issue red,
  Praise green, Rail Service violet, App Updates blue (`CATEGORY_BADGE_COLORS`).
- Three metrics: reviews, share of the topic reviews and average rating. The help text of the average rating gives
  its interval, for example "95% confidence interval: 1.72 to 1.84 stars." Reply rates stay per year, as in the
  full table.
- Most typical words: the 5 keywords of `topic_keywords.csv`, in Italian.
- Share per year: the share of the topic among the topic reviews of each complete year with at least 30 topic
  reviews (every year from 2015 to 2025). Title, computed: "Highest share in <year>: <x.x>%", for example "Highest
  share in 2018: 42.6%" for Inaccurate Train Info. Caption: "Generic reviews left out vary by year (7.4% to 23.8%), so
  compare years with care." The two numbers are the lowest and the highest share of `EXCLUDE` reviews among the
  years of the chart (2017 and 2020). If no year had enough reviews, an `st.info` message would replace the chart and
  its caption.
- Rating distribution: the share of the topic reviews with each number of stars. Title, computed, for example "63% of
  these reviews give 1 star".
- Most upvoted reviews: up to 5 reviews from `top_reviews_per_topic.csv`, each in an expander with its upvotes, stars
  and date. The first one is open.

### About this analysis
Three short paragraphs. Every number is read from the data files:

> 6,951 Italian reviews from Google Play, grouped into 12 topics with BERTopic and named by hand. 953 generic reviews
> like "great" or "terrible" are left out. A manual check of 196 reviews agrees with the topics in 86.6% of cases.
>
> Google Play only. Unhappy users write more, so the shares describe reviewers, not all users.
>
> Code and full method on GitHub.

86.6% is the weighted agreement of `validation_summary.csv` and 196 its sample size (§10). "GitHub" links to the
repository.

### Theme and brand colours
`.streamlit/config.toml` sets the [theme](glossary.md#streamlit-theme). Streamlit reads it when it starts, and Streamlit Cloud reads the same file
from the repository.

| Setting | Value |
|---|---|
| `base` | `light` |
| `primaryColor` | `#006633` |
| `backgroundColor` | `#FFFFFF` |
| `secondaryBackgroundColor` | `#F2F4F3` |
| `textColor` | `#262730` |
| `font` | `sans-serif` |

The two brand colours come from trenord.it, checked on 2026-11-13:
- Trenord green `#006633` is the background of the header bar of the site, the rule
  `.header-top .background-top{background-color:#006633}` in its stylesheet.
- Trenord red `#D71920` is the colour of the red mark in the logo image
  `https://www.trenord.it/fileadmin/templates/img/header/logo-top-trenord.png`, sampled from the image.

The brand colours are used only for the interface: the green banner, its red bottom border and the primary colour of
the widgets. The logo is not used. The data keep the [Okabe-Ito](glossary.md#okabe-ito-palette) colours of the
notebooks: App Issue `#D55E00`, Praise `#009E73`, Rail Service `#CC79A7`, App Updates `#0072B2`, and from 1 to 5
stars `#D55E00`, `#E69F00`, `#999999`, `#66C5AB`, `#009E73`. The yearly lines carry no category, so they are dark
grey `#4A4A4A`, and the partial year is a lighter grey `#9B9B9B` with a dashed line.

### Charts
- All charts are Plotly, drawn with `theme=None`, so the style is the one set in the app: white background, light
  grid `#E6E6E6`, the same font size (13) everywhere and no toolbar.
- Chart titles are written above each chart with `st.markdown`, because Markdown wraps on a phone and a Plotly title
  does not.
- Every value can be read without the colours: it is written as text, in the hover or in the full table.
- The page was checked at 1,440 and 390 pixels wide in headless Chrome.

### Parameters

| Parameter | Value | Why |
|---|---|---|
| `MIN_REVIEWS_PER_YEAR` | 30 | So that a year with a handful of reviews cannot make a peak on its own; a common rule-of-thumb sample size, not tuned. |
| `LAST_REPLY_YEAR` | 2020 | The last year with a reply to almost every review, named in the trend title. |
| `FIRST_LOW_RATING_YEAR` | 2023 | The first year of the lowest ratings, named in the trend title. |
| `FONT_SIZE` | 13 | One size for ticks, labels, values and legends, readable on a phone. |
| Labelled yearly points | peak, first, last, lowest | Enough to read the trend without labels touching at 390 pixels. |

### Design decisions
- One scrolling page, with no tabs and no filters. A reader sees the main message in the header and the cards, and
  the explorer keeps the detail for whoever wants it.
- The cards show the newest data, Jan-Aug 2026, and compare it with the first year, 2015. The label always says which
  period it is.
- Reply rates only per year. The reply rate changed so much in 2021 that one rate over all years would describe no
  real year, so the page shows it per year, in the cards and in the trend chart.
- Only the files of the pipeline. The keywords and the agreement numbers are read from two small CSVs written by 07
  and 08. The app does not load the model, so the dashboard needs only streamlit, pandas, plotly and scipy
  (`requirements.txt`). scipy gives the t distribution of the confidence intervals, the same as in 07.

### Validation
`tests/test_dashboard.py` runs the app with `streamlit.testing.v1.AppTest` in 16
[smoke tests](glossary.md#smoke-test), all passing:
- the page renders without exceptions, with its four sections in order;
- the three cards have the expected labels and a value, and the second shows the App Issue share computed from the
  analysis file;
- the dropdown lists the 12 topics sorted by share;
- each of the 12 topics can be selected without exceptions, and the explorer shows its number of reviews (12 tests);
- the expanders hold their content: the full table with 12 rows, and the text of each upvoted review.

AppTest cannot click an expander, so the last test checks that the content inside each expander is rendered.

---

## 12. Reproducibility

**Run order.** 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08, then the dashboard. In normal use 01 is **not** rerun,
because it would make a new snapshot. 05 only compares settings and saves nothing, so it can be skipped. It reads
only `trenord_reviews_clean.csv`. 08 needs the output of 07. It writes its coding files to `labeling/`, which the
dashboard does not read, one chart to `reports/figures/` and `validation_summary.csv`, which the dashboard reads. Its coding files are written only once (§10). It must run in
the `venv_trenord` kernel.

**Environment.**
- Python 3.13.0 (`.python-version`).
- Three requirements files:
  - `requirements.txt`: the dashboard, read by Streamlit Cloud and by the tests in GitHub Actions;
  - `requirements-notebooks.txt`: the packages the notebooks use directly, pinned;
  - `requirements-notebooks.lock.txt`: every package of the environment, with its exact version.
- Full environment: `requirements-notebooks.lock.txt`, a [lock file](glossary.md#lock-file) from `pip freeze`. It
  pins all 144 installed packages, including indirect ones such as transformers, numba and pynndescent.
  - It captures the environment of 2026-11-02. setuptools, already installed, was added to the file on
    2026-11-03, and nbformat with its dependency fastjsonschema, also already installed, on 2026-11-04. openpyxl
    3.1.5 and its dependency et_xmlfile 2.0.0 were installed and added on 2026-11-05, for the Excel file of 08. No
    other version changed. In it 06 reproduces the current topic model exactly and the tests pass.
  - It is not the environment of the earlier model replaced on 2026-11-02 (§8), which was not recorded.
- [Secret key](glossary.md#secret-key) in `.env` (template: `.env.example`).

**How to run.**

```bash
python -m venv venv_trenord
venv_trenord\Scripts\activate                   # Windows; on macOS / Linux: source venv_trenord/bin/activate
pip install -r requirements-notebooks.lock.txt  # notebooks, full pinned environment (or requirements-notebooks.txt)
pip install -r requirements.txt                 # dashboard
cp .env.example .env                            # then replace change_me with the output of:
python -c "import secrets; print(secrets.token_hex(32))"
# Notebooks, from the notebooks/ folder: 01 → 02 → 03 → 04 → 05 → 06 → 07 → 08
streamlit run dashboard/app.py                  # from the repository root
pytest tests/                                   # dashboard smoke tests, from the repository root
```

The tests need only `requirements.txt` and `pytest` (pinned in `requirements-notebooks.txt`). GitHub Actions runs
them on every push and pull request to `main` (`.github/workflows/tests.yml`).

**Your own key.** Everyone who reruns 02 needs their own key, generated as above. A different key gives different
`review_id` values and nothing else: no step uses the id as an input. On 2026-11-02 the key was rotated and the
pipeline rerun. Every `review_id` changed. All other columns of every output were identical, as were the topic of
every review, the 13 labels with their sizes and the six charts (byte-identical).

**Rerun of 2026-11-03.** 02, 03, 04 and 07 were rerun with the same key after the new labeling. The anon, clean
and topics files were identical to the previous run, so every `review_id` is unchanged. The charts changed only in
their titles.

**Rerun of 2026-11-04.** 06 and 07 were rerun in a fresh kernel after new cells were added to both, and 04 after
its colours changed. 06 gave the same topic for every review, the same sizes and the same keywords. The three
CSVs of 07 were identical to the previous commit. The six charts of 04 changed only in their colours.

**Rerun of 2026-11-12.** 07 and 08 were rerun in a fresh kernel after eight labels were renamed, two of them into
the same name, Station Issues (§9). In the labeled and analysis CSVs only `topic_label` and `topic_merged` changed;
every other column is identical to the previous commit. The three charts of 07 and the confusion matrix of 08 were
drawn again with the new labels.

**Second rerun of 2026-11-12.** 07 was rerun in a fresh kernel after the priority chart and the recommendations were
added and the markdown of every notebook was shortened. The three published CSVs and the three earlier charts of 07
are byte-identical to the previous commit; `chart_topic_priority.png` is new. The other notebooks changed only in
their markdown and were not rerun.

**Rerun of 2026-11-13.** 07 and 08 were rerun in a fresh kernel after each got a cell that saves a small file for the
dashboard, `topic_keywords.csv` and `validation_summary.csv`, and 03 after its stopword export was removed. The
three published CSVs of 07, `trenord_reviews_clean.csv`, every chart and the files in `labeling/` are
byte-identical to the previous run.

**Deterministic steps.**
- 02, given the same raw file and key.
- 03, for fixed library versions.
- 04.
- 05, 06 and 08, in the locked environment.
- 07, which loads the 06 model.

**Non-deterministic steps.**
- 01 depends on the live store.
- 06 in a different environment: after the venv was rebuilt, retraining gave a different clustering (§8).

**Why the label map must be rebuilt after retraining in another environment.** The label map refers to the topic
ids and sizes of the 06 model. A model trained elsewhere can number and size its topics differently, so labels
would attach to the wrong reviews. The keyword check of the label map in 07 stops with an error in that case.

**What a fresh clone can reproduce.** The BERTopic model, the raw data and the intermediate CSVs are not published,
so on a fresh clone 06 and 07 cannot run as is. Someone cloning the repository can:
- run the dashboard on the published CSVs;
- inspect every notebook with its saved outputs;
- rerun the whole pipeline on a new scrape with their own key, in the locked environment.

They cannot regenerate the published topics and labels exactly without the original raw data.

---

## 13. Privacy and data handling

| Item | Status |
|---|---|
| Raw reviews (`data/raw/`) | local only, gitignored |
| Anon, clean and topics CSVs | local only, gitignored |
| BERTopic models | local only, gitignored |
| Manual labeling notes, the validation sample of 08 with its key and the disagreements file (`labeling/`, contain review texts) | local only, gitignored |
| Secret key (`.env`) | local only, gitignored and never committed; rotated on 2026-11-02; `.env.example` holds a placeholder |
| Labeled, analysis and top-reviews CSVs | published: review text, rating, date, app version and developer reply; no author, pseudonymised id |
| `topic_keywords.csv`, `validation_summary.csv` | published: keywords and agreement numbers only, no review text |
| Charts | published (aggregates only) |

**Pseudonymization.**
- `review_id` becomes `HMAC-SHA256(PSEUDO_KEY, review_id)`, truncated to 12 hex characters. Without the key, an
  original id cannot be mapped to its pseudonym, so published rows cannot be joined back to store records.
- Author names are dropped in 02 and never reach a later file.
- Ticket-like codes in the text are masked.

**Key rotation (2026-11-02).** A new key was generated with `secrets.token_hex(32)` and stored only in the local
`.env`. It is not in the repository, in any notebook output or in any document. The pipeline was rerun, so every
published `review_id` comes from the new key. Ids published before the rotation cannot be linked to the new ones.

**Notebook outputs.** The notebooks print only counts, aggregates, keywords and, in 02, a preview of non-text
columns. A scan of all saved outputs after the 2026-11-04 rerun found no key, review or reply text (also as
tokens), author name or local path. The same scan of 08, on 2026-11-05 and again on 2026-11-12 after part 3 was
added, found none either, and so did a scan of 07 and 08 after the labels were renamed on 2026-11-12.

---

## 14. Future work

- A second coder for the blind sample of 08 (§10), to measure the agreement between two people and not only between
  the labels and their author.
- **Sentiment analysis of the text**, to check the ratings and find the reviews where text and rating disagree.
- **Aspect-based sentiment analysis**, to capture several issues and opinions within one review instead of one
  topic per review.
- **Analysis of the developer replies**: their content, response time, and effect on later ratings.

---

## 15. Data dictionary

The five published CSVs in `data/processed/`: three review files and `topic_keywords.csv` written by 07,
`validation_summary.csv` written by 08, all with `encoding="utf-8-sig"` and `index=False`.
Types are as read by `pandas.read_csv`. "Empty" means an empty cell, read as `NaN`. Columns that hold review or
reply text, or text derived from it, have no example values.

### `trenord_reviews_labeled.csv`

All Italian reviews: 6,951 rows, 21 columns, one row per review.

| Column | Type | Description | Example values |
|---|---|---|---|
| `review_id` | string | Pseudonymised review id: HMAC-SHA256 of the store id with `PSEUDO_KEY`, first 12 hex characters (§4). Unique. Changes if the key changes. | `e0441c09f9ba`, `525ab22d4722` |
| `rating` | int | Star rating, 1-5. | `1`, `4`, `5` |
| `text` | string | Review text as published on the store, with ticket-like codes masked (§4). | - |
| `thumbs_up` | int | Number of users who marked the review as helpful, 0-87. | `0`, `1`, `51` |
| `app_version` | string | App version the review was written with. Empty when the store does not report it (496 rows). | `4.12.0`, `4.16.7`, `5.0.7` |
| `date` | string | Review date and time, `YYYY-MM-DD HH:MM:SS`, from 2015-05-05 to 2026-08-04. | `2026-08-03 17:29:22` |
| `has_reply` | bool | Whether the developer replied. | `True`, `False` |
| `reply_text` | string | Developer reply. Empty when `has_reply` is `False` (4,095 rows). | - |
| `reply_date` | string | Reply date and time, `YYYY-MM-DD HH:MM:SS`. Empty when `has_reply` is `False`. | `2015-06-20 13:15:12`, `2026-07-20 11:04:11` |
| `year` | int | Year of `date`, 2015-2026. | `2015`, `2025`, `2026` |
| `month` | int | Month of `date`, 1-12. | `1`, `8`, `12` |
| `day_of_week` | string | Weekday of `date`, in English. | `Monday`, `Sunday` |
| `year_month` | string | `YYYY-MM` of `date`. | `2015-05`, `2026-08` |
| `language` | string | Language detected by lingua (§5). Always `it` in this file. | `it` |
| `text_clean` | string | Lowercased text without URLs, symbols and extra spaces (§5). Input to BERTopic (§8). | - |
| `word_count` | int | Number of words in the original `text`, 1-278. | `17`, `45`, `63` |
| `text_lemmatized` | string | Lemmas without stopwords (§5). Not read by the dashboard. Empty when no token survives (49 rows). | - |
| `topic` | int | Topic id of the 06 BERTopic model, 0-29 (§8). | `0`, `2`, `22` |
| `topic_label` | string | One of the 12 topic labels, or `EXCLUDE` for topics without specific content (§9). | `Ticket Purchase Failures`, `Ease of Use`, `EXCLUDE` |
| `category` | string | Category of the label: `App Issue`, `Praise`, `Rail Service` or `App Updates` (§9). Empty for `EXCLUDE` rows (953 rows). | `App Issue`, `Praise`, `Rail Service` |
| `topic_merged` | int | Topic id after the merges in 07, 0-20, renumbered by size. Not stable across retrainings; use `topic_label`. | `0`, `1`, `12` |

### `trenord_reviews_analysis.csv`

The informative reviews: `trenord_reviews_labeled.csv` without the `EXCLUDE` rows. 5,998 rows, the same 21 columns.
This is the main file of the dashboard.

| Column | Type | Description | Example values |
|---|---|---|---|
| `review_id` | string | Pseudonymised review id, 12 hex characters. Unique. | `e0441c09f9ba`, `525ab22d4722` |
| `rating` | int | Star rating, 1-5. | `1`, `4`, `5` |
| `text` | string | Review text, with ticket-like codes masked. | - |
| `thumbs_up` | int | Number of users who marked the review as helpful, 0-87. | `0`, `1`, `51` |
| `app_version` | string | App version. Empty when not reported (406 rows). | `4.16.7`, `5.0.6`, `5.0.7` |
| `date` | string | Review date and time, `YYYY-MM-DD HH:MM:SS`, from 2015-05-05 to 2026-08-04. | `2026-08-03 17:29:22` |
| `has_reply` | bool | Whether the developer replied (2,396 rows `True`). | `True`, `False` |
| `reply_text` | string | Developer reply. Empty when `has_reply` is `False` (3,602 rows). | - |
| `reply_date` | string | Reply date and time. Empty when `has_reply` is `False`. | `2015-06-20 13:15:12`, `2026-07-20 11:04:11` |
| `year` | int | Year of `date`, 2015-2026. | `2015`, `2025`, `2026` |
| `month` | int | Month of `date`, 1-12. | `1`, `8`, `12` |
| `day_of_week` | string | Weekday of `date`, in English. | `Monday`, `Sunday` |
| `year_month` | string | `YYYY-MM` of `date`. | `2015-05`, `2026-08` |
| `language` | string | Detected language. Always `it`. | `it` |
| `text_clean` | string | Lowercased, cleaned text. | - |
| `word_count` | int | Number of words in the original `text`, 1-278. | `17`, `45`, `63` |
| `text_lemmatized` | string | Lemmas without stopwords. Empty when no token survives (9 rows). | - |
| `topic` | int | Topic id of the 06 model; the 21 ids kept by the label map (§9). | `0`, `2`, `22` |
| `topic_label` | string | One of the 12 topic labels; never `EXCLUDE`. | `Inaccurate Train Info`, `Subscription & Payment Failures` |
| `category` | string | `App Issue`, `Praise`, `Rail Service` or `App Updates`. Never empty. | `App Issue`, `Praise`, `App Updates` |
| `topic_merged` | int | Post-merge topic id; 12 distinct values in 0-17, one per label. | `0`, `1`, `12` |

### `top_reviews_per_topic.csv`

The 5 most upvoted reviews with at least one upvote for each of the 12 topics, shown in the topic explorer of the
dashboard: 60 rows, 6 columns.

| Column | Type | Description | Example values |
|---|---|---|---|
| `topic_label` | string | Topic label, 5 rows each. | `App Not Working`, `Login & Account Issues` |
| `category` | string | Category of the topic: `App Issue` (40 rows), `Praise` (10), `Rail Service` (5) or `App Updates` (5). | `App Issue`, `Praise` |
| `rating` | int | Star rating, 1-5. | `1`, `3`, `5` |
| `thumbs_up` | int | Helpful votes, 1-87; the ranking key within each topic. | `23`, `53`, `64` |
| `date` | string | Review date and time, `YYYY-MM-DD HH:MM:SS`. | `2021-09-15 06:12:06`, `2023-07-02 17:12:43` |
| `text` | string | Review text, with ticket-like codes masked. | - |

### `topic_keywords.csv`

The top 5 keywords of each of the 12 topics, from the merged model of 07: 60 rows, 3 columns. Read by the topic
explorer of the dashboard.

| Column | Type | Description | Example values |
|---|---|---|---|
| `topic_label` | string | Topic label, 5 rows each, largest topic first. | `Inaccurate Train Info`, `Station Issues` |
| `rank` | int | Position of the keyword in its topic, 1-5; 1 is the most typical. | `1`, `5` |
| `keyword` | string | One word or a bigram, in Italian, letters only. | `treni`, `acquistare biglietti`, `login` |

### `validation_summary.csv`

The agreement between my blind coding and the model labels (§10): 3 rows, 5 columns. The dashboard reads the
weighted agreement and the sample size, for "About this analysis".

| Column | Type | Description | Example values |
|---|---|---|---|
| `measure` | string | `raw_agreement`, `cohens_kappa` or `weighted_agreement`. | `cohens_kappa` |
| `value` | float | The measure; the two agreements are shares between 0 and 1. | `0.826530612244898`, `0.8121546961325967` |
| `ci_low` | float | Lower end of the 95% bootstrap interval. | `0.7627118644067796` |
| `ci_high` | float | Upper end of the 95% bootstrap interval. | `0.8616053776196125` |
| `sample_size` | int | Reviews in the coded sample. | `196` |
