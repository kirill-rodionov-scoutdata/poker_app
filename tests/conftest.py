from __future__ import annotations

import json
from pathlib import Path

import pytest

from poker.models import Source
from poker.normalizer import HandNormalizer
from poker.parser import HandParser

_REPO_ROOT = Path(__file__).resolve().parent.parent
_POPULATION_DIR = _REPO_ROOT / "Test base" / "Тестовая база данные популяции"
_STAT_CATALOG_PATH = _REPO_ROOT / "stat_catalog.json"


@pytest.fixture(scope="module")
def population_hands():
    parser = HandParser()
    normalizer = HandNormalizer()
    all_parsed = []
    for path in sorted(_POPULATION_DIR.glob("*.txt"))[:30]:
        all_parsed.extend(parser.parse_file(path, Source.POPULATION))
    result = []
    for hand in all_parsed:
        result.extend(normalizer.normalize(hand))
    return result


@pytest.fixture(scope="module")
def stat_catalog():
    return json.loads(_STAT_CATALOG_PATH.read_text(encoding="utf-8"))
