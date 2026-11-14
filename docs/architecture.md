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
| 09 feature requests | Finds the reviews that ask for something new with rules, a classifier and an LLM, checks them against my own labels and groups them into themes. |

## Data

I collected 7,329 reviews, every written review the scraper could reach. 6,951 are in Italian and are the ones analysed; 363 have no clear language and 15 are in other languages. The store showed 16,787 ratings, but that count also includes star-only ratings without text.

## Topic model

BERTopic with paraphrase-multilingual-mpnet-base-v2 embeddings, UMAP and HDBSCAN. I picked min_cluster_size 30 and min_df 5 after comparing settings on coherence (c_v), diversity and the size of the largest topic. The model has 30 topics, coherence 0.419 and diversity 0.783. HDBSCAN left 23.0% of the reviews as outliers, and I assigned them to the closest topic.

I also tried two other embedding models, other min_samples values and other keyword methods. None was clearly better, so the settings stayed.

## Labels

I read each of the 30 topics with its keywords and example reviews, named it, and merged the topics about the same theme. That left 12 topics in four categories: App Issue, Praise, Rail Service and App Updates.

The other 9 topics (953 reviews, 13.7%) only hold generic verdicts like "ottima" or "pessima" and are left out. They are more positive than the rest (3.66 stars against 1.93), so the analysed reviews are more negative than all Italian reviews.

## Recent years

Notebook 07 compares the last two complete years, 2024-2025, with the whole period. The same three problems lead: Inaccurate Train Info, Ticket Purchase Failures and App Not Working. Stability and usability problems (App Not Working, Poor Usability, Login & Account Issues and Station Issues) grew from 28.1% to 36.6% of the topic reviews, while praise (Ease of Use and Easy Purchases) fell from 12.3% to 3.5%.

## Checks

- Blind coding: I labelled a stratified sample of 196 reviews (14 per label) without seeing the model's label. Cohen's kappa is 0.812 (95% CI 0.763 to 0.862). Weighted to all reviews, the agreement is 86.6% (95% CI 81.7% to 91.2%). The weakest label is App Not Working: 6 of its 14 sampled reviews only say that the app does not work.
- Random seeds: I retrained the model with 4 other UMAP seeds. With three of them, 93.6% to 94.6% of the reviews keep their label. With the fourth, 79.1% do, because it merges the subscription and login reviews into ticket purchases.
- Average ratings come with 95% confidence intervals (t distribution).

## Feature requests

Notebook 09 looks for the reviews that ask for a feature or a change the app does not offer. I wrote 20 rules (regular expressions) and drew a sample of 400 reviews: 200 that match the rules and 200 that do not. I coded the sample twice. The first time I followed the wording of the rules too closely, so I coded all 400 again, blind to the rules and to the other methods, and the results use the second coding. The estimates weight each half of the sample by the size of its group.

I compared three methods on the sample: the rules, a classifier on the review embeddings trained with the sample weights, and an LLM, openai/gpt-5.4-mini-20260317 through OpenRouter, zero-shot. The LLM has the highest recall, 0.808 (95% CI 0.614 to 0.994), against 0.253 for the rules and 0.274 for the classifier. The F1 intervals overlap (rules 0.324, classifier 0.302, LLM 0.502), so no method is clearly best on F1. I used the LLM for all reviews because it misses the fewest requests.

The LLM flagged 1,279 reviews (18.4%) and put each one in one of 13 themes that I reviewed. Its precision is only 0.364 (95% CI 0.236 to 0.522): it also flags many reports of broken features. So I measured the precision of each theme on my sample and multiplied the flagged reviews of the theme by it. About 7.7% of the reviews are requests (95% CI 4.7% to 11.1%). The clearest themes are train information (precision 0.965, about 107 real requests, 95% CI 81 to 111) and notifications (precision 0.904, about 66, 95% CI 29 to 73). The dashboard shows one example review per theme, chosen with a fixed rule: among the sample reviews I coded as requests in that theme, the one with the most thumbs up among those of at most 300 characters (ties: the shortest), skipping any review that could identify someone.

## Dashboard

One Streamlit page that reads the published CSVs and computes every number itself. The tests in tests/ run on every push.

## Reproducibility

requirements-notebooks.lock.txt pins the full environment; with it, 06 gives exactly the same topics. The raw and intermediate files are not published, so the pipeline can only be rerun from a new scrape, which will return different reviews. A different pseudonymization key changes the review ids but not the results. Notebook 09 needs an OpenRouter key in .env. My labels and the saved LLM answers stay in labeling/, which is not published, so 09 cannot be rerun from the repository alone.

## Privacy

Author names are dropped, review ids are pseudonymized with a secret key kept out of the repository, and ticket-like codes are masked. The published files contain review texts without authors. The notebooks never print review texts. Review texts, without authors, were sent to the LLM through OpenRouter.

## Limits

- Google Play only.
- Unhappy users write more, so the shares describe reviewers, not all users.
- Star ratings are ordinal; I used averages anyway, as is common.
- The manual check was done by one person, me.
- The generic reviews left out are more positive than the rest.
- The topics depend partly on the UMAP seed.
- The LLM flags many reports of broken features as requests; the counts per theme are corrected with a small checked sample, so most intervals are wide.
- The LLM does not accept a fixed temperature: its answers are saved, but a new run could give slightly different ones.
