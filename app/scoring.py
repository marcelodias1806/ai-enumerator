from math import prod

SOURCE_CAPS = {
    "manual": 100,
    "vendor_docs": 95,
    "certificate_transparency": 45,
    "dns": 45,
    "github_official": 80,
    "observed_traffic": 70,
}

def combined_confidence(observations) -> int:
    """Combine independent evidence probabilistically, capped at 100.

    Each observation confidence is capped by source class so that CT/DNS alone
    cannot make a destination effectively 'certain'.
    """
    probs = []
    seen = set()
    for obs in observations:
        key = (obs.source_type.value, obs.source_ref)
        if key in seen:
            continue
        seen.add(key)
        cap = SOURCE_CAPS.get(obs.source_type.value, 50)
        score = min(obs.source_confidence, cap)
        probs.append(score / 100.0)
    if not probs:
        return 0
    combined = 1 - prod(1 - p for p in probs)
    return min(100, round(combined * 100))
