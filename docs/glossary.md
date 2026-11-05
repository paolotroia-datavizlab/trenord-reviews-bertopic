# Glossary - Trenord App Reviews: Topic Modeling with BERTopic

Technical terms used in [architecture.md](architecture.md), in alphabetical order.

## BERTopic
A topic modeling library that groups documents by meaning rather than by shared words. It chains an embedding
model, dimensionality reduction (UMAP), clustering (HDBSCAN) and keyword extraction (c-TF-IDF).
In this project it groups the Italian reviews into 30 topics (notebook 06).

## Bigram
A sequence of two adjacent words treated as one term, such as "acquistare biglietti". Single words are unigrams;
both are n-grams.
Here topic keywords may be single words or bigrams.

## BOM (byte-order mark)
An invisible marker at the start of a text file that declares its encoding.
The CSV files are saved as `utf-8-sig`, which adds a BOM so that spreadsheet programs read accented characters correctly.

## c-TF-IDF
Class-based TF-IDF: a score for how characteristic a word is of one topic compared with all the others.
It treats all the documents of a topic as a single document.
BERTopic uses it to find each topic's keywords.

## Category
The group a topic label belongs to. This project uses four categories of its own:
- App Issue: something in the app does not work, works badly or stopped working;
- Praise: what users like about the app;
- Rail Service: complaints about the trains and the company, not about the app;
- App Updates: reviews that compare the app with its earlier versions.

Notebook 07 assigns them by hand. No topic is made mostly of requests for new features, so there is no category
for them.

## Confidence interval
A range around an average that shows how precise the average is. A 95% interval is built so that, over many
samples, 95% of the intervals computed this way would contain the true average. It is the average plus or minus a
margin: the [standard error](#standard-error) times a value from the [t distribution](#t-distribution).
In 07 every final topic has a 95% interval for its average rating. Small topics have wide intervals.

## Continuation token
A bookmark returned by a paginated interface that tells the next request where the previous page ended.
The scraper passes it back on every request to download the reviews page by page.

## Cosine similarity
A measure of how similar two vectors are, based on the angle between them, from −1 (opposite) to 1 (identical
direction).
UMAP compares review embeddings with it, and outlier reduction uses it to find each outlier's closest topic.

## CountVectorizer
A scikit-learn tool that turns texts into word counts, with options to drop stopwords and rare words
([min_df](#min_df)) and to count n-grams.
BERTopic uses it to build the vocabulary from which topic keywords are chosen.

## Embedding
A list of numbers (a vector) that represents the meaning of a text, so that texts with similar meaning have
nearby vectors.
Every Italian review is turned into an embedding before clustering.

## Exclusion bias
A distortion that arises when the data removed from an analysis differs systematically from the data kept.
Here the excluded reviews are short verdicts, mostly with 5 or 1 star, and on average more positive than the
analysed ones, so the analysis set is more negative than all reviews; notebook 07 measures this.

## HDBSCAN
A clustering algorithm that finds groups of points in dense regions and leaves isolated points unassigned as
outliers. It finds the number of clusters from the data and accepts groups of any shape. K-Means, a common
alternative, needs the number of clusters fixed in advance and puts every point in a group.
It forms the topics from the reduced review embeddings. Its `min_cluster_size` is the smallest group it accepts as
a topic. Its `min_samples` sets how strict it is about dense areas. It is not set here, so the library uses
`min_cluster_size` and the effective value is 30.

## HMAC
Hash-based message authentication code: a one-way fingerprint of a value computed with a
[secret key](#secret-key). The same value and key always give the same code. Without the key, nobody can
recompute the code from the value or reverse it.
It replaces the original review ids (HMAC-SHA256, truncated to 12 hexadecimal characters).

## Identifying keywords
Two keywords written next to each topic in the 07 label map, chosen by hand among its top 10 keywords. Notebook 07
checks that both are still among the top 10 keywords of that topic. If one is missing, the model has changed since
the labels were written and the notebook stops.

## Language detection confidence
The probability, between 0 and 1, that a language detector assigns to its best guess for a text.
Notebook 03 accepts Italian at any confidence and other languages only at 0.5 or above.

## Lemmatization
Reducing each word to its dictionary form, for example a conjugated verb to its infinitive.
It groups word variants in the frequency analyses of the dashboard.

## Lock file
A list of every installed package with its exact version, including the indirect dependencies that a
requirements file does not pin, so that the same environment can be rebuilt.
`requirements-notebooks.lock.txt` is the `pip freeze` of the project environment. In it, retraining 06 reproduces
the current topic model exactly.

## min_df
A CountVectorizer option: a term is kept only if it appears in at least this many documents.
BERTopic fits the vectorizer on one joined text per topic, so in BERTopic `min_df` counts topics, not reviews. It
changes only the keywords, not which reviews belong to which topic. Here `min_df=5`; notebook 05 compares it with
1 and 2.

## MMR (Maximal Marginal Relevance)
A method that selects keywords that are relevant to a topic but not redundant with each other. A diversity
parameter balances relevance against variety.
It refines the keywords of every topic.

## Normalized frequency ratio
The rate of a word per negative review divided by its rate per positive review, with a small constant to
avoid division by zero.
The dashboard uses it to rank the "critical words" of negative reviews.

## Okabe-Ito palette
A set of eight colours designed by Masataka Okabe and Kei Ito to stay distinct for people with colour vision
deficiency. The notebooks and the dashboard use its vermillion, bluish green, reddish purple and blue for the four
[categories](#category), and a scale from vermillion to green for the star ratings.

## Outlier
A document that the clustering step does not assign to any topic. BERTopic gives it the topic id −1.
Training produced outliers, which were then reassigned.

## Outlier reduction
Assigning outliers to an existing topic after training, here to the topic whose centre is most similar to the
outlier's embedding.
All outliers were reassigned, so every Italian review has a topic.

## Pseudonymization
Replacing direct identifiers with artificial values, so that records cannot be linked to a person without extra
information kept separately.
Here the review ids are replaced by keyed hashes and the author names are removed.

## Random seed
A fixed starting value for a random process, which makes its result repeatable.
UMAP uses `random_state=42`. This makes training repeatable only in the same software environment, which is why
the environment is recorded in a [lock file](#lock-file).

## Safetensors
A file format for storing model weights safely, without the code-execution risks of pickle files.
Both BERTopic models are saved in this format. BERTopic then keeps the topics, keywords, topic vectors, c-TF-IDF
counts and settings, but not the UMAP and HDBSCAN models, the MMR representation model or the embedding model
weights, which are reloaded by name.

## Secret key
A random value known only to its owner, used to compute codes that others cannot recompute.
`PSEUDO_KEY` is the HMAC key of the pseudonymization. It is generated with
`python -c "import secrets; print(secrets.token_hex(32))"` and stored only in the gitignored `.env`. Changing it
changes every `review_id`.

## Sentence transformer
A neural network that turns a whole sentence or paragraph into a single embedding.
The multilingual model `paraphrase-multilingual-mpnet-base-v2` produces the review embeddings.

## Smoke test
A quick test that runs a program end to end to check that nothing breaks, without verifying every result in
detail.
The dashboard is smoke-tested in 18 filter scenarios with Streamlit's AppTest.

## Sparkline
A very small line or bar chart without axes, shown next to a number to indicate its trend.
The dashboard's metric cards show yearly sparklines.

## Standard error
How much an average would change from one sample to another. It is the standard deviation of the values divided by
the square root of their number, so it gets smaller as the sample grows.
Notebook 07 uses it to build the [confidence interval](#confidence-interval) of each topic's average rating.

## Stopwords
Very common words with little meaning on their own, such as articles and prepositions, that are usually removed
before counting words.
The spaCy Italian stopword list is removed in lemmatization, topic keywords and the dashboard word analysis.

## t distribution
A probability distribution similar to the normal one but with heavier tails, used when the spread of the
population is estimated from the sample itself. Its shape depends on the degrees of freedom, here the number of
reviews minus one; with many reviews it is almost identical to the normal distribution.
Notebook 07 takes from it the multiplier of the 95% [confidence interval](#confidence-interval), `t.ppf(0.975, n - 1)`.

## Topic coherence
A score for how often the top keywords of a topic appear together in the same documents. Higher values usually
mean keywords that belong together. The c_v variant, computed with gensim, usually falls between 0 and 1.
Notebook 05 uses it to compare settings. It is a proxy: it also rewards near-synonyms and generic words, so it
does not replace reading the topics.

## Topic diversity
The share of distinct words among the top keywords of all topics: 1.0 means no word is shared between two topics.
Notebook 05 uses it to compare settings. Variants of the same word count as different strings, so a high value
is not always better.

## Topic merge
Combining two or more topics into one; the model then recomputes the keywords of the merged topic.
In 07, topics that share a label are merged with `merge_topics()`. The merge changes only the model, which
renumbers its topics by size; the new numbers are copied to the `topic_merged` column.

## Topic representation
The description of a topic, usually its top keywords with their scores.
The representations are recomputed after outlier reduction and after merging.

## UMAP
Uniform Manifold Approximation and Projection: a method that compresses high-dimensional vectors into a few
dimensions while keeping similar items close together.
It reduces the review embeddings to 5 dimensions before clustering.
