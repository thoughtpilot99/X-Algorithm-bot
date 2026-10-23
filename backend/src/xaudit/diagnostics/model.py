"""The diagnostic record every engine output is reduced to."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

EvidenceClass = Literal[
    "repo_verified",            # read directly in the X algorithm repository
    "account_observed",         # directly observed post/reply data
    "statistical_association",  # computed comparison/regression, not causal
    "hypothesis",               # reasonable but untested explanation
    "unsupported",              # common claim not supported by repo or data
    "insufficient",             # cannot be assessed with available data
]
Confidence = Literal["high", "medium", "low", "insufficient evidence"]


class Evidence(BaseModel):
    kind: Literal["post", "metric", "comparison", "finding", "data_gap"]
    ref: str  # tweet_id, metric name, comparison key, finding id
    label: str
    value: float | str | None = None
    url: str | None = None
    evidence_class: EvidenceClass = "account_observed"


class Diagnostic(BaseModel):
    id: str
    handle: str
    issue: str
    status: Literal["supported", "mixed", "not_supported", "insufficient"]
    observation: str
    evidence: list[Evidence] = Field(default_factory=list)
    algo_links: list[str] = Field(default_factory=list)  # finding ids
    algo_connection: str = ""
    alternatives: list[str] = Field(default_factory=list)
    confidence: Confidence
    impact: str
    recommendation: str
    validation: str
    evidence_class: EvidenceClass
    # Ranking inputs, 0..1 each (see recommend.rank_root_causes).
    evidence_strength: float = 0.0
    business_relevance: float = 0.5
    likely_impact: float = 0.5
    ease_of_testing: float = 0.5
    example_posts: list[str] = Field(default_factory=list)
    confounders: list[str] = Field(default_factory=list)
    success_criteria: str = ""

    @property
    def priority(self) -> float:
        conf = {"high": 1.0, "medium": 0.7, "low": 0.4, "insufficient evidence": 0.0}[self.confidence]
        return round(
            0.30 * self.evidence_strength + 0.20 * self.business_relevance + 0.25 * self.likely_impact
            + 0.10 * self.ease_of_testing + 0.15 * conf, 4)
