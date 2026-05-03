from poker.models import Street
from poker.stat_engine import compute_stat


def test_population_parse_sample_size(population_parsed_hands):
    # Arrange
    min_expected = 1000

    # Act
    parsed_count = len(population_parsed_hands)

    # Assert
    assert parsed_count >= min_expected, (
        f"Parsed too few hands: {parsed_count}, expected at least {min_expected}"
    )


def test_population_normalized_hands_are_flop_only(population_hands):
    # Arrange
    expected_street = Street.FLOP

    # Act
    distinct_streets = {hand.street for hand in population_hands}

    # Assert
    assert distinct_streets == {expected_street}, (
        f"Unexpected streets in normalized data: {distinct_streets}"
    )


def test_population_stat_numerator_not_greater_than_denominator(
    population_hands, stat_catalog
):
    # Arrange
    computed = [compute_stat(stat, population_hands) for stat in stat_catalog]

    # Act
    invalid_pairs = [
        (index, numerator, denominator)
        for index, (numerator, denominator) in enumerate(computed)
        if numerator < 0 or denominator < 0 or numerator > denominator
    ]

    # Assert
    assert not invalid_pairs, f"Found invalid (num, den) pairs: {invalid_pairs}"


def test_population_has_stats_with_nonzero_denominator(population_hands, stat_catalog):
    # Arrange
    min_nonzero_stats = 5

    # Act
    nonzero_count = sum(
        1 for stat in stat_catalog if compute_stat(stat, population_hands)[1] > 0
    )

    # Assert
    assert nonzero_count >= min_nonzero_stats, (
        f"Too few stats with non-zero denominator: {nonzero_count}, "
        f"expected at least {min_nonzero_stats}"
    )
