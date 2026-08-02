from __future__ import annotations

from copy import deepcopy


DEFAULT_BOOTSTRAP_FIDELITY_LEVEL = "methods_robustness_200"
PUBLISHED_UNCERTAINTY_BOOTSTRAP_N = 10000
TEST_FIXTURE_BOOTSTRAP_FIDELITY_LEVEL = "test_fixture_unregistered"

BOOTSTRAP_FIDELITY_LEVELS = {
    "methods_robustness_200": {
        "level": "methods_robustness_200",
        "n_bootstrap": 200,
        "published_equivalent": False,
        "published_n_bootstrap": PUBLISHED_UNCERTAINTY_BOOTSTRAP_N,
        "description": (
            "Runtime-bounded Methods robustness convention; not published-equivalent "
            "for SI uncertainty distributions."
        ),
    },
    "published_uncertainty_10000": {
        "level": "published_uncertainty_10000",
        "n_bootstrap": PUBLISHED_UNCERTAINTY_BOOTSTRAP_N,
        "published_equivalent": True,
        "published_n_bootstrap": PUBLISHED_UNCERTAINTY_BOOTSTRAP_N,
        "description": "Declared-fidelity SI uncertainty-distribution convention.",
    },
}


def fidelity_metadata(level: str) -> dict:
    if level not in BOOTSTRAP_FIDELITY_LEVELS:
        choices = ", ".join(sorted(BOOTSTRAP_FIDELITY_LEVELS))
        raise ValueError(f"Unknown bootstrap fidelity level {level!r}; expected one of: {choices}")
    return deepcopy(BOOTSTRAP_FIDELITY_LEVELS[level])


def n_bootstrap_for_level(level: str) -> int:
    return int(fidelity_metadata(level)["n_bootstrap"])


def validate_n_bootstrap_for_fidelity(level: str, n_bootstrap: int) -> dict:
    observed = int(n_bootstrap)
    if level == TEST_FIXTURE_BOOTSTRAP_FIDELITY_LEVEL:
        if observed < 1:
            raise ValueError("test fixture bootstrap fidelity requires positive n_bootstrap")
        return {
            "level": TEST_FIXTURE_BOOTSTRAP_FIDELITY_LEVEL,
            "n_bootstrap": observed,
            "published_equivalent": False,
            "published_n_bootstrap": PUBLISHED_UNCERTAINTY_BOOTSTRAP_N,
            "description": "Internal unit-test fixture fidelity; not a Paper 0 registered production level.",
        }
    meta = fidelity_metadata(level)
    expected = int(meta["n_bootstrap"])
    if observed != expected:
        raise ValueError(
            f"bootstrap fidelity {level!r} requires n_bootstrap={expected}; got {observed}"
        )
    return meta
