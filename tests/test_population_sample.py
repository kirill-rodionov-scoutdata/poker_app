from __future__ import annotations

from collections import Counter

from poker.models import Formation, HeroRole, PostflopPosition
from poker.stat_engine import compute_stat


def test_stat_001_population_sample_not_too_small(population_hands, stat_catalog):
    # Arrange
    stat = next(s for s in stat_catalog if s["id"] == "stat-001")

    # Act
    numerator, denominator = compute_stat(stat, population_hands)

    # Assert
    assert denominator > 50, f"stat-001 denominator={denominator}, expected >50"


def test_diagnostic_position_distribution(population_hands):
    # Arrange
    positions = Counter(h.hero_position for h in population_hands)

    # Act
    ip_count = positions.get(PostflopPosition.IP, 0)
    oop_count = positions.get(PostflopPosition.OOP, 0)

    # Assert
    assert ip_count > 0, (
        f"No IP hands found — hero_position is hardcoded to OOP in normalizer. "
        f"Distribution: {dict(positions)}"
    )
    assert oop_count > 0, f"No OOP hands found. Distribution: {dict(positions)}"


def test_diagnostic_role_distribution(population_hands):
    # Arrange
    roles = Counter(h.hero_role for h in population_hands)

    # Act
    pfr_count = roles.get(HeroRole.PFR, 0)
    pfc_count = roles.get(HeroRole.PFC, 0)

    # Assert
    assert pfr_count > 0, f"No PFR hands found. Roles: {dict(roles)}"
    assert pfc_count > 0, f"No PFC hands found. Roles: {dict(roles)}"


def test_diagnostic_formation_distribution(population_hands):
    # Arrange
    formations = Counter(h.formation for h in population_hands)

    # Act
    bb_btn_count = formations.get(Formation.BB_BTN, 0)
    bb_sb_count = formations.get(Formation.BB_SB, 0)

    # Assert
    assert bb_btn_count > 0, f"No BB_BTN hands found. Formations: {dict(formations)}"
    assert bb_sb_count > 0, f"No BB_SB hands found. Formations: {dict(formations)}"
