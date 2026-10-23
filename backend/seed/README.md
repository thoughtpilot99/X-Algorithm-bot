# Seed data for a fresh database

- `labels/*.jsonl`: model-reviewed topic, hook, narrative and reply-category labels from the first audit (2026-10-23). They hold tweet ids and labels only, with no post text. Import them with `xaudit import-labels --folder seed/labels`.
- `rewrites/*.json`: the drafted post rewrites shown in Reports A and B. Copy them to `data/labels/rewrites/`.

The monitoring workflow uses both on its first run, so CI keeps the reviewed labels rather than falling back to the heuristic labeller.
