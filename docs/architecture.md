# How this project works

This page explains the steps, the main choices and the checks. The code and the outputs are in the notebooks.

## Steps

| Notebook | What it does |
|---|---|
| 01 scraping | Downloads the Google Play reviews of the app with google-play-scraper, newest first. |
| 02 anonymization | Drops author names, replaces review ids with a keyed hash (HMAC-SHA256) and masks ticket-like codes. |
| 03 cleaning | Detects the language of each review (lingua), cleans and lemmatizes the text (spaCy). |
| 04 exploratory analysis | Ratings, reviews per year and developer replies. |
| 05 model selection | Compares BERTopic settings. Nothing is saved. |
| 06 topic model training | Trains the final model. |
| 07 topic labeling | Names the topics, merges them into 12 and saves the files for the dashboard. |
| 08 label validation | Checks the labels against my blind coding and across random seeds. |

## Data

I collected 7,329 reviews, every written review the scraper could reach. 6,951 are in Italian and are the ones analysed; 363 have no clear language and 15 are in other languages. The store showed 16,787 ratings, but that count also includes star-only ratings without text.

## Topic model

BERTopic with paraphrase-multilingual-mpnet-base-v2 embeddings, UMAP and HDBSCAN. I picked min_cluster_size 30 and min_df 5 after comparing settings on coherence (c_v), diversity and the size of the largest topic. The model has 30 topics, coherence 0.419 and diversity 0.783. HDBSCAN left 23.0% of the reviews as outliers, and I assigned them to the closest topic.

I also tried two other embedding models, other min_samples values and other keyword methods. None was clearly better, so the settings stayed.

## Labels

I read each of the 30 topics with its keywords and example reviews, named it, and merged the topics about the same theme. That left 12 topics in four categories: App Issue, Praise, Rail Service and App Updates.

The other 9 topics (953 reviews, 13.7%) only hold generic verdicts like "ottima" or "pessima" and are left out. They are more positive than the rest (3.66 stars against 1.93), so the analysed reviews are more negative than all Italian reviews.

## Checks

- Blind coding: I labelled a stratified sample of 196 reviews (14 per label) without seeing the model's label. Cohen's kappa is 0.812 (95% CI 0.763 to 0.862). Weighted to all reviews, the agreement is 86.6% (95% CI 81.7% to 91.2%). The weakest label is App Not Working: 6 of its 14 sampled reviews only say that the app does not work.
- Random seeds: I retrained the model with 4 other UMAP seeds. With three of them, 93.6% to 94.6% of the reviews keep their label. With the fourth, 79.1% do, because it merges the subscription and login reviews into ticket purchases.
- Average ratings come with 95% confidence intervals (t distribution).

## Dashboard

One Streamlit page that reads the published CSVs and computes every number itself. The tests in tests/ run on every push.

## Reproducibility

requirements-notebooks.lock.txt pins the full environment; with it, 06 gives exactly the same topics. The raw and intermediate files are not published, so the pipeline can only be rerun from a new scrape, which will return different reviews. A different pseudonymization key changes the review ids but not the results.

## Privacy

Author names are dropped, review ids are pseudonymized with a secret key kept out of the repository, and ticket-like codes are masked. The published files contain review texts without authors. The notebooks never print review texts.

## Limits

- Google Play only.
- Unhappy users write more, so the shares describe reviewers, not all users.
- Star ratings are ordinal; I used averages anyway, as is common.
- The manual check was done by one person, me.
- The generic reviews left out are more positive than the rest.
- The topics depend partly on the UMAP seed.
