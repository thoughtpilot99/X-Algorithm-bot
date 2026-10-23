# Methodology and data dictionary

## Units of analysis

| Term | Definition |
|---|---|
| Authored post | An original post or a quote post written by the account |
| Reply to others | A reply whose parent author is someone else |
| Self-reply (thread) | A reply in the account's own thread. Identified when there is no leading @mention, or when tweet-detail confirms it |
| Fulfilment reply | Template replies such as "Sent", "Here you go: <link>" or "Appreciate the comment: <link>" that deliver a lead magnet to people who commented a keyword. Detected by a fixed regular expression (`analysis/features.py::FULFILMENT`) and analysed separately from commenting |
| Conversational comment | Any reply to others that is not a fulfilment reply. This is the commenting strategy that gets audited |
| Mature post | A post at least 72 hours old when observed. Younger posts are shown in the dashboard but left out of baselines |
| Views | X's public view count as stored by the console. Used as a proxy for impressions |
| Baseline | For each authored post, the median views of the account's previous authored posts in the trailing 28 days. Requires at least 5 earlier posts |
| vs baseline | The post's views divided by its baseline |

## Statistics

**Summaries.** Medians, quantiles and MAD (median absolute deviation) are used throughout. In Nicolas's case the top 5% of posts account for about 96% of views, so means are reported but never used for conclusions.

**Segment tests.** Each level of a feature is compared with all other authored posts using:
- the ratio of medians, with a 90% percentile bootstrap confidence interval (2,000 resamples);
- a Mann–Whitney p-value;
- a Benjamini–Hochberg q-value computed across all comparisons.

Levels with fewer than 8 posts are reported as untested. A result is called a "signal" only when q < 0.1.

**Multivariable model.** OLS on log(1 + views) with these terms:
- format and topic;
- link presence in non-article posts, list formatting, use of data, personal experience, promotion and keyword CTA;
- log word count;
- month fixed effects.

Standard errors use HC3. Hook type is left out because it is collinear with the article format.

**Trend.** The Theil–Sen slope of log views against time, reported as a multiplier per 30 days with a 90% confidence interval.

**Power.** Posts needed per arm for a two-sided test at α = 0.05 with 80% power on log views, using the model's residual standard deviation.

- At current posting rates, a 1.3× effect takes many months to detect.
- So 30-day experiments are labelled *directional* unless the effect is roughly 2× or larger.

**Confounding.**
- Formats differ in topic and promotion effort, so format effects are shown both raw and in the model.
- Most X Article posts are a bare t.co link, so the link-penalty test is run only on non-article posts.
- Media and external links both appear as t.co URLs and cannot be told apart in this data.

## Commenting Effectiveness Score (internal diagnostic)

This score is 0–100 per conversational comment. It is **not** an X algorithm score. Component weights are set in `backend/src/xaudit/config/accounts.yaml`.

| Component | Default weight | Scored as |
|---|---|---|
| Relevance | 0.25 | The comment's subject matters to the client's buyers (label) |
| Originality | 0.25 | Category is substantive: insight, expertise, question, disagreement or experience |
| Observed engagement | 0.20 | Comment views ÷ the account's median comment views, capped at 3, then divided by 3 |
| Conversation | 0.15 | The comment received at least one public reply |
| Timing | 0.15 | Unavailable for most comments (no parent timestamp), so its weight is redistributed |

## Diagnostics

**Format.** Each diagnostic records:
- observation and evidence (posts, metrics, comparisons);
- algorithm links (finding IDs) and the algorithm connection;
- alternative explanations;
- confidence and impact;
- recommendation, validation and success criteria;
- evidence class;
- ranking inputs.

**Root-cause priority** combines these inputs:

| Input | Weight |
|---|---|
| Evidence strength | 0.30 |
| Likely impact | 0.25 |
| Business relevance | 0.20 |
| Confidence | 0.15 |
| Ease of testing | 0.10 |

Only diagnostics the data supports, fully or in part, are ranked.

## Data availability (first audit, 2026-10-23)

| Data | Status |
|---|---|
| Posts, replies, quotes, reposts and public metrics (180 days) | Available |
| Metric scrape time | Not recorded by the store; stamped at import. Stored values were refreshed, not frozen, when compared with an August scrape |
| Follower count | Single snapshot. No history |
| Profile bio and account creation date | Not returned |
| Media type | Unavailable |
| Private analytics (profile visits, follows, link clicks, audience) | Unavailable. This audit uses public data only |
| Reply parent post | Collected for a sample of the 40 most recent conversational comments per account. Elsewhere the parent author is inferred from the leading @mention |
| Replies and quotes by others mentioning the account | From the console store, since 2026-07-25 |
| Likes and reposts by others | Not exposed |
| Peers | Newest ≤ 100 original posts in 90 days, follower snapshot. Replies not collected |
