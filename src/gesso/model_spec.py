"""Parse `--model` / provider selection for LLM backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Provider = Literal["perplexity", "kimi"]

DEFAULT_PERPLEXITY_MODEL = "sonar-pro"
DEFAULT_KIMI_MODEL = "kimi-k2.6"


@dataclass(frozen=True)
class ResolvedModel:
    provider: Provider
    api_model: str


def resolve_model(flag: str) -> ResolvedModel:
    """
    Accept provider aliases, optional provider:model_id, or bare API model id when unambiguous.

    Examples: perplexity, pplx, kimi, moonshot, perplexity:sonar-pro, kimi:kimi-k2.6, kimi-k2.6
    """
    s = flag.strip()
    if not s:
        return ResolvedModel("perplexity", DEFAULT_PERPLEXITY_MODEL)

    lower = s.lower()
    if ":" in lower:
        prov, mid = s.split(":", 1)
        prov_l = prov.strip().lower()
        model_id = mid.strip()
        if prov_l in {"perplexity", "pplx"}:
            return ResolvedModel(
                "perplexity",
                model_id or DEFAULT_PERPLEXITY_MODEL,
            )
        if prov_l in {"kimi", "moonshot"}:
            return ResolvedModel("kimi", model_id or DEFAULT_KIMI_MODEL)
        raise SystemExit(
            f"[ERROR] Unknown provider in --model {flag!r} "
            "(use perplexity or kimi before ':')"
        )

    if lower in {"perplexity", "pplx"}:
        return ResolvedModel("perplexity", DEFAULT_PERPLEXITY_MODEL)
    if lower in {"kimi", "moonshot"}:
        return ResolvedModel("kimi", DEFAULT_KIMI_MODEL)

    # Bare model ids
    if lower.startswith("kimi-") or lower.startswith("moonshot-"):
        return ResolvedModel("kimi", s.strip())
    if lower.startswith("sonar"):
        return ResolvedModel("perplexity", s.strip())

    raise SystemExit(
        f"[ERROR] Unrecognized --model {flag!r}. "
        "Use perplexity, kimi, provider:model_id (e.g. kimi:kimi-k2.6), or a bare model id "
        "like sonar-pro or kimi-k2.6."
    )
