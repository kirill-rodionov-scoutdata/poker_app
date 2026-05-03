import json
from pathlib import Path

import pytest

from poker.models import Source
from poker.normalizer import HandNormalizer
from poker.parser import HandParser

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POPULATION_DIR = _REPO_ROOT / "Test base" / "Тестовая база данные популяции"
_STAT_CATALOG_PATH = _REPO_ROOT / "stat_catalog.json"

if not _POPULATION_DIR.exists():
    raise FileNotFoundError(
        f"Directory with population test data not found: {_POPULATION_DIR}\n"
        "Please make sure 'Test base/Тестовая база данные популяции' exists in the repository root."
    )

if not any(_POPULATION_DIR.glob("*.txt")):
    raise FileNotFoundError(
        f"No .txt files found in population directory: {_POPULATION_DIR}\n"
        "Please add hand history files to the test directory."
    )

if not _STAT_CATALOG_PATH.exists():
    raise FileNotFoundError(
        f"Stat catalog file not found: {_STAT_CATALOG_PATH}\n"
        "Please make sure 'stat_catalog.json' exists in the repository root."
    )


@pytest.fixture(scope="module")
def population_parsed_hands():
    parser = HandParser()
    all_parsed = []
    for path in sorted(_POPULATION_DIR.glob("*.txt"))[:30]:
        all_parsed.extend(parser.parse_file(path, Source.POPULATION))
    return all_parsed


@pytest.fixture(scope="module")
def population_hands(population_parsed_hands):
    normalizer = HandNormalizer()
    result = []
    for hand in population_parsed_hands:
        result.extend(normalizer.normalize(hand))
    return result


@pytest.fixture(scope="module")
def stat_catalog():
    return json.loads(_STAT_CATALOG_PATH.read_text(encoding="utf-8"))
