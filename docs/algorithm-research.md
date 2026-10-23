# X algorithm research — what the published repository says

Studied commit: [`07d159b`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/README.md) · local HEAD `07d159b` (2026-10-23) · 78 findings · 23 claims checked · citation check: 122/122 anchors verified.

Every finding records: the mechanism, repository path and line range, symbol, commit, a plain-English explanation, potential relevance to an account, verification status, and limitations. Citations are machine-checked (`xaudit verify-citations`): the anchor text must appear within the cited lines.

> The public repository is not a complete representation of live production systems. Ranking weights multiply *predicted* per-viewer action probabilities, not raw counts.

## Knowledge gaps

- Trained model weights for Phoenix retrieval/ranking are not published, so per-post predicted probabilities cannot be reproduced.
- Grox prompts and some botmaker rules are deliberately withheld; classifier thresholds (e.g. BDSM) are redacted.
- The `component_library` crate (maps model outputs to named scores, holds the retrieval client and quality_factor) is not in the repository.
- Published parameter values are defaults mirrored from feature switches; live experiments can override them. home-mixer and vm-ranker declare the same keys with different defaults.
- Per-account outputs (user-cred score, Agatha labels, visibility labels, safety labels) are not observable from public data, so no audit can confirm or rule out an account-level label.
- Only engagement on posts served in Home Timeline feeds ranking (per the repository's own note); public counts mix all surfaces.

## Published ranking weights (home-mixer defaults at studied commit)

| Parameter | Value | Source |
|---|---:|---|
| FavoriteWeight | 0.66 | [home-mixer/params/param.rs:345](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L345) |
| ReplyWeight | 5.0 | [home-mixer/params/param.rs:346](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L346) |
| RetweetWeight | 1.0 | [home-mixer/params/param.rs:359](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L359) |
| PhotoExpandWeight | 0.05 | [home-mixer/params/param.rs:360](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L360) |
| VideoOpenWeight | 0.02 | [home-mixer/params/param.rs:366](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L366) |
| ClickWeight | 0.3 | [home-mixer/params/param.rs:372](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L372) |
| OpenLinkWeight | 0.2 | [home-mixer/params/param.rs:373](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L373) |
| ProfileClickWeight | 0.0 | [home-mixer/params/param.rs:374](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L374) |
| VqvWeight | 0.0 | [home-mixer/params/param.rs:380](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L380) |
| ShareWeight | 2.0 | [home-mixer/params/param.rs:381](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L381) |
| ShareViaDmWeight | 5.0 | [home-mixer/params/param.rs:382](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L382) |
| ShareViaCopyLinkWeight | 20.0 | [home-mixer/params/param.rs:388](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L388) |
| DwellWeight | 0.05 | [home-mixer/params/param.rs:394](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L394) |
| QuoteWeight | 5.0 | [home-mixer/params/param.rs:395](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L395) |
| QuotedClickWeight | 0.05 | [home-mixer/params/param.rs:396](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L396) |
| QuotedVqvWeight | 0.0 | [home-mixer/params/param.rs:402](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L402) |
| FollowAuthorWeight | 4.0 | [home-mixer/params/param.rs:408](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L408) |
| PostUnexploredWeight | 0.015 | [home-mixer/params/param.rs:414](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L414) |
| ReactWithVideoWeight | 0.0 | [home-mixer/params/param.rs:420](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L420) |
| ContDwellTimeWeight | 0.006 | [home-mixer/params/param.rs:426](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L426) |
| ContClickDwellTimeWeight | 0.4 | [home-mixer/params/param.rs:432](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L432) |
| NotInterestedWeight | -52.272 | [home-mixer/params/param.rs:439](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L439) |
| BlockAuthorWeight | -31.2 | [home-mixer/params/param.rs:445](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L445) |
| MuteAuthorWeight | -58.8 | [home-mixer/params/param.rs:451](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L451) |
| ReportWeight | -234.0 | [home-mixer/params/param.rs:457](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L457) |
| NotDwelledWeight | -0.02 | [home-mixer/params/param.rs:458](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L458) |
| VideoCarouselVideoOpenWeight | 1.0 | [home-mixer/params/param.rs:1182](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L1182) |
| VideoCarouselImmersiveVqvWeight | 0.0 | [home-mixer/params/param.rs:1188](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L1188) |

### Parameter changes in the last commits scanned

| Date | Commit | File | Parameter | From | To |
|---|---|---|---|---|---|
| 2026-08-25 | 0d3cdd8 | home-mixer/params/param.rs | ColdStartTsTopK | 5 | 2 |
| 2026-08-25 | 0d3cdd8 | home-mixer/params/param.rs | DwellWeight | 0.0 | 0.05 |
| 2026-08-25 | 0d3cdd8 | home-mixer/params/param.rs | VideoOpenWeight | 0.05 | 0.07 |
| 2026-08-25 | 0d3cdd8 | home-mixer/params/param.rs | VqvWeight | 0.05 | 0.0 |
| 2026-09-17 | 42266f3 | home-mixer/params/param.rs | ColdStartMaxPostAgeSecs | 86400 | 172800 |
| 2026-09-23 | 1b3fec2 | home-mixer/params/param.rs | PhoenixMoeColdStartMaxResults | 0 | 200 |
| 2026-09-29 | a707cc2 | home-mixer/params/param.rs | ClickWeight | 0.4 | 0.3 |
| 2026-09-29 | a707cc2 | home-mixer/params/param.rs | ContClickDwellTimeWeight | 0.0 | 0.4 |
| 2026-09-29 | a707cc2 | home-mixer/params/param.rs | NotInterestedWeight | -43.2 | -47.52 |
| 2026-09-29 | a707cc2 | vm-ranker/params.rs | ClickWeight | 0.4 | 0.3 |
| 2026-09-29 | a707cc2 | vm-ranker/params.rs | ContClickDwellTimeWeight | 0.0 | 0.4 |
| 2026-09-29 | a707cc2 | vm-ranker/params.rs | NotInterestedWeight | -43.2 | -47.52 |
| 2026-09-30 | 77d431a | home-mixer/params/param.rs | ColdStartFollowerCap | 1000 | 50000 |
| 2026-09-30 | 77d431a | home-mixer/params/param.rs | ColdStartImpressionThreshold | 1000 | 200 |
| 2026-09-30 | 77d431a | home-mixer/params/param.rs | ColdStartMaxPostAgeSecs | 172800 | 7200 |
| 2026-09-30 | 77d431a | home-mixer/params/param.rs | EnableColdStartThompsonSampling | false | true |
| 2026-09-30 | 77d431a | home-mixer/params/param.rs | PhoenixColdStartMaxResults | 0 | 200 |
| 2026-10-07 | 78460ca | home-mixer/params/param.rs | PostUnexploredWeight | 0.02 | 0.015 |
| 2026-10-13 | e1a0375 | home-mixer/params/param.rs | ContDwellTimeWeight | 0.004 | 0.006 |
| 2026-10-13 | e1a0375 | home-mixer/params/param.rs | FavoriteWeight | 0.5 | 0.6 |
| 2026-10-13 | e1a0375 | home-mixer/params/param.rs | VideoOpenWeight | 0.07 | 0.02 |
| 2026-10-14 | 17c96bf | home-mixer/params/param.rs | FavoriteWeight | 0.6 | 0.66 |
| 2026-10-14 | 17c96bf | home-mixer/params/param.rs | NotInterestedWeight | -47.52 | -52.272 |

## A. Content candidate retrieval

### A01 — Follow graph is the sole input to in-network (Thunder) retrieval

- **Location:** [`home-mixer/sources/thunder_source.rs:29-43`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/thunder_source.rs#L29-L43) · symbol `ThunderSource::source` · commit `07d159b`
- **Status:** verified
- **Mechanism:** ThunderSource builds a GetInNetworkPostsRequest whose following_user_ids are the viewer's followed_user_ids (hydrated from the social graph by FollowedUserIdsQueryHydrator). Already-seen post ids are passed as exclude_tweet_ids, and max_results comes from ThunderMaxResults (default 1200 in param.rs) passed through quality_factor::apply. Posts returned are tagged ForYouInNetwork.
- **Relevance to an account:** Only viewers who follow an account can receive its posts through this path, so follower count plausibly bounds in-network candidate supply. It says nothing about non-follower discovery, which depends on the out-of-network paths (A04-A18).
- **Observable proxy:** follower count; views relative to follower count on posts
- **Limitations:** quality_factor::apply lives in the xai_candidate_pipeline component_library, which is not in this repo, so the effective max_results under load is unknown. ThunderSource is disabled when the request is served from cached posts. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### A02 — Thunder per-author caps on in-network posts

- **Location:** [`thunder/config.rs:1-7`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/thunder/config.rs#L1-L7) · symbol `MAX_ORIGINAL_POSTS_PER_AUTHOR, MAX_REPLY_POSTS_PER_AUTHOR, MAX_POSTS_TO_RETURN` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Thunder caps how many posts per followed author it returns: MAX_ORIGINAL_POSTS_PER_AUTHOR = 50 originals and MAX_REPLY_POSTS_PER_AUTHOR = 30 replies/reposts, with a global MAX_POSTS_TO_RETURN = 1200 (MAX_VIDEOS_TO_RETURN = 600 for video requests). thunder_service.rs uses these as upper bounds and allows a request to lower them via per_author_limits.
- **Relevance to an account:** Very prolific accounts could have older posts cut from a follower's in-network candidate set once the per-author cap is reached; typical posting volumes are unlikely to hit these caps.
- **Observable proxy:** post timing / posting frequency per 48h window
- **Limitations:** Constants are compiled into Thunder; whether production Thunder runs with different limits is not stated. The For You ThunderSource sends per_author_limits: None, so these defaults apply there.

### A03 — Thunder orders in-network candidates purely by recency

- **Location:** [`thunder/thunder_service.rs:307-343`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/thunder/thunder_service.rs#L307-L343) · symbol `score_recent` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Whatever algorithm string is requested, Thunder logs an error for unsupported values and calls score_recent, which sorts posts by created_at descending and truncates to max_results. There is no engagement-based ordering at this stage; ranking happens later in home-mixer.
- **Relevance to an account:** For viewers who follow many active accounts, older posts may fall outside the in-network candidate window before ranking, so posting time relative to a follower's session could plausibly matter.
- **Observable proxy:** post timing (hour/day), post age at time of views
- **Limitations:** Thunder's in-memory retention is set by post_retention_seconds (default 172800 in thunder/args.rs lines 48-49); home-mixer also applies a 48h AgeFilter. How often the 1200 cap binds in practice is not observable from code.

### A04 — Viewer's recent engagement sequence feeds Phoenix retrieval

- **Location:** [`home-mixer/query_hydrators/retrieval_sequence_query_hydrator.rs:36-61`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/query_hydrators/retrieval_sequence_query_hydrator.rs#L36-L61) · symbol `RetrievalSequenceQueryHydrator::hydrate` · commit `07d159b`
- **Status:** verified
- **Mechanism:** RetrievalSequenceQueryHydrator fetches the viewer's aggregated user-action sequence from the user action aggregation service, with length up to MaxSeqLengthRetrieval (default 1024) and aggregation type PhoenixRetrievalAggregationType (default DENSE_WITH_LONG_DWELL). That sequence is the input PhoenixSource, PhoenixMOESource and PhoenixTopicsSource send to the retrieval model.
- **Relevance to an account:** Out-of-network retrieval is driven by what each viewer engaged with, so an account's posts are plausibly more retrievable for viewers whose histories contain similar posts/authors. This is a viewer-side signal, not something an author controls directly.
- **Observable proxy:** none — not observable from public data (viewer histories are private)
- **Limitations:** The aggregation service and the exact actions included per aggregation type are not in this repo; the meaning of UAS_WINDOW_TIME_MS passed here is not documented.

### A05 — Phoenix retrieval is a two-tower model over engagement history

- **Location:** [`phoenix/README.md:99-121`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/phoenix/README.md#L99-L121) · symbol `RecsysTwoTowerModel (user_tower, candidate_tower)` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Per phoenix/README.md, the user tower encodes the viewer's engagement history (plus one user-features token) into a normalized embedding, with no learned per-user ID embedding. The candidate tower embeds posts via semantic IDs plus hashed author IDs; the index is baked into the checkpoint, and serving retrieves top-K by dot product.
- **Relevance to an account:** Main ML path by which non-followers can be shown an account's posts: posts whose content/author embeddings sit near a viewer's history embedding are more likely to be retrieved. Content similarity (semantic IDs) and author identity both enter the candidate representation.
- **Observable proxy:** views from non-followers are not public; total views vs follower count is a weak proxy
- **Limitations:** This is README prose; the code is phoenix/xrex/models/recsys_two_tower_model.py (RecsysTwoTowerModel, RecsysCandidateTower). The README also says retrieval is trained with favorites as the positive signal (phoenix/README.md lines 274-275). Production checkpoints, corpus and cluster configs are not published.

### A06 — PhoenixSource request: main and cold-start result budgets

- **Location:** [`home-mixer/sources/phoenix_source.rs:124-146`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/phoenix_source.rs#L124-L146) · symbol `PhoenixSource::source, served_type_for_dataset` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PhoenixSource calls the retrieval service with PhoenixMaxResults (default 1000) for the main budget and PhoenixColdStartMaxResults (default 200) as a separate cold-start budget, optional seen-post exclusions and retrieval value-model weights. Returned candidates get a served type per dataset: HomeCold maps to ForYouPhoenixRetrievalCold and ZeroFav to ForYouPhoenixRetrievalZeroFav (served_type_for_dataset, same file lines 199-205).
- **Relevance to an account:** A dedicated cold-start retrieval budget means low-engagement posts can plausibly be retrieved for non-followers separately from the main pool, which matters for smaller accounts.
- **Observable proxy:** early views on new posts with few likes
- **Limitations:** How the retrieval server splits/uses the cold-start budget is inside the Phoenix serving engine and the retrieval client (component_library, not in repo). RetrievalValueModelWeights defaults to an empty string. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### A07 — Cold-start retrieval pool: low-fav, low-view, fresh posts

- **Location:** [`phoenix/xrex/data/cold_pool_filter.py:16-51`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/phoenix/xrex/data/cold_pool_filter.py#L16-L51) · symbol `cold_pool_mask, DEFAULT_COLD_START_MAX_AGE_SECONDS` · commit `07d159b`
- **Status:** verified
- **Mechanism:** cold_pool_mask keeps posts whose metadata shows view_count < max_views (default 500) and fav_count < max_favs (default 8); posts missing metadata are kept. retrieval_dataset.py combines this with fresh_post_mask(cold_start_max_age_seconds) to form the HOME_COLD slice of the home index, and the complement becomes HOME_HOT (DEFAULT_COLD_START_MAX_AGE_SECONDS = 2 * 60 * 60).
- **Relevance to an account:** Young posts that have not yet accumulated many views or likes appear to be eligible for a separate cold-start retrieval slice, which could give small accounts' new posts some out-of-network exposure; eligibility appears to end once a post crosses the view/fav/age limits.
- **Observable proxy:** views and likes in the first hours after posting; post age
- **Limitations:** Defaults are function defaults in training/indexing code (phoenix/xrex); whether production serving passes other values (e.g. cold_start_max_age_seconds) is not shown. HOME_COLD is built from the 1fav_1day snapshot (retrieval_dataset.py line 280), so it presumably requires the post to be in the 1fav index (see A08).

### A08 — Phoenix retrieval index admission is triggered by favorite events

- **Location:** [`phoenix-rankall-strato/columns/phoenix_rank_all/phoenixRankAllCandidateProcessor.strato:469-530`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/phoenix-rankall-strato/columns/phoenix_rank_all/phoenixRankAllCandidateProcessor.strato#L469-L530) · symbol `executeOp, build1FavIndex, build32FavIndex, buildPostCreationIndex` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The rank-all candidate processor skips community posts and reposts, routes replies to separate reply indexes, and skips posts that visibility filtering would drop or that are adult (except an NSFW video index). For other posts, a Fav event source writes the post to the 1fav, 1fav_topic and 32fav (only if favoriteCount >= 32, lines 62-76) indexes; a PostCreation event writes a separate post-creation index.
- **Relevance to an account:** Getting at least one like plausibly matters for an original post to enter the 1fav retrieval index that HOME/HOME_COLD slices are built from; posts that VF would drop or that are labelled adult are not indexed there, which would limit non-follower discovery.
- **Observable proxy:** like count (whether a post has >= 1 like; >= 32 likes); reply vs original post type
- **Limitations:** Which index each Phoenix retrieval cluster actually queries in production is configured outside this file. eventProcessing helpers (shouldDropPostByVF, isNsfwPost) are referenced but their full logic is elsewhere. lifecycle labels differ between strato files (some say Development).

### A09 — Phoenix MoE retrieval source is off by default

- **Location:** [`home-mixer/sources/phoenix_moe_source.rs:25-35`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/phoenix_moe_source.rs#L25-L35) · symbol `PhoenixMOESource::enable` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PhoenixMOESource only runs when EnablePhoenixMOESource is true, the SID source is not enabled, the request is not in-network-only or cached, and a kill-switch decider is off. It uses a separate MoE inference cluster and tags candidates ForYouPhoenixRetrievalMoe. Defaults in param.rs are EnablePhoenixMOESource = false and PhoenixMOEMaxResults = 0.
- **Relevance to an account:** With repo defaults this path contributes no candidates, so it is unlikely to explain reach for most viewers; it may apply to experiment buckets.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Experiment overrides (feature switches) can enable it for some users; the repo does not say for whom. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### A10 — Phoenix topics source serves only single-topic requests

- **Location:** [`home-mixer/sources/phoenix_topics_source.rs:26-32`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/phoenix_topics_source.rs#L26-L32) · symbol `PhoenixTopicsSource::enable` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PhoenixTopicsSource is enabled only for topic requests that are not bulk topic requests (and not in-network-only or cached). It sends the requested topic entity ids plus a topic-filter mode to the topic retrieval cluster (PhoenixRetrievalTopicInferenceClusterId) with a cold-start budget of 0.
- **Relevance to an account:** Matters only on topic-filtered timeline requests; posts classified into a topic (via the 1fav_topic index, A08) may be discoverable by non-followers browsing that topic.
- **Observable proxy:** none — not observable from public data
- **Limitations:** How topics are assigned to posts relies on classifiers/stores outside this source file.

### A11 — SimClusters source constants (score floor, seed age, result caps)

- **Location:** [`home-mixer/sources/simclusters_source.rs:25-36`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/simclusters_source.rs#L25-L36) · symbol `POST_ANN_MIN_SCORE, MAX_SEED_AGE, MAX_RESULTS, MAX_SANN_CANDIDATES` · commit `07d159b`
- **Status:** verified
- **Mechanism:** SimclustersSource queries SimClusters ANN with cosine similarity over log-fav embeddings (MODEL_20M_145K_2020), ANN_MAX_NUM_RESULTS = 200 per seed, scanning up to 50 clusters. Results are kept only if score > POST_ANN_MIN_SCORE = 0.5, seeds must be no older than MAX_SEED_AGE (90 days), and the merged output is capped at MAX_RESULTS = 800.
- **Relevance to an account:** A second out-of-network path: posts that are cluster-similar (by who favorites them) to posts the viewer engaged with can be surfaced to non-followers. Candidate age is bounded by SimclustersMaxCandidateAgeHours (default 48).
- **Observable proxy:** likes (log-fav embeddings are favorite-based); post age
- **Limitations:** The SimClusters embeddings and ANN service are in simclusters/ (Scala) and their training data is not published. The OONNsfwSimclustersFilter later removes SimClusters posts from adult-flagged authors the viewer does not follow.

### A12 — SimClusters seeds come from the viewer's recent engagements

- **Location:** [`home-mixer/sources/simclusters_source.rs:222-252`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/simclusters_source.rs#L222-L252) · symbol `SimclustersSource::source, post_signal_ids` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Seeds are the post ids from the viewer's explicit and implicit engagement signals, sorted by engaged_at_ms (most recent first) and deduplicated; seeds older than MAX_SEED_AGE are dropped. Each seed's ANN results are filtered by POST_ANN_MIN_SCORE, limited to MAX_SANN_CANDIDATES / number_of_seeds per seed, round-robin interleaved, and truncated to 800.
- **Relevance to an account:** If viewers who engage with posts similar to an account's posts are numerous, the account's posts may be pulled in as similar candidates; engagement on an account's own posts also becomes a seed for that engager's future SimClusters retrieval.
- **Observable proxy:** likes, reposts, replies, bookmarks on posts (as seeds for engagers)
- **Limitations:** Per-type signal caps (EngagementSignalsMaxPerType, default 15) and the upstream engagement stores (twistly) are outside this file; caching (pod and shared caches, 600s pod TTL) can delay changes.

### A13 — Explicit engagement signal types used as retrieval seeds

- **Location:** [`home-mixer/query_hydrators/explicit_engagement_signals_query_hydrator.rs:68-96`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/query_hydrators/explicit_engagement_signals_query_hydrator.rs#L68-L96) · symbol `split_by_type` · commit `07d159b`
- **Status:** verified
- **Mechanism:** ExplicitEngagementSignalsQueryHydrator splits the viewer's recent engaged tweets into Favorite, Retweet, Reply, Bookmark, Share and OriginalTweet (the viewer's own posts) signals, keeping EngagementSignalsMaxPerType per type. The implicit hydrator adds PhotoExpand, VideoQualityView and ImmersiveVideoQualityView. These feed SimClusters and SID seeds via post_signal_ids.
- **Relevance to an account:** Bookmarks and shares are seed signals here even though bookmarks have no weight in the ranking value model; a viewer bookmarking a post may plausibly lead to similar posts being retrieved for that viewer later.
- **Observable proxy:** bookmarks, likes, reposts, replies (counts are public; who engaged mostly is not)
- **Limitations:** Signals are capped per type and fetched with a 300ms timeout (HYDRATE_TIMEOUT, line 16); the store's retention is unknown.

### A14 — Popular-posts list: time-decayed view quality with per-author cap

- **Location:** [`home-mixer/util/popular_posts.rs:36-86`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/util/popular_posts.rs#L36-L86) · symbol `SelectionConfig::default, quality, select_popular_posts` · commit `07d159b`
- **Status:** verified
- **Mechanism:** select_popular_posts keeps posts aged 0..window_hours, scores each with quality = views * saturation / elapsed using an exponential half-life, keeps the top per_author posts per author, then the top budget overall. SelectionConfig defaults: per_author 5, budget 500, half_life_hours 8.0, floor_hours 0.5, window_hours 24.0.
- **Relevance to an account:** Only authors in the popular-authors list (A15) feed this list, so for most accounts it is not a discovery path; for eligible authors, posts with high views relative to age rank higher.
- **Observable proxy:** views and post age (views per hour since posting)
- **Limitations:** home-mixer/main.rs exposes CLI flags for per_author, budget and half_life (defaults 5, 500, 8.0); actual job flags in production are not shown. PopularPostsSource serves up to PopularPostsMaxResults (default 500) and is shared across viewers.

### A15 — Popular authors are the top fraction of active posters by followers

- **Location:** [`home-mixer/util/popular_authors.rs:11-43`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/util/popular_authors.rs#L11-L43) · symbol `select_top_posting_authors, TOP_POSTING_AUTHORS_FRACTION` · commit `07d159b`
- **Status:** verified
- **Mechanism:** select_top_posting_authors takes authors sorted by follower count descending and keeps the top k = ceil(active_posters_7d * fraction), with TOP_POSTING_AUTHORS_FRACTION = 0.00005. The job reads the ranked list from a BigQuery table of popular posting authors and logs the minimum follower count of the selection.
- **Relevance to an account:** Eligibility for the shared popular-posts list depends on being among the highest-follower accounts that posted in the last 7 days; most accounts will not qualify, so this path likely matters only for very large accounts.
- **Observable proxy:** follower count
- **Limitations:** The absolute follower threshold depends on how many accounts posted in 7 days, which is not in the repo. The BigQuery table's construction is not published; the fraction can be overridden by a CLI flag.

### A16 — Popular-posts job uses original posts only

- **Location:** [`home-mixer/popular_posts_job.rs:67-106`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/popular_posts_job.rs#L67-L106) · symbol `is_original, Job::fetch_posts` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The popular-posts job fetches posts for popular authors from Thunder in chunks of 20 authors with per_author_limits of 50 posts and max_replies_reposts_per_author Some(0), then keeps only originals (not replies or reposts) before fetching view counts and selecting.
- **Relevance to an account:** Replies and reposts from popular authors are not eligible for the shared popular list.
- **Observable proxy:** post type (original vs reply/repost); views
- **Limitations:** Job cadence is a CLI flag (default 300s); production flags unknown.

### A17 — Tweet Mixer source is disabled by default

- **Location:** [`home-mixer/sources/tweet_mixer_source.rs:17-29`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/tweet_mixer_source.rs#L17-L29) · symbol `TweetMixerSource::enable, MAX_POST_AGE` · commit `07d159b`
- **Status:** verified
- **Mechanism:** TweetMixerSource requests HOME_RECOMMENDED_TWEETS from the tweet-mixer service and keeps candidates up to MAX_POST_AGE (48h). It is gated by EnableTweetMixerSource, which defaults to false in param.rs (TweetMixerMaxResults default 800).
- **Relevance to an account:** With repo defaults it contributes no candidates, so it is unlikely to drive reach for most viewers.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Tweet-mixer's internal candidate sources are not in this repo. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### A18 — Semantic-ID (SID) retrieval source seeded by engagements, off by default

- **Location:** [`home-mixer/sources/sid_source.rs:66-85`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/sources/sid_source.rs#L66-L85) · symbol `SidSource::source` · commit `07d159b`
- **Status:** verified
- **Mechanism:** SidSource takes the same engagement-signal seeds as SimClusters, truncated to SidSourceMaxSeeds (default 50), and asks the SID retrieval service for posts sharing a semantic-ID prefix of at least SidSourceMinPrefixDepth (default 3), up to SidSourceMaxPerSeed (100) per seed and SidSourceMaxResults (800). EnableSidSource defaults to false; when enabled it disables the MoE source.
- **Relevance to an account:** If enabled for a viewer, content-similar posts (same semantic-ID prefix) to what they engaged with could be surfaced, a content-based non-follower discovery path.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Off by default per param.rs; SID assignment model is in phoenix/xrex (sid code) and SID index server.


## B. Ranking and engagement prediction

### B01 — Predicted heads consumed by the value model

- **Location:** [`xai-value-model/phoenix_scores.rs:1-31`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/phoenix_scores.rs#L1-L31) · symbol `PhoenixScores` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PhoenixScores lists the per-candidate predictions the value model reads: probability heads (favorite, reply, retweet, photo_expand, video_open, click, open_link, profile_click, vqv, share, share_via_dm, share_via_copy_link, dwell, quote, quoted_click, quoted_vqv, follow_author, post_unexplored, react_with_video), negative heads (not_interested, block_author, mute_author, report, not_dwelled) and continuous values (dwell_time, click_dwell_time, home_video_continuation_secs, home_profile_visit_secs).
- **Relevance to an account:** These are the only engagement predictions that enter the weighted score; actions not listed (e.g. bookmark) have no direct weight in ranking.
- **Observable proxy:** likes, replies, reposts, quotes (public counts only loosely track predicted probabilities)
- **Limitations:** The mapping from Phoenix output indices to these fields is in the component_library (PredictNextActions::candidate_scores), not in this repo. Which heads a production checkpoint emits is not published.

### B02 — Continuous action names in recsys.proto

- **Location:** [`phoenix/crates/serving/xai-recsys-proto/proto/recsys.proto:683-692`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/phoenix/crates/serving/xai-recsys-proto/proto/recsys.proto#L683-L692) · symbol `ContinuousActionName` · commit `07d159b`
- **Status:** verified
- **Mechanism:** recsys.proto defines ContinuousActionName (HOME_PROFILE_VISIT_SECS, DWELL_TIME, CLICK_DWELL_TIME, HOME_VIDEO_CONTINUATION_SECS, plus ads/value names) alongside the ActionName enum of discrete actions (e.g. SERVER_TWEET_FAV = 1 at line 445). PhoenixScorer reads HomeVideoContinuationSecs and HomeProfileVisitSecs only when EnableHomeExcursionScores is true (default false).
- **Relevance to an account:** Dwell time and click-dwell time are modelled as continuous values; time spent on a post (not just taps) can feed ranking via ContDwellTimeWeight and ContClickDwellTimeWeight.
- **Observable proxy:** none — not observable from public data (dwell is private)
- **Limitations:** A second copy of recsys.proto exists under phoenix/python/common/xai-proto/proto/.

### B03 — Published weights: like, reply, bidirectional boost, repost

- **Location:** [`home-mixer/params/param.rs:345-359`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L345-L359) · symbol `FavoriteWeight, ReplyWeight, BidirectionalFollowReplyWeightBoost, BidirectionalFollowDwellWeightBoost, RetweetWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs sets FavoriteWeight 0.66, ReplyWeight 5.0, BidirectionalFollowReplyWeightBoost 15.0, BidirectionalFollowDwellWeightBoost 0.0 and RetweetWeight 1.0. Each multiplies a predicted probability for the viewer, not an engagement count.
- **Relevance to an account:** Posts a viewer is predicted to reply to get relatively large weight per unit probability; the contribution also depends on how likely each action is, which the weights do not show.
- **Observable proxy:** replies, likes, reposts
- **Limitations:** Line 1 states values are mirrored from config defaults (last sync 2026-10-22T16:00:34Z). README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B04 — Published weights: clicks, expands, profile click 0, VQV 0

- **Location:** [`home-mixer/params/param.rs:360-380`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L360-L380) · symbol `PhotoExpandWeight, VideoOpenWeight, ClickWeight, OpenLinkWeight, ProfileClickWeight, VqvWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs sets PhotoExpandWeight 0.05, VideoOpenWeight 0.02, ClickWeight 0.3, OpenLinkWeight 0.2, ProfileClickWeight 0.0 and VqvWeight 0.0. With weight 0.0, predicted profile clicks and video quality views add nothing to the weighted score.
- **Relevance to an account:** Under these defaults, predicted profile clicks and video quality views do not raise a post's score; link opens and post clicks contribute small weights.
- **Observable proxy:** none — not observable from public data (clicks/expands are private)
- **Limitations:** VQV is additionally gated per candidate (vqv_eligible in home-mixer/util/candidates_util.rs: video duration > MinVideoDurationMs and a follower-count condition on the requesting user). README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B05 — Published weights: shares (copy link 20), dwell, quote

- **Location:** [`home-mixer/params/param.rs:381-395`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L381-L395) · symbol `ShareWeight, ShareViaDmWeight, ShareViaCopyLinkWeight, DwellWeight, QuoteWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs sets ShareWeight 2.0, ShareViaDmWeight 5.0, ShareViaCopyLinkWeight 20.0, DwellWeight 0.05 and QuoteWeight 5.0. share_via_copy_link has the largest positive weight in the file.
- **Relevance to an account:** Posts viewers are predicted to share (especially via copy link or DM) or quote receive relatively high weight per unit probability; since such actions are presumably rare, the realized effect is uncertain.
- **Observable proxy:** quotes (public); shares are not public
- **Limitations:** Weights scale predicted probabilities whose base rates differ by action, so weight size alone does not show relative influence. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B06 — Published weights: follow_author, unexplored, continuous dwell

- **Location:** [`home-mixer/params/param.rs:396-437`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L396-L437) · symbol `QuotedClickWeight, QuotedVqvWeight, FollowAuthorWeight, PostUnexploredWeight, ReactWithVideoWeight, ContDwellTimeWeight, ContClickDwellTimeWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs sets QuotedClickWeight 0.05, QuotedVqvWeight 0.0, FollowAuthorWeight 4.0, PostUnexploredWeight 0.015, ReactWithVideoWeight 0.0, ContDwellTimeWeight 0.006 and ContClickDwellTimeWeight 0.4. The cont_* weights multiply predicted continuous dwell values rather than probabilities.
- **Relevance to an account:** Predicted probability that a viewer follows the author is rewarded, which could favour posts that convert non-followers; predicted dwell also contributes. PostUnexplored applies only to in-network candidates in home-mixer (see B17).
- **Observable proxy:** follower growth after posts (weak, aggregate proxy); dwell not observable
- **Limitations:** Units/scale of predicted dwell_time and click_dwell_time are not documented. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B07 — Published negative weights

- **Location:** [`home-mixer/params/param.rs:439-463`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L439-L463) · symbol `NotInterestedWeight, BlockAuthorWeight, MuteAuthorWeight, ReportWeight, NotDwelledWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs sets NotInterestedWeight -52.272, BlockAuthorWeight -31.2, MuteAuthorWeight -58.8, ReportWeight -234.0 and NotDwelledWeight -0.02. These multiply the viewer's predicted probability of each negative action.
- **Relevance to an account:** Content a viewer is predicted to mark not-interested, mute, block or report is pushed down for that viewer; per the code comments, this is personalized rather than a global count-based penalty.
- **Observable proxy:** none — not observable from public data (negative feedback is private)
- **Limitations:** See B08 for the authors' caution against reading weight ratios as count equivalences. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B08 — Weights multiply predicted probabilities; only Home Timeline engagement counts

- **Location:** [`home-mixer/params/param.rs:316-344`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L316-L344) · symbol `weights comment block` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The param.rs comment says each weight multiplies a predicted probability (or continuous value) and not raw engagement counts, so ratios such as report vs like are not count equivalences. It adds that the baseline report probability is more than 1000x lower than a like, and that for an engagement to count in the recommendation system it must happen on a post served in Home Timeline.
- **Relevance to an account:** Coordinated engagement from people navigating directly to a post is described as having no ranking impact; reach depends on per-viewer predicted actions, not totals.
- **Observable proxy:** none — public counts do not separate Home Timeline engagement from other surfaces
- **Limitations:** The same comment appears in xai-value-model/scoring.rs (lines 28-56) and README.md lines 353-355. The '468' example matches 234/0.5 (the vm-ranker/params.rs favorite default), whereas param.rs now has 0.66 (inferred arithmetic). The training-label pipeline that enforces the Home Timeline rule is not shown in this file.

### B09 — compute_weighted_score: weighted sum with eligibility gates

- **Location:** [`xai-value-model/scoring.rs:73-113`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L73-L113) · symbol `compute_weighted_score` · commit `07d159b`
- **Status:** verified
- **Mechanism:** compute_weighted_score sums apply(score, weight) = score.unwrap_or(0.0) * weight across all heads. VQV and quoted VQV weights are zeroed for ineligible candidates; post_unexplored applies only in-network unless post_unexplored_include_out_of_network is set; reply and dwell weights come from reply_weight_for / dwell_weight_for (bidirectional boost). Continuous video/profile terms are products of a probability and a continuous value.
- **Relevance to an account:** A post's base score is a linear blend of predicted actions for the specific viewer; missing heads contribute 0.
- **Observable proxy:** likes, replies, reposts, quotes as weak proxies of predicted heads
- **Limitations:** Model calibration and head availability in production are unknown.

### B10 — offset_score and NEGATIVE_SCORES_OFFSET

- **Location:** [`xai-value-model/scoring.rs:161-181`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L161-L181) · symbol `offset_score, unoffset_score, NEGATIVE_SCORES_OFFSET` · commit `07d159b`
- **Status:** verified
- **Mechanism:** offset_score adds NEGATIVE_SCORES_OFFSET (0.001, weights.rs line 4) to non-negative combined scores. Negative combined scores are mapped to (combined + negative_sum) / total_sum * 0.001, i.e. into the range below the offset, where negative_sum is the magnitude of the negative weights. unoffset_score inverts this.
- **Relevance to an account:** Posts whose predicted negatives outweigh positives for a viewer are compressed below every net-positive post, so they would rank under all net-positive candidates for that viewer.
- **Observable proxy:** none — not observable from public data
- **Limitations:** home-mixer/params/config.rs line 43 duplicates the 0.001 constant.

### B11 — vm-ranker/params.rs defaults conflict with home-mixer param.rs

- **Location:** [`vm-ranker/params.rs:3-132`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/params.rs#L3-L132) · symbol `FavoriteWeight, VideoOpenWeight, ContDwellTimeWeight, PostUnexploredWeight, NotInterestedWeight` · commit `07d159b`
- **Status:** verified
- **Mechanism:** vm-ranker/params.rs declares the same feature-switch keys with different compiled defaults: FavoriteWeight 0.5 (vs 0.66), VideoOpenWeight 0.07 (vs 0.02), ContDwellTimeWeight 0.004 (vs 0.006), PostUnexploredWeight 0.02 (vs 0.015) and NotInterestedWeight -47.52 (vs -52.272). Other weights in this range match, and it adds VideoContinuationWeight, UserVideoContinuationWeight and ProfileVisitSecsWeight at 0.0.
- **Relevance to an account:** Which defaults apply in production is ambiguous from code alone; an audit should not treat either file's like weight as certain.
- **Observable proxy:** none — not observable from public data
- **Limitations:** vm-ranker loads feature switches from a synced rust_home_mixer.yml (vm-ranker/config_sync.rs), so live values may override both sets of compiled defaults. Unlike param.rs, vm-ranker/params.rs has no 'last sync' header, so it may be stale (inferred). README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B12 — Author diversity decay and out-of-network discount (vm-ranker)

- **Location:** [`vm-ranker/params.rs:169-228`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/params.rs#L169-L228) · symbol `AuthorDiversityDecay, AuthorDiversityFloor, OonWeightFactor, TopicOonWeightFactor, NewUserOonWeightFactor` · commit `07d159b`
- **Status:** verified
- **Mechanism:** vm-ranker defaults: EnableAuthorDiversity true with AuthorDiversityDecay 0.5 and AuthorDiversityFloor 0.25, applied as (1 - floor) * decay^k + floor for an author's k-th post in the slate (scoring.rs diversity_multiplier). OonWeightFactor 0.75 multiplies out-of-network posts and, with EnableOonRescoreForInNetworkRepliesRetweets true, in-network replies/reposts; topic requests use TopicOonWeightFactor 0.5.
- **Relevance to an account:** A non-follower sees an account's post at a 0.75 multiplier relative to an identical in-network post, and several posts from the same author in one slate get progressively discounted.
- **Observable proxy:** posting frequency (multiple posts per session window); follower count
- **Limitations:** These params are vm-ranker-only names (not in home-mixer param.rs); home-mixer's local value model disables author diversity and OON rescoring (B17), so on the RPC-failure fallback path these multipliers are not applied. NewUserAgeThresholdSecs defaults to 0, effectively disabling the new-user OON factor. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.

### B13 — ComputeValueModel default false is overridden by the request flag

- **Location:** [`vm-ranker/scoring/mod.rs:31-35`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/scoring/mod.rs#L31-L35) · symbol `rank, ComputeValueModel` · commit `07d159b`
- **Status:** verified
- **Mechanism:** vm-ranker computes the value model when req.compute_value_model is true or the ComputeValueModel param is true (default false in vm-ranker/params.rs). home-mixer's RequestShape::build always sets compute_value_model: true with value_model_id "dpp", so the vm-ranker value model runs regardless of the param default; otherwise vm-ranker would pass through home-mixer's scores.
- **Relevance to an account:** Means the vm-ranker weights, author diversity and OON factor (B11/B12) are the ones applied on the normal path, followed by DPP diversity reordering (DppEnabled true, DppTheta 0.65 in vm-ranker/params.rs lines 235-247).
- **Observable proxy:** none — not observable from public data
- **Limitations:** If vm-ranker has no resolved config it falls back to upstream scores (reason no_config); home-mixer/scorers/vm_ranker_request.rs lines 37-45 hold the request flag.

### B14 — Bidirectional (mutual) follow reply boost history

- **Location:** [`docs/BIDIRECTIONAL_BOOST_CHANGE.md:5-11`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/docs/BIDIRECTIONAL_BOOST_CHANGE.md#L5-L11) · symbol `BidirectionalFollowReplyWeightBoost` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The doc says the boost raises the weight on the predicted probability that a viewer replies to an original post from someone they mutually follow. An A/B test from July 10, 2026 tried values 5, 10, 15, 20; a value of 20 rolled out broadly on July 13; on July 24, 2026 it was set to 15. A dwell boost was tested but not shipped broadly.
- **Relevance to an account:** Original posts may rank higher for mutual followers who are likely to reply, which favours accounts with many mutual-follow relationships; it does not affect non-followers.
- **Observable proxy:** replies from accounts the author follows back (partially observable)
- **Limitations:** The doc reports 'great initial results' without metrics. Some users were still in other boost arms per the doc; current arm allocation is unknown.

### B15 — Bidirectional boost eligibility: mutual-follow original posts only

- **Location:** [`xai-value-model/weights.rs:84-100`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/weights.rs#L84-L100) · symbol `ValueModelWeights::reply_weight_for, dwell_weight_for` · commit `07d159b`
- **Status:** verified
- **Mechanism:** reply_weight_for returns reply + bidirectional_follow_reply_weight_boost when the boost is non-zero and the candidate is bidirectional_boost_eligible, defined in inputs.rs as not a reply, not a repost, and is_mutual_follow_author. Mutual status is hydrated by BidirectionalFollowHydrator (EnableBidirectionalFollowHydration default true).
- **Relevance to an account:** With ReplyWeight 5.0 and boost 15.0 the effective reply weight for eligible posts is 20.0 in home-mixer defaults (arithmetic); only original posts benefit, not the author's replies or reposts.
- **Observable proxy:** reply counts on original posts; mutual-follow relationships (partially public)
- **Limitations:** Mutual-follow check uses the social graph at request time; failures return errors for the hydrator.

### B16 — Phoenix ranking transformer with candidate isolation

- **Location:** [`phoenix/xrex/pallas/ranker_attention_utils.py:49-56`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/phoenix/xrex/pallas/ranker_attention_utils.py#L49-L56) · symbol `history_candidate_mask` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The ranker attention mask lets history and candidate queries attend to history keys, while a candidate may attend to candidate keys only at its own position (q_pos == kv_pos). Per README, this makes a candidate's score independent of which other posts are in the batch.
- **Relevance to an account:** A post's predicted engagement depends on the viewer's history and the post, not on competing posts; competition only matters later via sorting, diversity and DPP.
- **Observable proxy:** none — not observable from public data
- **Limitations:** phoenix/README.md lines 129-235 describe the mask (user-token handling there is described at the README level). Production checkpoints and model sizes are not published; several attention kernel variants exist in phoenix/xrex/pallas/.

### B17 — home-mixer local value model hard-codes several terms to 0/off

- **Location:** [`home-mixer/scorers/value_model.rs:28-49`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/value_model.rs#L28-L49) · symbol `weights_for` · commit `07d159b`
- **Status:** verified
- **Mechanism:** weights_for in home-mixer sets video_continuation, user_video_continuation and profile_visit_secs to 0.0, post_unexplored_include_out_of_network false, enable_author_diversity false (decay/floor 1.0), oon_rescore_in_network_replies_retweets false and multiplier_pre_offset false, while reading the other weights from param.rs.
- **Relevance to an account:** Predicted video-continuation seconds and profile-visit seconds do not affect the local score; author diversity and OON discounting are left to vm-ranker.
- **Observable proxy:** none — not observable from public data
- **Limitations:** vm-ranker reads its own VideoContinuationWeight/UserVideoContinuationWeight/ProfileVisitSecsWeight (all default 0.0), so those terms are also zero on the vm-ranker path under defaults.

### B18 — Scorer order: PhoenixScorer, ImmersiveVideoScorer, VMRanker

- **Location:** [`home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs:475-476`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs#L475-L476) · symbol `PhoenixCandidatePipeline::build_with_clients (scorers)` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PhoenixCandidatePipeline runs scorers in the order PhoenixScorer (per-action predictions), ImmersiveVideoScorer (immersive predictions for carousel videos, only when the video carousel is enabled), then VMRanker (local weighted score + cold start, then the vm-ranker RPC).
- **Relevance to an account:** Pre-scoring filters run before this, so a post removed by filters is never scored; final order comes from VMRanker's score, then TopKScoreSelector.
- **Observable proxy:** none — not observable from public data
- **Limitations:** README's diagram names a 'RankingScorer' step; in this code that logic lives inside VMRanker (value_model + author_cold_start) and vm-ranker. VMRanker is gated by EnableRanking (default true).

### B19 — Local-score fallback when the vm-ranker RPC fails

- **Location:** [`home-mixer/scorers/vm_ranker.rs:107-113`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/vm_ranker.rs#L107-L113) · symbol `VMRanker::score` · commit `07d159b`
- **Status:** verified
- **Mechanism:** If the vm-ranker call fails, VMRanker logs a warning, records a local_score_fallback metric and serves the locally computed scores (home-mixer weighted score with cold-start lift). Candidates missing from a successful response also keep local scores. Separately, VMRankerEnableFallback (default false) only controls retrying via DNS after an xDS failure.
- **Relevance to an account:** On fallback, author diversity, OON discount and DPP reordering are not applied (B17), so ranking could differ for those requests; frequency is unknown.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Fallback rates are only in internal metrics.

### B20 — New-author cold-start lift with Thompson sampling

- **Location:** [`home-mixer/scorers/author_cold_start.rs:243-334`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/author_cold_start.rs#L243-L334) · symbol `sample_reward, pick_thompson, apply_cold_start` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Eligible posts are originals (not replies/reposts) from authors with followers <= ColdStartFollowerCap, no older than ColdStartMaxPostAgeSecs, with view_count_on_home < ColdStartImpressionThreshold, ranked within LowImpressionsMaxPositionRatio of non-zero scores, and in the viewer's experiment corpus. One post is picked (Thompson sampling over Beta(alpha0 + favs, beta0 + views - favs), then highest score among the top ts_top_k) and its score is raised to at least the score at a random rank in [slot_min, slot_max) chosen by cold_start_target (lines 216-226).
- **Relevance to an account:** Smaller accounts' fresh, low-impression original posts can be lifted into a mid-feed slot for some viewers; among eligible posts, a higher like-to-view ratio raises the sampled reward.
- **Observable proxy:** follower count; likes and views in the first hours after posting; post age
- **Limitations:** At most one post per request is lifted. Corpus eligibility depends on experiment arms (PhoenixMoeCodivertViewerIsTreatment/Control; AuthorIsTreatment/Control); with both viewer flags false the viewer is in Holdout, where all authors are corpus-eligible. view_count_on_home comes from the engagement-counts service (not in repo). In vm-ranker the lift is applied before the author-diversity and OON multipliers (xai-value-model/scoring.rs lines 315-327), so a lifted out-of-network post is still discounted.

### B21 — Cold-start parameter defaults

- **Location:** [`home-mixer/params/param.rs:538-617`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L538-L617) · symbol `ColdStart* params` · commit `07d159b`
- **Status:** verified
- **Mechanism:** param.rs defaults: ColdStartImpressionThreshold 200, ColdStartSlotMin 15, ColdStartSlotMax 16, ColdStartFollowerCap 50000, ColdStartMaxPostAgeSecs 7200, LowImpressionsMaxPositionRatio 0.97, EnableViewerColdStart true, EnableColdStartThompsonSampling true, ColdStartBetaAlpha0 0.75, ColdStartBetaBeta0 49.25, ColdStartTsTopK 2, ColdStartImpressionScale 1.0.
- **Relevance to an account:** Under these defaults the lift targets posts under 2 hours old, with fewer than 200 home views, from accounts with at most 50000 followers; the prior mean alpha0/(alpha0+beta0) is 0.015 (arithmetic).
- **Observable proxy:** follower count; views and likes within the first 2 hours
- **Limitations:** view_count_on_home is not the public view count; public views may include other surfaces. README (Experiments and Configuration) says tunable values are read from a configuration system and that cron scripts set code defaults to the primary production values; per-user experiments can still override them.


## C. Account and content quality

### C01 — user-cred-v2 turns PageRank mass into a 0-100 score

- **Location:** [`user-cred-v2/UserCredV2.scala:9-20`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2.scala#L9-L20) · symbol `UserCredV2.fromMass` · commit `07d159b`
- **Status:** verified
- **Mechanism:** user-cred-v2 is an offline Scalding job that runs PageRank and converts each account's resulting mass into a score of 165.2 + 7.07 * ln(mass), clamped to [0, 100]; zero or negative mass maps to 0. The score is logarithmic in mass, so large differences in mass translate into modest score differences.
- **Relevance to an account:** The score is an account-level reputation number. In this repo it is used to exempt high-scoring accounts from some automated spam labelling (see C05, C06, C10, C11), not as a ranking feature in the For You value model (see C07).
- **Observable proxy:** none — not observable from public data (mass depends on the whole follow graph and on non-public engagement logs)
- **Limitations:** Only the job is published; the output dataset and the values any given account receives are not. Slope/intercept are hard-coded here but production could run a different build.

### C02 — user-cred-v2 PageRank defaults (jump 0.2, 50 iterations, beta 0.5)

- **Location:** [`user-cred-v2/UserCredV2Config.scala:24-45`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2Config.scala#L24-L45) · symbol `UserCredV2Config.fromArgs` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Command-line defaults set the PageRank jump (teleport) probability to 0.2, convergence threshold 0.001, at most 50 iterations, and an engagement teleport blend beta of 0.5. Engagement edges are read over a 7-day window (EngagementWindowDays), and the run is gated on row-count and mass-sum sanity checks before publishing.
- **Relevance to an account:** The 7-day engagement window means the engagement-driven part of an account's score can move week to week; the follow-graph part changes more slowly.
- **Observable proxy:** none — not observable from public data
- **Limitations:** These are argument defaults; the production job may be launched with other values. vit_threshold (55.0) is read but its use is outside this file.

### C03 — user-cred-v2 teleport set is premium/verified accounts plus engagement mass

- **Location:** [`user-cred-v2/UserCredV2App.scala:141-193`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2App.scala#L141-L193) · symbol `UserCredV2App.computeTeleportWeights` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The PageRank graph uses follow edges; the teleport (restart) distribution blends (1 - beta) x uniform mass over premium accounts (blue, gold, gray verified, verified organisations and their affiliates, excluding near-zero state accounts) with beta x engagement mass, where each engager's prior mass is split across the authors they liked or reposted in the window. Restricted, deactivated, suspended and erased accounts are dropped from the user set.
- **Relevance to an account:** Being followed by, or liked/reposted by, accounts that themselves hold mass (premium accounts are seeded with mass) would plausibly raise an account's score. This affects reach only through the consumers in C05/C06/C10/C11, which use the score as an exemption from some spam actions.
- **Observable proxy:** Partial: whether followers/engagers are verified is visible publicly; their mass is not.
- **Limitations:** isPremium is defined in user-cred-v2/ValidUserInfo.scala. The magnitude of any individual account's mass cannot be reconstructed without the full graph.

### C04 — user-cred-v2 counts only likes/reposts and drops linked-account edges

- **Location:** [`user-cred-v2/UserCredV2App.scala:79-118`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2App.scala#L79-L118) · symbol `readEngagementEdges, filterLinkedUserEdges` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Engagement edges are built only from Favorite and Retweet interactions where the engager is not the author. Both follow and engagement edges are removed when the (source, destination) pair appears in an account-expansion investigations dataset of linked users, so edges between accounts flagged as linked do not transfer mass.
- **Relevance to an account:** Self-engagement and engagement from accounts identified as linked to the author would plausibly not raise the author's score; replies, quotes and bookmarks are not engagement edges here.
- **Observable proxy:** Partial: public like/repost counts exist, but who engaged and whether accounts are linked is not public.
- **Limitations:** How AccountExpansionInvestigations identifies linked users is not in this repo.

### C05 — scarecrow rules treat high user-cred (>= 54) as an exemption

- **Location:** [`botmaker-rules/scarecrow/derived-feature/IsHighPageRankUser.df:1-28`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/botmaker-rules/scarecrow/derived-feature/IsHighPageRankUser.df#L1-L28) · symbol `IsHighPageRankUser` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The botmaker derived feature IsHighPageRankUser is true when the UserCredV2 score is >= HighPageRankThreshold (54 in HighPageRankThreshold.df) or the account carries a PREDICTED_HIGH_PAGE_RANK label; if neither is available it falls back to follower count > 25,000. Many scarecrow rules (low-quality URL, duplicate text, Grox reply flags, NSFW labelling) require !IsHighPageRankUser before acting.
- **Relevance to an account:** Accounts below the threshold are eligible for these automated labels; accounts above it are skipped by the rules that check it. Being below the threshold does not by itself reduce reach.
- **Observable proxy:** Partial: follower count (> 25,000 fallback) is public; the user-cred score and PREDICTED_HIGH_PAGE_RANK label are not.
- **Limitations:** Some botmaker rules are withheld from the repo (README "What's not in this repo?"), so the full set of rules using this exemption is unknown.

### C06 — abuse-enforcement-service skips accounts with high cred, grey badge or many followers

- **Location:** [`abuse-enforcement-service/service-lib/rules/enforcement_user.yaml:18-38`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/abuse-enforcement-service/service-lib/rules/enforcement_user.yaml#L18-L38) · symbol `very_high_follower_count, high_follower_count, pagerank_skipped` · commit `07d159b`
- **Status:** verified
- **Mechanism:** In the published user and post enforcement rule files, an account is skipped (no action) when cred.is_high is true (high-PageRank flag OR grey badge, composed in strato.rs compose_cred) or cred.score >= 50.0, and also above follower-count thresholds. The follower thresholds in the file are explicitly mock values; production uses different ones.
- **Relevance to an account:** Model-driven suspensions and labels (e.g. SpamHighRecall from anchor-campaign scores) are not applied to accounts that clear these skips. Lower-cred, smaller accounts are the ones exposed to these actions.
- **Observable proxy:** Partial: follower count is public but production thresholds are not; cred score is not public.
- **Limitations:** The file is "mirrored from GrowthBook dynamic config"; production rules can change without a code change. Follower thresholds are mock values.

### C07 — No user-cred input in the For You value-model scoring path

- **Location:** [`xai-value-model/inputs.rs:3-17`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/inputs.rs#L3-L17) · symbol `CandidateScoringInputs` · commit `07d159b`
- **Status:** inferred
- **Mechanism:** The per-candidate inputs to the value model are predicted engagement scores plus author id, in-network, reply/retweet, mutual-follow and video eligibility flags; there is no user-cred, PageRank or verification field. A search of home-mixer, vm-ranker and xai-value-model finds no reference to user cred or page rank. In bdsm the user_cred_norm feature is filled with zeros.
- **Relevance to an account:** In this code, the final weighted score does not appear to apply a direct reputation multiplier. Cred can still matter indirectly through labels whose application it gates (C05/C06/C10/C11), which visibility filtering can act on.
- **Observable proxy:** none — not observable from public data
- **Limitations:** This is a negative result from searching the published code. The Phoenix model's own input features are not fully audited here, and a TweetEmbedding thrift struct in phoenix/crates/serving/xai-recsys-mm-server/src/events.rs carries a user_credibility field whose use was not traced.

### C08 — Agatha rate-based labels (blocks, reports, spam reports per out-of-network fav)

- **Location:** [`agatha/scalding/labels/rate_based_labels/RateBasedLabels.scala:28-118`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/agatha/scalding/labels/rate_based_labels/RateBasedLabels.scala#L28-L118) · symbol `RateBasedLabels.computeScoresForInteractions, getUserLabels` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Agatha's offline job computes per-account smoothed ratios of blocks, abuse reports (180-day window, AbuseTriageTool reports only), legit spam reports and all spam reports, each relative to out-of-network favorites received: (interaction + 0.1) / (interaction + favs + 0.1 / prior). These are written as user labels (BlocksPerFav, ReportsPerFav, SpamReportsPerFav, AllSpamReportsPerFav) used in downstream account models.
- **Relevance to an account:** An account that draws many blocks or reports relative to the likes it gets from non-followers would plausibly get a higher rate. How those rates turn into labels or enforcement that affect reach is not shown here.
- **Observable proxy:** Partial: public like counts give a rough denominator; blocks and reports are not public.
- **Limitations:** Thresholds and the models trained on these labels (e.g. Blink scores in agatha/scalding/blink) are only partly published. Blocks are taken from a graph snapshot filtered by update time and known-artificial users.

### C09 — BDSM behavioural sequence model for bots/spam/coordination (thresholds redacted)

- **Location:** [`bdsm/README.md:17-40`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/bdsm/README.md#L17-L40) · symbol `bdsm heads` · commit `07d159b`
- **Status:** verified
- **Mechanism:** BDSM is a transformer over an account's recent action sequence (timing-aware position embeddings, action type, surface, dwell, device signals) with eight heads: FollowBot, LikeBot, EngagementAmplifier, ReplySpamBot, TweetSpamBot, RTBot, MultiActionBot and LegitimateUser. A results sink applies per-head thresholds and graduated actions (challenge vs suspend).
- **Relevance to an account:** Automation-like patterns (mechanical cadence, bursts, repetitive engagement) are what the model is designed to detect; an account flagged here could be challenged or suspended, which would plausibly remove reach entirely.
- **Observable proxy:** Partial: post timestamps and posting cadence are public; likes, follows, dwell and device signals of the account are not.
- **Limitations:** Operating points are redacted: bdsm/runtime/sink_policy.yaml ships 9.99 and 999999 sentinels. The backing sequence store and weights are not published.

### C10 — Grox PTOS spam verdicts apply SpamHighRecall post labels

- **Location:** [`grox/flows/ptos/task_write_safety_post_annotations_result_sink.py:233-248`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/ptos/task_write_safety_post_annotations_result_sink.py#L233-L248) · symbol `TaskWriteSafetyPostAnnotationsResultSink._apply_labels_for_annotation` · commit `07d159b`
- **Status:** verified
- **Mechanism:** When the Grox PTOS (post terms-of-service) classifier returns a Spam violation, the sink applies the SpamHighRecall post label. Engagement baiting, engagement farming and card manipulation are labelled for every author; other spam policy types are skipped for high-PageRank authors. Adult and violent-media verdicts apply NSFW/gore labels.
- **Relevance to an account:** A SpamHighRecall post label drops the post from out-of-network For You recommendations to non-authors (see C17), while followers can still see it. Engagement-bait style posts are labelled even for high-cred authors.
- **Observable proxy:** Partial: post text is public, so engagement-bait phrasing can be checked heuristically; the classifier verdict is not public.
- **Limitations:** The LLM prompts defining each policy are withheld (C12). Which posts enter the PTOS flow (rate limits, filters) is only partly visible.

### C11 — Grox reply spam flags replies with RiskyHighVizReply unless high cred (>= 66)

- **Location:** [`grox/flows/reply_spam/task_write.py:39-80`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/reply_spam/task_write.py#L39-L80) · symbol `_is_label_exempt_high_page_rank, _apply_reply_spam_label` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The reply_spam flow scores replies; when the reply-ranking score is 0.0 it applies the RiskyHighVizReply post label unless the author's user-cred is >= 66 (or the high-PageRank flag when no score), the author has a grey badge, or is a test user. Separately, scarecrow rule 25026 applies RISKY_HIGH_VIZ_REPLY for 14 days when a Grox spamScore >= 0.97, unless the reply is by the conversation author or the author is high-PageRank, skip-listed or gray verified.
- **Relevance to an account:** Low-cred accounts that leave replies judged spammy may have those replies labelled; the rule name suggests a downrank of the reply, but where the label is consumed is not in this repo.
- **Observable proxy:** Partial: an account's reply text and reply volume are public; scores and labels are not.
- **Limitations:** The consumer of RiskyHighVizReply (e.g. conversation reply ordering) is not present; the effect on reach is inferred from the label name only. Prompts are withheld. See botmaker-rules/scarecrow/bot/GroxTweetProcessor.bot for rule 25026.

### C12 — Grox prompts withheld; UPA "banger" screen and multimodal embeddings

- **Location:** [`grox/flows/ptos/prompts.py:11-11`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/ptos/prompts.py#L11) · symbol `prompts.py` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Grox runs LLM/VLM flows on posts: ptos (safety/spam policy), reply_spam, upa (an initial "banger" screen and post-safety screen that send boolean metadata to a labelling endpoint) and mm_emb (multimodal post embeddings). The prompt templates (.j2) are excluded from the repo; each prompts.py says so in a comment.
- **Relevance to an account:** Grox outputs can become post labels that visibility filtering acts on, but the classification criteria are not public, so a specific post's risk cannot be predicted from code alone.
- **Observable proxy:** none — not observable from public data (criteria withheld; outputs not public except via the Under the Hood label tool)
- **Limitations:** The README lists Grox prompts among withheld files. How UPA labels are used downstream (grok_upa_action_with_labels) is not shown. mm_emb gates embedding by an adaptive minimum fav count (grox/flows/mm_emb/adaptive_min_fav.py).

### C13 — abuse-enforcement-service maps model labels to post/account actions

- **Location:** [`abuse-enforcement-service/service-lib/rules/enforcement_post.yaml:39-58`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/abuse-enforcement-service/service-lib/rules/enforcement_post.yaml#L39-L58) · symbol `act_add_llm_slop_post_label, act_add_gibberish_post_label, act_add_fast_reply_spam_post_label` · commit `07d159b`
- **Status:** verified
- **Mechanism:** After the skip rules, enforcement rules map model score labels to actions, for example llm_slop_post -> RiskyHighVizReply post label for 30 days, gibberish_post and fast_reply_spam_post -> SpamHighRecall post label, anchor_campaign_* -> SpamHighRecall user label or suspension. The post rules also apply the follower/PageRank skips unless a score sets skip_author_credibility_prechecks.
- **Relevance to an account:** Posts classified as low-effort generated text, gibberish or fast reply spam can receive labels that limit distribution (SpamHighRecall is a drop for out-of-network recommendations, C17).
- **Observable proxy:** Partial: post text and reply timing are public; the upstream model scores are not.
- **Limitations:** The models producing labels like llm_slop_post are not in this file and may not be published. The rules are a mirror of GrowthBook config and may change.

### C14 — abuse-ledger appeal holds block re-applying overturned actions

- **Location:** [`abuse-ledger-service/src/sql.rs:3-7`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/abuse-ledger-service/src/sql.rs#L3-L7) · symbol `PROBE_SQL` · commit `07d159b`
- **Status:** verified
- **Mechanism:** abuse-ledger-service answers whether an account has an active (uncleared, unexpired) enforcement hold for a suspension or for specific labels. Per the README, when an enforcement is overturned on appeal, abuse-enforcement-service does not re-apply that action for a fixed period set per appeal queue.
- **Relevance to an account:** A successful appeal can temporarily protect an account from the same automated label or suspension being re-applied.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Hold durations per queue are not in the repo. The client side in abuse-enforcement-service was only partly read.

### C15 — botmaker-rules label duplicate-text replies as COPYPASTA_SPAM (some rules withheld)

- **Location:** [`botmaker-rules/scarecrow/bot/BBQDuplicateTextRepliesProd.bot:25-46`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/botmaker-rules/scarecrow/bot/BBQDuplicateTextRepliesProd.bot#L25-L46) · symbol `BBQDuplicateTextRepliesProd` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Rule 21599 consumes scheduled BigQuery jobs that cluster replies with duplicate text (unigrams, or characters for CJK) and applies the COPYPASTA_SPAM label to each reply, skipping test users, high-PageRank users, a temporary skip list and gray-verified users. Some botmaker rules are deliberately not published.
- **Relevance to an account:** Posting the same or near-identical reply text repeatedly could plausibly get replies labelled; the rule's own note calls this a downrank, but the label's ranking effect is not shown in this repo.
- **Observable proxy:** Account's own reply texts are public, so repeated identical replies can be counted.
- **Limitations:** README.md line 433 lists "Some botmaker rules" as withheld. The clustering query and its similarity thresholds are not published.

### C16 — Visibility-filtering verdicts are Withheld (Drop/Tombstone) or Shown with notices

- **Location:** [`visibility-filtering/models/verdict.rs:8-26`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/visibility-filtering/models/verdict.rs#L8-L26) · symbol `Verdict, Notice` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The visibility-filtering service returns either Withheld (Drop or Tombstone) or Shown with optional notice (soft intervention, appealable notice, label interstitial), media restriction and limited-engagement parts. Per the README, the first rule that answers drop ends evaluation.
- **Relevance to an account:** Only drop-type outcomes remove a post from For You in home-mixer (see D13); notices and interstitials change presentation, not eligibility, in the code read here.
- **Observable proxy:** Partial: interstitials/notices are visible on public posts; drops are not observable from public data.
- **Limitations:** The mapping from Verdict to the client Action enum used by home-mixer (Allow, Interstitial, Avoid, Downrank, Drop, Tombstone, NotEvaluated) was not fully traced.

### C17 — Extra drop rules for out-of-network recommendations; README cites missing registry.rs

- **Location:** [`visibility-filtering/rules/levels.rs:142-213`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/visibility-filtering/rules/levels.rs#L142-L213) · symbol `TIMELINE_HOME_RECOMMENDATIONS` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Home-mixer evaluates in-network posts at safety level TimelineHome and out-of-network posts (plus ancestors and quotes) at TimelineHomeRecommendations. The recommendations level adds author-label drops (NSFW labels, SpamHighRecall, Compromised, ReadOnly, Impersonation, AbusiveHighRecall, DoNotAmplify) and post-label drops (DMCA, NSFW, SoftNsfw for new users, DoNotAmplify, MaliciousUrl, SpamHighRecall, abuse insults). The README says these lists live in visibility-filtering/rules/registry.rs, which does not exist; they are in rules/levels.rs.
- **Relevance to an account:** An account or post carrying one of these labels would plausibly lose out-of-network For You distribution while remaining visible to followers in their home timeline. DoNotAmplify user label applies to non-followers only.
- **Observable proxy:** none — not observable from public data (labels visible only to the account via the Under the Hood tool, per README)
- **Limitations:** README.md line 408 links to rules/registry.rs, which is absent at this commit. Rule definitions are in rules/tweet_rules.rs and rules/author_rules.rs.

### C18 — safety-label-user-agg promotes repeated post labels to account labels

- **Location:** [`safety-label-user-agg/postToUserLabelRules.strato:395-426`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/safety-label-user-agg/postToUserLabelRules.strato#L395-L426) · symbol `defaultRulesJson (nsfw_high_precision)` · commit `07d159b`
- **Status:** verified
- **Mechanism:** A config-driven Strato library aggregates post safety labels into user labels. The default config includes, for example, applying the NSFW_HIGH_PRECISION user label for 7 days when at least 3 of the account's last 5 posts within 60 days carry NSFW_HIGH_PRECISION. Rules can exclude high-PageRank or grey-badge accounts.
- **Relevance to an account:** Repeated labelled posts can escalate to an account label; NSFW user labels are drop rules for out-of-network recommendations (C17), affecting all of the account's posts while the label lasts.
- **Observable proxy:** Partial: whether recent posts contain adult media is publicly visible; the labels are not.
- **Limitations:** The live rules come from feature switch safety_understanding_post_to_user_label_rules (line 430-432); the default JSON may not match production.

### C19 — Legal and local-law takedowns drop posts in the request country

- **Location:** [`visibility-filtering/rules/tweet_rules.rs:231-243`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/visibility-filtering/rules/tweet_rules.rs#L231-L243) · symbol `LEGAL_TAKEDOWN_DROP_UNSPECIFIED, LOCAL_LAWS_TAKEDOWN_DROP_UNSPECIFIED` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Visibility rules drop a post for non-authors when it has a legal or local-laws takedown in the viewer's request country. The tweet entity service merges a post's own takedown reasons with its author's account-level takedown reasons, so an account-level takedown applies to its posts.
- **Relevance to an account:** Reach in specific countries can be zero for withheld posts or accounts, regardless of engagement. This is country-specific, not global.
- **Observable proxy:** Partial: country-withheld notices are sometimes visible publicly; README says Under the Hood reports show such withholding to the account.
- **Limitations:** See takedowns/tweet-entity-service/TakedownReasonsTransform.scala for the merge; how takedowns are decided is out of scope of the code.

### C20 — Adult-content scoring combines media models with account-level scores

- **Location:** [`pnsfwmedia/model_experimental.py:50-60`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/pnsfwmedia/model_experimental.py#L50-L60) · symbol `_get_final_feature_tensor` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The experimental pNSFW media model concatenates a CLIP image score with account-level health scores, including Agatha's calibrated NSFW score, an NSFW text user score and an NSFW consumer-follower score. Home-mixer also drops SimClusters-sourced out-of-network posts from authors flagged NSFW (OONNsfwSimclustersFilter).
- **Relevance to an account:** An account's history (its own NSFW score and its audience) can influence how its media is classified, and NSFW flags restrict out-of-network recommendation (C17, D01).
- **Observable proxy:** Partial: posted media is public; account-level scores are not.
- **Limitations:** The file is named "experimental"; whether it serves production is not stated. adult-content/ holds training and calibration code only.


## D. Feed-level ranking behaviour

### D01 — Pre-scoring filter order in the Phoenix For You pipeline

- **Location:** [`home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs:419-453`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/candidate_pipeline/phoenix_candidate_pipeline.rs#L419-L453) · symbol `PhoenixCandidatePipeline filters` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Before scoring, candidates pass in order through DropDuplicates, ZeroFavCodivert, CoreDataHydration, NewUserSoftNsfw, Age, SelfTweet, OONRetweetReply, OONNsfwSimclusters, RetweetDeduplication, IneligibleSubscription, PreviouslySeenPosts, PreviouslySeenPostsBackup, PreviouslyServedPosts, ViewerMutedKeyword, AuthorSocialgraph, Brazil2026Election, Video, TopicIds, NewUserMinEngagement, InventoryHoldout, FavHoldout and FairShareRanking. Several are switched off by default params.
- **Relevance to an account:** A post must survive all of these to be scored at all; most are viewer- specific (seen, muted, blocked), so failing one for one viewer does not affect other viewers.
- **Observable proxy:** Partial: post age, reply/repost type and author are public; viewer-side state is not.
- **Limitations:** The README table (README.md lines 370-390) omits ZeroFavCodivert, NewUserSoftNsfw and FairShareRanking; the code is the authority. Holdout and new-user filters default to false in home-mixer/params/param.rs.

### D02 — 48-hour maximum post age for For You candidates

- **Location:** [`home-mixer/params/config.rs:40-40`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/config.rs#L40) · symbol `MAX_POST_AGE` · commit `07d159b`
- **Status:** verified
- **Mechanism:** AgeFilter removes candidates whose snowflake-derived age exceeds MAX_POST_AGE = 48 hours; candidates with undeterminable age are also removed. TweetMixerSource applies the same 48-hour cut, and Thunder's in-memory in-network post store defaults to 172,800 s (2 days) retention.
- **Relevance to an account:** A post plausibly stops receiving For You distribution through this pipeline after 48 hours, regardless of performance.
- **Observable proxy:** Post created_at timestamps are public; impressions per hour after 48h can be compared if available.
- **Limitations:** Other surfaces (search, profile, notifications, conversation views) are not governed by this filter. Thunder retention is a CLI default (thunder/args.rs).

### D03 — SelfTweetFilter removes the viewer's own posts

- **Location:** [`home-mixer/filters/self_tweet_filter.rs:7-20`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/self_tweet_filter.rs#L7-L20) · symbol `SelfTweetFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Candidates authored by the requesting viewer are removed from that viewer's For You candidate set.
- **Relevance to an account:** No effect on an account's reach to others; it only means an author never sees their own post in their own For You feed from this pipeline.
- **Observable proxy:** none — not observable from public data
- **Limitations:** None material.

### D04 — Out-of-network reposts and replies are filtered out

- **Location:** [`home-mixer/filters/oon_retweet_reply_filter.rs:15-28`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/oon_retweet_reply_filter.rs#L15-L28) · symbol `OONRetweetReplyFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Reposts from accounts the viewer does not follow are removed, as are out-of-network replies unless EnablePhoenixOonReplies is on and the reply came from Phoenix retrieval (optionally only replies to the root). Any reply whose ancestors failed to hydrate is removed regardless of network.
- **Relevance to an account:** Replies and reposts mostly reach For You only for the author's followers; with EnablePhoenixOonReplies defaulting to false, an account's replies are unlikely to be recommended to non-followers through this pipeline.
- **Observable proxy:** Post type (reply / repost / original) is public; compare impressions by type.
- **Limitations:** EnablePhoenixOonReplies default (false) is from home-mixer/params/param.rs; experiments can enable it for some viewers.

### D05 — Previously seen and previously served posts are removed

- **Location:** [`home-mixer/filters/previously_seen_posts_filter.rs:16-31`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/previously_seen_posts_filter.rs#L16-L31) · symbol `PreviouslySeenPostsFilter, PreviouslyServedPostsFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** PreviouslySeenPostsFilter drops a candidate if it, or a related post id (the reposted post or the parent it replies to), is in the viewer's seen ids or impression bloom filters. PreviouslyServedPostsFilter drops ones already served in the session (enabled for all requests by default via EnableServedFilterAllRequests).
- **Relevance to an account:** A post is generally shown to a given viewer once in For You; repeat impressions to the same viewer are not expected from this pipeline. Bloom filters can have false positives, so a small share of unseen posts may be dropped.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Bloom-filter sizes and false-positive rates come from request data, not code.

### D06 — AuthorSocialgraphFilter removes blocked/muted authors in either direction

- **Location:** [`home-mixer/filters/author_socialgraph_filter.rs:27-56`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/author_socialgraph_filter.rs#L27-L56) · symbol `AuthorSocialgraphFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Candidates are removed when the viewer mutes or blocks the author, the author blocks the viewer, the quoted author blocks the viewer, or the viewer blocks the quoted or reposted author.
- **Relevance to an account:** Each block or mute removes that one viewer from the author's For You audience; quoting or reposting an account a viewer blocks also hides the quote/repost from that viewer.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Block/mute lists are private.

### D07 — Duplicate posts and repeated reposts collapse to one candidate

- **Location:** [`home-mixer/filters/retweet_deduplication_filter.rs:19-30`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/retweet_deduplication_filter.rs#L19-L30) · symbol `RetweetDeduplicationFilter, DropDuplicatesFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** DropDuplicatesFilter keeps the first copy of a tweet id returned by several sources (merging retrieval sources). RetweetDeduplicationFilter keys candidates on the reposted id (or own id) and keeps only the first, so an original and its reposts collapse to whichever arrived first.
- **Relevance to an account:** Many followers reposting the same post do not create multiple slots for it in one viewer's feed.
- **Observable proxy:** Repost counts are public, but how many reached a given viewer is not.
- **Limitations:** Ordering of candidates before the filter decides which copy survives.

### D08 — DedupConversationFilter keeps one post per conversation (highest score)

- **Location:** [`home-mixer/filters/dedup_conversation_filter.rs:19-49`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/dedup_conversation_filter.rs#L19-L49) · symbol `DedupConversationFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** After selection, candidates are grouped by conversation (the smallest ancestor id, or the original post id) and only the highest-scoring candidate per conversation is kept.
- **Relevance to an account:** An author's self-reply thread or several replies in the same conversation compete for one slot per viewer feed request.
- **Observable proxy:** Conversation ids and reply structure are public.
- **Limitations:** Applies per feed response; other surfaces are not covered.

### D09 — Author diversity multiplier decays repeated authors within one feed

- **Location:** [`xai-value-model/scoring.rs:183-204`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L183-L204) · symbol `diversity_multiplier, author_pool_counts` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Candidates are ordered by score; the k-th additional post from the same author in that request (k = 0 for the first) is multiplied by (1 - floor) * decay^k + floor. With defaults decay 0.5 and floor 0.25 this gives 1.0, 0.625, 0.4375, ... approaching 0.25.
- **Relevance to an account:** Several posts by the same author competing for one viewer's feed are progressively discounted; this is per viewer per request, not a global penalty on posting frequency.
- **Observable proxy:** Posting frequency is public; whether several posts reach the same viewer at once is not.
- **Limitations:** Defaults are in vm-ranker/params.rs (lines 169-186). Home-mixer's local fallback scoring disables author diversity (home-mixer/scorers/value_model.rs).

### D10 — Out-of-network discount (OonWeightFactor 0.75), also for in-network replies/reposts

- **Location:** [`xai-value-model/scoring.rs:206-251`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L206-L251) · symbol `oon_applies, post_fusion_multipliers` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The OON multiplier applies to out-of-network candidates and, when EnableOonRescoreForInNetworkRepliesRetweets is true (default), to in-network replies and reposts. The multiplier is the request's effective_oon_weight: OonWeightFactor (0.75) normally, TopicOonWeightFactor (0.5) for topic requests, or NewUserOonWeightFactor for eligible new viewers.
- **Relevance to an account:** Reaching non-followers carries a 25% score discount at defaults, so out-of-network posts need higher predicted engagement to rank equally.
- **Observable proxy:** Partial: follower vs non-follower impressions are not public; follower count gives the in-network ceiling.
- **Limitations:** Defaults from vm-ranker/params.rs lines 205-228; production values can differ per experiment bucket.

### D11 — New-viewer OON factor exists but default age threshold is 0

- **Location:** [`vm-ranker/scoring/value_model.rs:118-142`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/scoring/value_model.rs#L118-L142) · symbol `scoring_context` · commit `07d159b`
- **Status:** verified
- **Mechanism:** For a viewer younger than NewUserAgeThresholdSecs who follows at least 5 accounts, effective_oon_weight is NewUserOonWeightFactor (default 0.00001), almost eliminating out-of-network posts. With the default threshold of 0 seconds, no viewer qualifies, so the branch is inactive unless configured.
- **Relevance to an account:** If enabled in production, brand-new viewers would see almost only accounts they follow, reducing out-of-network reach to new users.
- **Observable proxy:** none — not observable from public data
- **Limitations:** Whether production sets a non-zero threshold is unknown.

### D12 — DPP diversity rerank zeroes non-selected candidates

- **Location:** [`vm-ranker/scoring/dpp_model.rs:196-207`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/scoring/dpp_model.rs#L196-L207) · symbol `rank_with_memo, dpp::rescore` · commit `07d159b`
- **Status:** verified
- **Mechanism:** vm-ranker takes the top DppMaxSelectedRank (150) candidates by score and greedily selects a subset maximising a determinant over a kernel combining score (scaled by theta 0.65) with cosine similarity of multimodal post embeddings. Selected posts keep their score; non-selected posts get score 0. Posts with missing embeddings get a random unit vector.
- **Relevance to an account:** A post that is semantically similar to higher-scored posts in the same viewer's candidate set can be dropped from the slate even with a good score.
- **Observable proxy:** Partial: post content is public; the embedding and competing candidates are not.
- **Limitations:** Params default in vm-ranker/params.rs (DppEnabled true, theta 0.65, max rank 150); CLI defaults in vm-ranker/args.rs differ (dpp_enabled false, theta 0.5, top_k 50). The final top_k used in production is not shown.

### D13 — VFFilter drops only Drop/Tombstone/NotEvaluated; Downrank/Avoid kept

- **Location:** [`home-mixer/filters/vf_filter.rs:22-27`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/vf_filter.rs#L22-L27) · symbol `should_drop_action` · commit `07d159b`
- **Status:** verified
- **Mechanism:** After selection, VFFilter removes candidates whose visibility action is Drop, Tombstone or NotEvaluated. Allow, Interstitial, Avoid and Downrank are kept, and no other home-mixer code was found that changes scores based on Avoid or Downrank.
- **Relevance to an account:** Visibility filtering affects For You reach mainly by dropping posts. A post whose VF lookup failed (NotEvaluated) would also be dropped.
- **Observable proxy:** none — not observable from public data
- **Limitations:** The absence of Downrank/Avoid handling is from a search of home-mixer only; other services could use them.

### D14 — Post-selection AncillaryVF, AncestorVideo and VideoCarousel filters

- **Location:** [`home-mixer/candidate_hydrators/vf_candidate_hydrator.rs:140-160`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/candidate_hydrators/vf_candidate_hydrator.rs#L140-L160) · symbol `should_drop_ancillary, AncillaryVFFilter, AncestorVideoFilter, VideoCarouselFilter` · commit `07d159b`
- **Status:** verified
- **Mechanism:** AncillaryVFFilter drops a candidate flagged drop_ancillary_posts, which the VF hydrator sets when any non-tombstoned ancestor or the quoted post has a drop-type visibility action. Ancestors and quoted posts are always evaluated at the out-of-network safety level (TimelineHomeRecommendations), even for in-network candidates. AncestorVideoFilter drops posts whose ancestor has video when the request excludes video; VideoCarouselFilter runs last and splits candidates for a video carousel.
- **Relevance to an account:** Replying to or quoting a post that carries out-of-network drop labels can make the reply or quote ineligible for For You, even for the author's own followers.
- **Observable proxy:** Partial: quoted/parent posts are public; their visibility labels are not.
- **Limitations:** Filter in home-mixer/filters/ancillary_vf_filter.rs; the level assignment is in vf_candidate_hydrator.rs lines 70-85. Tombstone handling of ancestors was not traced in detail.

### D15 — No time-decay term in the weighted score

- **Location:** [`xai-value-model/scoring.rs:69-140`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L69-L140) · symbol `compute_weighted_score` · commit `07d159b`
- **Status:** verified
- **Mechanism:** The weighted score is a sum of head predictions times weights (favorite, reply, repost, clicks, dwell, shares, follow, negative feedback, etc.); none of the terms is a function of post age. Freshness is enforced by hard cutoffs (48h AgeFilter, D02) and by whatever the prediction model learns.
- **Relevance to an account:** There is no explicit half-life multiplier on the final score in this code. Recency can still matter if the Phoenix model's predictions depend on post age, which this finding does not establish.
- **Observable proxy:** Post timestamps are public.
- **Limitations:** Phoenix model inputs were not audited for age features. Cold-start lift (D19) has its own age cap.

### D16 — Popular-posts retrieval normalises views with an 8-hour half-life

- **Location:** [`home-mixer/util/popular_posts.rs:36-53`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/util/popular_posts.rs#L36-L53) · symbol `SelectionConfig, quality` · commit `07d159b`
- **Status:** verified
- **Mechanism:** A separate PopularPostsSource (enabled by default) selects up to 500 posts from the last 24 hours, at most 5 per author, by a quality score that divides views by an exponential saturation curve with an 8-hour half-life and a 0.5-hour age floor, i.e. favouring view velocity.
- **Relevance to an account:** Posts that gather views quickly are more likely to enter this candidate pool for out-of-network viewers. This affects retrieval only; the post is then scored like any other candidate.
- **Observable proxy:** View counts and post age are public for many posts.
- **Limitations:** half_life_hours can be overridden by a CLI flag (home-mixer/main.rs, default 8.0).

### D17 — Debias payload with has_url is sent to vm-ranker only when enabled (default off)

- **Location:** [`home-mixer/scorers/vm_ranker_request.rs:17-24`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/vm_ranker_request.rs#L17-L24) · symbol `RequestShape::from_query` · commit `07d159b`
- **Status:** verified
- **Mechanism:** When VMRankerSendDebiasInputs is true and the request has no cached posts, home-mixer adds per-candidate content features to the vm-ranker request: has_video, video duration, has_photo, media count, weighted text length, newline count and has_url (external URLs in text). The parameter defaults to false, and the value model shown here does not read these fields.
- **Relevance to an account:** No URL penalty appears in the published scoring formula; has_url is only an experimental payload field whose use by vm-ranker is not shown.
- **Observable proxy:** Presence of links in post text is public.
- **Limitations:** Default from home-mixer/params/param.rs lines 502-507. How vm-ranker experiments consume experiment_payload is not in this repo.

### D18 — Embedding-based similarity de-duplication (DPP, video carousel)

- **Location:** [`home-mixer/params/param.rs:1165-1175`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L1165-L1175) · symbol `EnableVideoCarouselEmbeddingDedupe, VideoCarouselEmbeddingDedupeThreshold` · commit `07d159b`
- **Status:** verified
- **Mechanism:** Content similarity is handled with embeddings rather than text matching in this pipeline: DPP (D12) penalises cosine-similar posts, and the video carousel de-duplicates by author and by embedding similarity above a 0.72 threshold (both enabled by default).
- **Relevance to an account:** Near-duplicate content competing for the same viewer is likely to be thinned out; an author's own similar posts compete with each other.
- **Observable proxy:** Partial: content of posts is public; embeddings are not.
- **Limitations:** The embedding models are not reproduced here.

### D19 — Cold-start lift for low-impression posts from smaller authors

- **Location:** [`home-mixer/scorers/author_cold_start.rs:188-193`](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/author_cold_start.rs#L188-L193) · symbol `cold_start_base_eligible, apply_cold_start` · commit `07d159b`
- **Status:** verified
- **Mechanism:** AuthorColdStart can lift one eligible candidate per request to the score at a randomly chosen target rank. Eligible posts are originals (not replies or reposts) from authors with <= 50,000 followers, younger than 7,200 s, with fewer than 200 home impressions, within an allowed position range, and in the viewer's experiment arm's author corpus.
- **Relevance to an account:** Small accounts' fresh original posts can get an exploratory boost early in their life; replies and reposts are not eligible.
- **Observable proxy:** Follower count, post type and post age are public; home impressions are partly visible via view counts.
- **Limitations:** Defaults from home-mixer/params/param.rs (lines 539-581); slot range and corpus bucketing are experiment-controlled.


## Common claims checked against the repository

| ID | Claim | Verdict | Explanation |
|---|---|---|---|
| K01 | X uses a TweepCred-style reputation score for accounts | **partially supported** | There is no "TweepCred" in this repo, but user-cred-v2 computes a PageRank-based per-account score (0-100) from follow edges, with premium accounts and like/repost engagement in the teleport set. In this code the score is consumed by spam/abuse systems as an exemption threshold, not by the For You value model. [user-cred-v2/UserCredV2.scala:9](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2.scala#L9-L20) [botmaker-rules/scarecrow/derived-feature/IsHighPageRankUser.df:1](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/botmaker-rules/scarecrow/derived-feature/IsHighPageRankUser.df#L1-L28) [xai-value-model/inputs.rs:3](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/inputs.rs#L3-L17) |
| K02 | TweepCred below 65 limits an account to 3 tweets being considered | **not found in repo** | No TweepCred, no threshold of 65, and no per-author cap of 3 tweets were found in the published ranking code. The user-cred thresholds visible here are 54 (scarecrow high-PageRank), 50.0 (abuse-enforcement skip) and 66 (Grox reply-label exemption), and they gate spam labelling, not tweet counts. Absence here does not prove absence in production. [abuse-enforcement-service/service-lib/rules/enforcement_user.yaml:32](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/abuse-enforcement-service/service-lib/rules/enforcement_user.yaml#L32-L38) [grox/flows/reply_spam/constants.py:9](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/reply_spam/constants.py#L9) |
| K03 | Posts with external links get a 30-50% reach penalty | **not found in repo** | The published weighted score has no link-penalty term; open_link is a positive head (weight 0.2). A has_url content feature exists only in an experimental debias payload that is off by default and is not read by the published value model. Link-specific effects could still arise from model predictions or URL-quality spam rules, which this does not rule out. [home-mixer/params/param.rs:373](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L373) [home-mixer/params/param.rs:502](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L502-L507) [home-mixer/models/content_features.rs:8](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/models/content_features.rs#L8-L20) |
| K04 | Using 3 or more hashtags gets a post penalised | **not found in repo** | No hashtag count or hashtag penalty appears in home-mixer, vm-ranker or xai-value-model; hashtags appear only in SimClusters entity extraction, muted keyword handling, ads tests and Agatha data loaders. This is absent from the public ranking code, not proven absent in production.  |
| K05 | Premium/verified accounts get a 4x in-network and 2x out-of-network boost | **not found in repo** | No verification or premium multiplier appears in the For You scoring code; the only post-fusion multipliers are author diversity and the out-of-network factor. Premium status does appear in user-cred-v2 as the uniform teleport set, and gray/grey-badge status exempts accounts from some spam labels, which are indirect effects, not a ranking boost. [xai-value-model/scoring.rs:12](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L12-L26) [user-cred-v2/UserCredV2App.scala:173](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/user-cred-v2/UserCredV2App.scala#L173-L175) |
| K06 | One report cancels out 468 likes | **contradicted** | The ratio comes from ReportWeight -234 vs a favorite weight of 0.5, but the weights multiply each viewer's predicted probabilities, not raw counts, and the code comment explicitly calls this reading incorrect. The current home-mixer favorite default is 0.66, so even the ratio differs by file. [home-mixer/params/param.rs:320](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L320-L330) [home-mixer/params/param.rs:457](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L457) |
| K07 | Replies are worth 27x a like | **contradicted** | Current defaults are ReplyWeight 5.0 and FavoriteWeight 0.66 in home-mixer (0.5 in vm-ranker), i.e. roughly 7.6x-10x, and they weight predicted probabilities rather than counts. The 27x figure may describe the 2023 heavy ranker, which is not in this repo. [home-mixer/params/param.rs:345](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L345-L346) [vm-ranker/params.rs:3](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/params.rs#L3-L4) |
| K08 | A reply the author engages with is worth 75x (or 150x) a like | **not found in repo** | The current Phoenix heads have no "reply engaged by author" prediction; the weighted score sums the listed heads only. These numbers come from the 2023 heavy-ranker configuration, which is not part of this repository. [xai-value-model/phoenix_scores.rs:1](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/phoenix_scores.rs#L1-L31) |
| K09 | Bookmarks are worth 20x a like | **not found in repo** | There is no bookmark prediction head or bookmark weight in the scoring code; bookmarks appear as viewer engagement-history signals and candidate counts. A weight of 20.0 exists for share_via_copy_link, which is a different action. [xai-value-model/phoenix_scores.rs:1](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/phoenix_scores.rs#L1-L31) [home-mixer/params/param.rs:388](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L388-L393) [home-mixer/models/engagement_signals.rs:20](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/models/engagement_signals.rs#L20-L26) |
| K10 | A good click / dwell (2+ minutes) is worth 10-11x a like | **contradicted** | Current defaults are ClickWeight 0.3, DwellWeight 0.05, ContDwellTimeWeight 0.006 and ContClickDwellTimeWeight 0.4 (per unit of predicted dwell time); there is no "good click" head with weight 10-11. The figure appears to come from the 2023 heavy ranker, not this code. [home-mixer/params/param.rs:372](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L372) [home-mixer/params/param.rs:432](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L432-L437) |
| K11 | Scores decay with a 6-hour half-life | **contradicted** | The published weighted score has no time-decay term; freshness is enforced by a hard 48-hour age cutoff. The only half-life found in home-mixer is 8 hours, used to normalise views in the popular-posts retrieval source, not to decay ranking scores. Recency could still be learned implicitly by the prediction model. [xai-value-model/scoring.rs:69](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L69-L140) [home-mixer/params/config.rs:40](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/config.rs#L40) [home-mixer/util/popular_posts.rs:36](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/util/popular_posts.rs#L36-L46) |
| K12 | The first 30 minutes decide a post's distribution | **not found in repo** | No 30-minute decision window exists in the ranking code. Related time windows are the cold-start lift for posts under 7,200 s old with fewer than 200 home impressions, a 0.5-hour age floor in popular-posts view normalisation, and the 48-hour age cutoff. Absence here is not proof of absence in production. [home-mixer/params/param.rs:562](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L562-L567) [home-mixer/util/popular_posts.rs:36](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/util/popular_posts.rs#L36-L46) |
| K13 | An Author Diversity Scorer throttles accounts that post frequently | **partially supported** | An author-diversity multiplier exists, but it applies within a single viewer's candidate set: the k-th additional post from the same author is multiplied by 0.75 * 0.5^k + 0.25. It does not count how often an account posts overall. [xai-value-model/scoring.rs:183](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L183-L204) [vm-ranker/params.rs:175](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/params.rs#L175-L186) |
| K14 | Grok reads every post and down-ranks negative sentiment | **not found in repo** | Grox runs LLM/VLM classifiers for safety, spam, reply spam and a "banger" screen, but no sentiment score or sentiment term appears in the ranking formula, and Grox flows are gated (e.g. multimodal embedding uses an adaptive minimum like count starting at 20,000). Prompts are withheld, so the exact criteria cannot be checked. [grox/flows/ptos/prompts.py:11](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/ptos/prompts.py#L11) [grox/flows/mm_emb/adaptive_min_fav.py:6](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/grox/flows/mm_emb/adaptive_min_fav.py#L6-L19) |
| K15 | Spelling errors cause a deboost | **not found in repo** | No spelling or typo check appears in the ranking or filtering code. Repo-wide regex matches are unrelated substrings (e.g. "tyPo" inside identifiers in a Grox file, a CLI-parsing test name in Phoenix). Not proof of absence in production; Grox prompts are withheld.  |
| K16 | Mass unfollowing triggers a 3-month shadowban | **not found in repo** | No unfollow-based penalty or 3-month restriction appears in home-mixer, visibility-filtering or the published enforcement rules. bdsm's FollowBot head targets automated follow behaviour, but its thresholds are redacted and no duration like 3 months is published. [bdsm/runtime/sink_policy.yaml:15](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/bdsm/runtime/sink_policy.yaml#L15-L20) |
| K17 | SimClusters has about 145k communities | **partially supported** | The SimClusters code refers to a model version named Model20M145K2020, which is consistent with ~145K clusters, but no explicit cluster count constant was found. SimClusters is used in home-mixer as one retrieval source. [simclusters/simclusters_v2/summingbird/common/SimClustersProfile.scala:145](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/simclusters/simclusters_v2/summingbird/common/SimClustersProfile.scala#L145) |
| K18 | Video posts get 10x reach | **not found in repo** | No video multiplier exists in the scoring code. Video heads carry small weights by default (video_open 0.02 in home-mixer, video quality view 0.0). Video can still affect predicted engagement and has dedicated carousel and immersive surfaces, so effects on reach are not ruled out. [home-mixer/params/param.rs:366](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L366-L371) [home-mixer/params/param.rs:380](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L380) |
| K19 | Replies between mutual followers get boosted | **partially supported** | A bidirectional-follow boost exists (default +15 on the reply weight), but it applies to original posts from authors the viewer mutually follows, raising the weight on the predicted probability that the viewer replies. Replies and reposts are explicitly excluded from eligibility. [xai-value-model/inputs.rs:19](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/inputs.rs#L19-L23) [home-mixer/params/param.rs:347](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L347-L352) [docs/BIDIRECTIONAL_BOOST_CHANGE.md:5](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/docs/BIDIRECTIONAL_BOOST_CHANGE.md#L5) |
| K20 | Profile clicks are a major ranking signal | **contradicted** | ProfileClickWeight defaults to 0.0 and profile-visit seconds are weighted 0.0 (home-mixer hard-codes it to 0.0), so predicted profile clicks do not add to the published weighted score at defaults. Experiments could set non-zero values. [home-mixer/params/param.rs:374](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L374-L379) [home-mixer/scorers/value_model.rs:38](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/scorers/value_model.rs#L38-L40) |
| K21 | Out-of-network posts are down-weighted | **supported** | Out-of-network candidates (and, by default, in-network replies and reposts) are multiplied by effective_oon_weight, which defaults to OonWeightFactor 0.75 (0.5 for topic requests). Out-of-network posts also face extra visibility drop rules. [xai-value-model/scoring.rs:206](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L206-L215) [vm-ranker/params.rs:211](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/vm-ranker/params.rs#L211-L216) |
| K22 | Posting too often cannibalises your own reach | **partially supported** | Within one viewer's feed, repeated posts by the same author are discounted (author diversity) and only one post per conversation is kept, so several simultaneous posts compete with each other for that viewer. Nothing in the code penalises posting frequency globally or across viewers. [xai-value-model/scoring.rs:183](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/xai-value-model/scoring.rs#L183-L185) [home-mixer/filters/dedup_conversation_filter.rs:19](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/filters/dedup_conversation_filter.rs#L19-L36) |
| K23 | Mass blocking/reporting by bad actors suppresses an account's reach | **unverifiable** | For ranking, the code comment states that weights apply to each viewer's predicted probabilities and that only actions on posts served in Home Timeline count, so coordinated reports mainly affect similar users. However, Agatha computes account-level blocks-per-fav and reports-per-fav rates that feed account models, and the thresholds turning those into labels are not published. [home-mixer/params/param.rs:332](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/home-mixer/params/param.rs#L332-L344) [agatha/scalding/labels/rate_based_labels/RateBasedLabels.scala:80](https://github.com/xai-org/x-algorithm/blob/07d159b69109f069c85f84d39dd38e38adc040f0/agatha/scalding/labels/rate_based_labels/RateBasedLabels.scala#L80-L90) |
