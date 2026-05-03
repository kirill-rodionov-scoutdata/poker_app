from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

from poker.aggregator import StatAggregator
from poker.models import NormalizedHand, Source
from poker.normalizer import HandNormalizer
from poker.parser import HandParser

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def main() -> None:
    gto_directory = Path(os.environ["GTO_DATA_DIR"])
    population_directory = Path(os.environ["POPULATION_DATA_DIR"])

    parser = HandParser()
    normalizer = HandNormalizer()

    all_parsed = []
    for file_path in sorted(gto_directory.glob("*.txt"))[:2]:
        hands = parser.parse_file(file_path, Source.GTO)
        all_parsed.extend(hands)
        logger.info("parsed %s: %d hands", file_path.name, len(hands))

    for file_path in sorted(population_directory.glob("*.txt"))[:5]:
        hands = parser.parse_file(file_path, Source.POPULATION)
        all_parsed.extend(hands)
        logger.info("parsed %s: %d hands", file_path.name, len(hands))

    logger.info("total parsed: %d", len(all_parsed))

    all_normalized: list[NormalizedHand] = []
    for parsed_hand in all_parsed:
        all_normalized.extend(normalizer.normalize(parsed_hand))

    logger.info("total normalized (flop HU BB-perspective): %d", len(all_normalized))

    _log_breakdown(all_normalized)

    stat_catalog = json.loads(Path("stat_catalog.json").read_text())
    aggregator = StatAggregator()
    results = aggregator.aggregate(all_normalized, stat_catalog)

    logger.info("--- stat results (sample) ---")
    shown = 0
    for result in results:
        if shown >= 3:
            break
        pop = result.population
        gto = result.gto
        if pop.status == "NO_DATA" and gto.status == "NO_DATA":
            continue
        logger.info(
            "%s | %s | pop: value=%.4f sample=%d status=%s | gto: value=%.4f sample=%d status=%s | delta=%s",
            result.stat_id,
            result.label,
            pop.value if pop.value is not None else 0.0,
            pop.sample,
            pop.status,
            gto.value if gto.value is not None else 0.0,
            gto.sample,
            gto.status,
            f"{result.delta:.4f}" if result.delta is not None else "N/A",
        )
        shown += 1

    logger.info("--- full output (first 3 results with data) ---")
    shown = 0
    for result in results:
        if shown >= 3:
            break
        if result.population.status == "NO_DATA" and result.gto.status == "NO_DATA":
            continue
        logger.info("%s", json.dumps(result.to_dict(), indent=2))
        shown += 1


def _log_breakdown(normalized_hands: list[NormalizedHand]) -> None:
    def _str_keys(counter: Counter) -> dict:
        return {str(k): v for k, v in counter.items()}

    logger.info("spots: %s", _str_keys(Counter(h.spot for h in normalized_hands)))
    logger.info("formations: %s", _str_keys(Counter(h.formation for h in normalized_hands)))
    logger.info("roles: %s", _str_keys(Counter(h.hero_role for h in normalized_hands)))
    logger.info("top lines: %s", dict(Counter(h.line for h in normalized_hands).most_common(10)))


if __name__ == "__main__":
    main()
