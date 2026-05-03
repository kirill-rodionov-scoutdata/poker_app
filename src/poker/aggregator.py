from __future__ import annotations

import logging

from poker.models import NormalizedHand, Source, SourceResult, StatResult, StatStatus
from poker.stat_engine import StatComputer

logger = logging.getLogger(__name__)


class StatAggregator:
    def __init__(self) -> None:
        self._stat_computer = StatComputer()

    def aggregate(
        self,
        hands: list[NormalizedHand],
        stat_catalog: list[dict],
    ) -> list[StatResult]:
        population_hands = [h for h in hands if h.source == Source.POPULATION]
        gto_hands = [h for h in hands if h.source == Source.GTO]

        return [
            self._compute_stat_result(stat, population_hands, gto_hands)
            for stat in stat_catalog
        ]

    def _compute_stat_result(
        self,
        stat: dict,
        population_hands: list[NormalizedHand],
        gto_hands: list[NormalizedHand],
    ) -> StatResult:
        min_sample = stat.get("minSample", 30)
        stat_id = stat.get("id", "unknown")

        pop_num, pop_den = self._stat_computer.compute(stat, population_hands)
        gto_num, gto_den = self._stat_computer.compute(stat, gto_hands)

        self._sanity_check(stat_id, "population", pop_num, pop_den)
        self._sanity_check(stat_id, "gto", gto_num, gto_den)

        pop_result = self._build_source_result(pop_num, pop_den, min_sample)
        gto_result = self._build_source_result(gto_num, gto_den, min_sample)

        delta: float | None = None
        if pop_result.value is not None and gto_result.value is not None:
            delta = round(pop_result.value - gto_result.value, 4)

        return StatResult(
            stat_id=stat_id,
            label=stat.get("label", ""),
            population=pop_result,
            gto=gto_result,
            delta=delta,
        )

    def _build_source_result(
        self, numerator: int, denominator: int, min_sample: int
    ) -> SourceResult:
        if denominator == 0:
            return SourceResult(value=None, sample=0, status=StatStatus.NO_DATA)

        value = round(numerator / denominator, 4)

        if denominator < min_sample:
            return SourceResult(value=value, sample=denominator, status=StatStatus.LOW_SAMPLE)

        return SourceResult(value=value, sample=denominator, status=StatStatus.OK)

    def _sanity_check(
        self, stat_id: str, source: str, numerator: int, denominator: int
    ) -> None:
        if numerator > denominator:
            logger.error(
                "sanity check failed stat=%s source=%s numerator=%d > denominator=%d",
                stat_id, source, numerator, denominator,
            )
