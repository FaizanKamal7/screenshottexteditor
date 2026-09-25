"""Bootstrap, linearized SE and Holm unit tests (hand-computed expectations)."""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import bootstrap as B  # noqa: E402

METHODS = ("percentile", "bca", "boot_t", "log_t")


def test_point_estimate_is_pooled_ratio_for_every_method():
    num = np.array([1.0, 0.0, 3.0, 0.0, 2.0, 1.0])
    den = np.array([10.0, 10.0, 20.0, 60.0, 30.0, 70.0])
    for m in METHODS:
        ci = B.ratio_ci(num, den, ["m", "m", "m", "d", "d", "d"], method=m, b=999)
        assert ci["point"] == pytest.approx(7 / 200)       # (1+0+3+0+2+1) / 200
        assert ci["lo"] <= ci["point"] <= ci["hi"], m


def test_linearized_se_matches_hand_computation():
    # One stratum, equal lengths: R = mean rate, u_t = (e_t - R l_t) / L,
    # var = n/(n-1) * Σ (u_t - ū)^2. e = [1, 3], l = [10, 10] -> R = 0.2, L = 20,
    # u = [(1-2)/20, (3-2)/20] = [-0.05, 0.05], var = 2 * (0.0025 + 0.0025) = 0.01 -> se = 0.1
    R, se = B.ratio_and_se(np.array([1.0, 3.0]), np.array([10.0, 10.0]), [slice(0, 2)])
    assert R == pytest.approx(0.2) and se == pytest.approx(0.1)


def test_constant_rate_templates_give_zero_width():
    num = np.array([1.0, 2.0, 3.0, 4.0])
    ci = B.ratio_ci(num, num * 10, ["m", "m", "d", "d"], method="percentile", b=500)
    assert ci["lo"] == pytest.approx(0.1) and ci["hi"] == pytest.approx(0.1)


def test_paired_difference_identical_engines():
    num = np.array([1.0, 2.0, 0.0, 5.0])
    den = np.array([10.0, 20.0, 30.0, 40.0])
    for m in ("percentile", "bca", "boot_t"):
        d = B.paired_diff_ci(num, den, num, den, ["m", "m", "d", "d"], method=m, b=500)
        assert d["delta"] == 0.0 and d["p"] == 1.0, m


def test_boot_t_p_value_small_for_large_consistent_difference():
    rng = np.random.default_rng(0)
    den = rng.integers(500, 1500, size=40).astype(float)
    ea = np.round(den * 0.01)
    eb = np.round(den * 0.05)                        # engine B always ~5x worse
    d = B.paired_diff_ci(ea, den, eb, den, ["m"] * 20 + ["d"] * 20, method="boot_t", b=999)
    assert d["delta"] < 0 and d["hi"] < 0 and d["p"] < 0.01


def test_rate_ratio_point_interval_and_p():
    rng = np.random.default_rng(1)
    den = rng.integers(500, 1500, size=40).astype(float)
    ea = np.round(den * 0.01) + rng.integers(0, 3, size=40)
    eb = np.round(den * 0.04) + rng.integers(0, 3, size=40)
    ff = ["m"] * 20 + ["d"] * 20
    r = B.rate_ratio_ci(ea, den, eb, den, ff, symmetric=True, b=999)
    assert r["ratio"] == pytest.approx((ea.sum() / den.sum()) / (eb.sum() / den.sum()))
    assert r["lo"] < r["ratio"] < r["hi"] < 1.0      # A clearly better: whole interval below 1
    assert r["p"] < 0.01


def test_rate_ratio_undefined_when_a_rate_is_zero():
    den = np.full(4, 100.0)
    r = B.rate_ratio_ci(np.zeros(4), den, np.array([1.0, 2.0, 1.0, 3.0]), den, ["m", "m", "d", "d"], b=99)
    assert r["undefined"] is True


def test_symmetric_difference_interval_is_symmetric():
    rng = np.random.default_rng(2)
    den = rng.integers(500, 1500, size=40).astype(float)
    ea = np.round(den * 0.02) + rng.integers(0, 4, size=40)
    eb = np.round(den * 0.03) + rng.integers(0, 4, size=40)
    d = B.diff_ci_sym(ea, den, eb, den, ["m"] * 20 + ["d"] * 20, b=999)
    assert d["hi"] - d["delta"] == pytest.approx(d["delta"] - d["lo"])


def test_holm_hand_computed():
    # p = [0.01, 0.04, 0.03, 0.20]; sorted 0.01, 0.03, 0.04, 0.20
    # adjusted: 4*0.01=0.04; max(0.04, 3*0.03=0.09)=0.09; max(0.09, 2*0.04=0.08)=0.09; max(0.09, 0.20)=0.20
    out = B.holm([0.01, 0.04, 0.03, 0.20])
    assert [round(o["p_holm"], 10) for o in out] == [0.04, 0.09, 0.09, 0.20]
    assert [o["reject"] for o in out] == [True, False, False, False]


def test_choose_method_applies_band_to_both_targets():
    study = {"band": [0.93, 0.97], "results": {
        "S": {"ratio:a": {"coverage": 0.95}, "diff:a": {"coverage": 0.94},
              "ratio:b": {"coverage": 0.95}, "diff:b": {"coverage": 0.92},
              "ratio:c": {"coverage": 0.95}}}}
    out = B.choose_method(study)
    assert out["chosen"] == "a"
    assert out["verdict"]["b"]["passes"] is False          # diff below band
    assert out["verdict"]["c"]["passes"] is False          # no paired-difference interval


def test_sample_size_rule_threshold():
    rule = B.sample_size_rule({"point": 0.004, "half_width": 0.01}, 2, 20)
    # projected = 0.01 * sqrt(2/20) = 0.0031623; threshold = max(0.002, 0.001) = 0.002 -> increase
    assert rule["projected_half_width_full"] == pytest.approx(0.0031623, rel=1e-4)
    assert rule["threshold"] == 0.002 and rule["increase_templates"] is True
