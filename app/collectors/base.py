from dataclasses import dataclass
from typing import Protocol

@dataclass(frozen=True)
class Candidate:
    value: str
    kind: str
    vendor: str
    category: str
    source: str
    confidence: int
    evidence: str | None = None

class Collector(Protocol):
    name: str
    async def collect(self) -> list[Candidate]: ...
