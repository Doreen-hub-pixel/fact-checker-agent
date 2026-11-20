import pytest

from core.trust import confidence_assessment, source_diversity


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.8, "High confidence"),
        (0.5, "Medium confidence"),
        (0.49, "Low confidence"),
    ],
)
def test_confidence_assessment_uses_expected_bands(score, expected):
    level, _, normalized_score = confidence_assessment(score)

    assert level == expected
    assert normalized_score == score


@pytest.mark.parametrize("score", [None, True, float("nan"), 1.1])
def test_confidence_assessment_marks_invalid_scores_unavailable(score):
    level, _, normalized_score = confidence_assessment(score)

    assert level == "Unavailable"
    assert normalized_score is None


def test_source_diversity_counts_domain_suffixes_and_other_urls():
    counts = source_diversity(
        [
            "https://research.example.edu/paper",
            "https://agency.gov/report",
            "https://group.org/about",
            "https://publisher.com/story",
            "https://example.net/page",
            "not a URL",
        ]
    )

    assert counts == {
        "Academic (.edu)": 1,
        "Government (.gov)": 1,
        "Organization (.org)": 1,
        "Commercial (.com)": 1,
        "Other": 2,
    }
