"""Cluster-bootstrap intervals, paired tests and Holm correction (PREREGISTRATION §7).

- Resampling unit: template; stratified by form factor (mobile / desktop resampled
  separately, with replacement); statistics recomputed from pooled units per resample
  (ratios of summed edits to summed reference characters).
- Interval methods: "percentile" (the original draft's method, kept for comparison),
  "bca", "boot_t" (studentized with a linearized stratified SE), "log_t" (ratio only).
  The method used for all confirmatory and descriptive intervals is chosen by
  choose_method() under the criterion in SELECTION_RULE, fixed before the study ran.
- Paired differences use the same resampled templates for both engines.
- Holm–Bonferroni at family-wise α.
"""

import numpy as np
from scipy import stats as st

SEED = 20260924
B_DEFAULT = 9_999

# Fixed before coverage_study() was first run (2026-09-24, PILOT C6 remediation):
SELECTION_RULE = (
    "Choose the method whose coverage for both the single-engine ratio and the paired "
    "difference is within [0.93, 0.97] in every scenario at 20 templates per stratum "
    "(2,000 simulations each, B=999). Among passing methods pick the smallest worst-case "
    "|coverage - 0.95|. If none passes, report that and do not relax the band."
)
C6_BAND = (0.93, 0.97)


# ---------------------------------------------------------------------------
# Core pieces
# ---------------------------------------------------------------------------

def _strata(form_factors) -> list[np.ndarray]:
    ff = np.asarray(form_factors)
    return [np.nonzero(ff == level)[0] for level in sorted(set(ff.tolist()))]


def _draws(strata, b, rng) -> np.ndarray:
    """(b, n) matrix of resampled template indices; stratum blocks are contiguous."""
    return np.concatenate([rng.choice(idx, size=(b, len(idx)), replace=True) for idx in strata], axis=1)


def _blocks(strata) -> list[slice]:
    out, start = [], 0
    for idx in strata:
        out.append(slice(start, start + len(idx)))
        start += len(idx)
    return out


def _var_from_influence(u: np.ndarray, blocks) -> np.ndarray:
    """Stratified with-replacement variance of a total from per-template influence values."""
    var = 0.0
    for sl in blocks:
        ub = u[..., sl]
        n_h = ub.shape[-1]
        if n_h < 2:
            continue
        var = var + n_h / (n_h - 1) * ((ub - ub.mean(axis=-1, keepdims=True)) ** 2).sum(axis=-1)
    return var


def ratio_and_se(e, l, blocks):
    """R = Σe/Σl and its linearized SE; e, l shaped (..., n)."""
    L = l.sum(axis=-1)
    R = e.sum(axis=-1) / L
    u = (e - R[..., None] * l) / L[..., None]
    return R, np.sqrt(_var_from_influence(u, blocks))


def diff_and_se(ea, la, eb, lb, blocks):
    """Δ = Ra - Rb and its linearized SE (paired: same templates)."""
    La, Lb = la.sum(axis=-1), lb.sum(axis=-1)
    Ra, Rb = ea.sum(axis=-1) / La, eb.sum(axis=-1) / Lb
    u = (ea - Ra[..., None] * la) / La[..., None] - (eb - Rb[..., None] * lb) / Lb[..., None]
    return Ra - Rb, np.sqrt(_var_from_influence(u, blocks))


def _jackknife(stat_fn, n):
    """Leave-one-template-out values of a statistic computed on index arrays."""
    idx = np.arange(n)
    return np.array([stat_fn(np.delete(idx, i)) for i in range(n)])


def _bca(theta_hat, boot, jack, alpha):
    prop = (np.sum(boot < theta_hat) + 0.5 * np.sum(boot == theta_hat)) / len(boot)
    prop = min(max(prop, 1e-6), 1 - 1e-6)
    z0 = st.norm.ppf(prop)
    d = jack.mean() - jack
    denom = 6.0 * (np.sum(d ** 2) ** 1.5)
    a = np.sum(d ** 3) / denom if denom > 0 else 0.0
    out = []
    for q in (alpha / 2, 1 - alpha / 2):
        zq = st.norm.ppf(q)
        adj = st.norm.cdf(z0 + (z0 + zq) / (1 - a * (z0 + zq)))
        out.append(np.quantile(boot, adj))
    return out


# ---------------------------------------------------------------------------
# Public interval / test functions
# ---------------------------------------------------------------------------

def ratio_ci(num, den, form_factors, method: str = "boot_t", b: int = B_DEFAULT, seed: int = SEED,
             alpha: float = 0.05) -> dict:
    """Interval for a pooled ratio (e.g. M1) from per-template sums."""
    num, den = np.asarray(num, float), np.asarray(den, float)
    strata = _strata(form_factors)
    order = np.concatenate(strata)
    num, den = num[order], den[order]
    blocks = _blocks(strata)
    rng = np.random.default_rng(seed)
    local = [np.arange(sl.start, sl.stop) for sl in blocks]
    draws = _draws(local, b, rng)
    R, se = ratio_and_se(num, den, blocks)
    Rb, seb = ratio_and_se(num[draws], den[draws], blocks)
    if method == "percentile":
        lo, hi = np.quantile(Rb, [alpha / 2, 1 - alpha / 2])
    elif method == "bca":
        jack = _jackknife(lambda ix: num[ix].sum() / den[ix].sum(), len(num))
        lo, hi = _bca(R, Rb, jack, alpha)
    elif method == "boot_t":
        ok = seb > 0
        if not ok.any() or se == 0:  # degenerate: identical rates in every template
            lo, hi = R, R
        else:
            t = (Rb[ok] - R) / seb[ok]
            tlo, thi = np.quantile(t, [alpha / 2, 1 - alpha / 2])
            lo, hi = R - thi * se, R - tlo * se
    elif method == "log_t":
        df = len(num) - len(blocks)
        if R <= 0:
            lo, hi = 0.0, 0.0
        else:
            h = st.t.ppf(1 - alpha / 2, df) * se / R
            lo, hi = R * np.exp(-h), R * np.exp(h)
    else:
        raise ValueError(method)
    lo, hi = max(0.0, float(lo)), float(hi)
    return {"point": float(R), "lo": lo, "hi": hi, "half_width": (hi - lo) / 2, "method": method, "b": b}


def paired_diff_ci(num_a, den_a, num_b, den_b, form_factors, method: str = "boot_t", b: int = B_DEFAULT,
                   seed: int = SEED, alpha: float = 0.05) -> dict:
    """Δ = ratio_a - ratio_b over the same template resamples, with a two-sided p-value."""
    arrs = [np.asarray(x, float) for x in (num_a, den_a, num_b, den_b)]
    strata = _strata(form_factors)
    order = np.concatenate(strata)
    ea, la, eb, lb = (x[order] for x in arrs)
    blocks = _blocks(strata)
    rng = np.random.default_rng(seed)
    local = [np.arange(sl.start, sl.stop) for sl in blocks]
    draws = _draws(local, b, rng)
    D, se = diff_and_se(ea, la, eb, lb, blocks)
    Db, seb = diff_and_se(ea[draws], la[draws], eb[draws], lb[draws], blocks)
    if method == "percentile":
        lo, hi = np.quantile(Db, [alpha / 2, 1 - alpha / 2])
        p = min(1.0, 2 * min(float(np.mean(Db <= 0)), float(np.mean(Db >= 0))))
    elif method == "bca":
        jack = _jackknife(lambda ix: ea[ix].sum() / la[ix].sum() - eb[ix].sum() / lb[ix].sum(), len(ea))
        lo, hi = _bca(D, Db, jack, alpha)
        p = min(1.0, 2 * min(float(np.mean(Db <= 0)), float(np.mean(Db >= 0))))
    elif method == "boot_t":
        ok = seb > 0
        if not ok.any() or se == 0:  # degenerate: no between-template variation at all
            return {"delta": float(D), "lo": float(D), "hi": float(D), "p": 1.0 if D == 0 else 0.0,
                    "method": method, "b": b}
        t = (Db[ok] - D) / seb[ok]
        tlo, thi = np.quantile(t, [alpha / 2, 1 - alpha / 2])
        lo, hi = D - thi * se, D - tlo * se
        if se > 0:
            t0 = D / se
            p = min(1.0, 2 * min(float(np.mean(t >= t0)), float(np.mean(t <= t0))))
        else:
            p = 1.0
    else:
        raise ValueError(method)
    return {"delta": float(D), "lo": float(lo), "hi": float(hi), "p": p, "method": method, "b": b}


def diff_ci_sym(num_a, den_a, num_b, den_b, form_factors, b: int = B_DEFAULT, seed: int = SEED,
                alpha: float = 0.05) -> dict:
    """Symmetric bootstrap-t interval for Δ: Δ ± q_{1-α}(|t*|) · SE, with p from |t*| >= |t0|."""
    arrs = [np.asarray(x, float) for x in (num_a, den_a, num_b, den_b)]
    strata = _strata(form_factors)
    order = np.concatenate(strata)
    ea, la, eb, lb = (x[order] for x in arrs)
    blocks = _blocks(strata)
    rng = np.random.default_rng(seed)
    draws = _draws([np.arange(sl.start, sl.stop) for sl in blocks], b, rng)
    D, se = diff_and_se(ea, la, eb, lb, blocks)
    Db, seb = diff_and_se(ea[draws], la[draws], eb[draws], lb[draws], blocks)
    ok = seb > 0
    if not ok.any() or se == 0:
        return {"delta": float(D), "lo": float(D), "hi": float(D), "p": 1.0 if D == 0 else 0.0,
                "method": "boot_t_sym", "b": b}
    t = np.abs((Db[ok] - D) / seb[ok])
    q = np.quantile(t, 1 - alpha)
    p = float(np.mean(t >= abs(D / se)))
    return {"delta": float(D), "lo": float(D - q * se), "hi": float(D + q * se), "p": min(1.0, p),
            "method": "boot_t_sym", "b": b}


def log_ratio_and_se(ea, la, eb, lb, blocks):
    """θ = log(Ra / Rb) and its linearized SE (paired). NaN where a rate is 0."""
    La, Lb = la.sum(axis=-1), lb.sum(axis=-1)
    Ra, Rb = ea.sum(axis=-1) / La, eb.sum(axis=-1) / Lb
    with np.errstate(divide="ignore", invalid="ignore"):
        theta = np.log(Ra) - np.log(Rb)
        u = (ea - Ra[..., None] * la) / (Ra * La)[..., None] - (eb - Rb[..., None] * lb) / (Rb * Lb)[..., None]
    return theta, np.sqrt(_var_from_influence(u, blocks))


def rate_ratio_ci(num_a, den_a, num_b, den_b, form_factors, symmetric: bool = False, b: int = B_DEFAULT,
                  seed: int = SEED, alpha: float = 0.05) -> dict:
    """Relative effect Ra/Rb: studentized bootstrap on the log scale, back-transformed.
    p tests H0: Ra = Rb (log ratio 0)."""
    arrs = [np.asarray(x, float) for x in (num_a, den_a, num_b, den_b)]
    strata = _strata(form_factors)
    order = np.concatenate(strata)
    ea, la, eb, lb = (x[order] for x in arrs)
    blocks = _blocks(strata)
    rng = np.random.default_rng(seed)
    draws = _draws([np.arange(sl.start, sl.stop) for sl in blocks], b, rng)
    th, se = log_ratio_and_se(ea, la, eb, lb, blocks)
    name = "log_boot_t_sym" if symmetric else "log_boot_t"
    if not np.isfinite(th) or not np.isfinite(se) or se == 0:
        return {"ratio": float(np.exp(th)) if np.isfinite(th) else None, "lo": None, "hi": None, "p": None,
                "method": name, "b": b, "undefined": True}
    thb, seb = log_ratio_and_se(ea[draws], la[draws], eb[draws], lb[draws], blocks)
    ok = np.isfinite(thb) & np.isfinite(seb) & (seb > 0)
    t = (thb[ok] - th) / seb[ok]
    t0 = th / se
    if symmetric:
        q = np.quantile(np.abs(t), 1 - alpha)
        lo, hi = th - q * se, th + q * se
        p = float(np.mean(np.abs(t) >= abs(t0)))
    else:
        tlo, thi = np.quantile(t, [alpha / 2, 1 - alpha / 2])
        lo, hi = th - thi * se, th - tlo * se
        p = min(1.0, 2 * min(float(np.mean(t >= t0)), float(np.mean(t <= t0))))
    return {"ratio": float(np.exp(th)), "lo": float(np.exp(lo)), "hi": float(np.exp(hi)), "p": min(1.0, p),
            "method": name, "b": b, "resamples_used": int(ok.sum())}


def holm(pvalues: list[float], alpha: float = 0.05) -> list[dict]:
    """Holm step-down. Returns adjusted p and reject flag per input, in input order."""
    m = len(pvalues)
    order = sorted(range(m), key=lambda i: pvalues[i])
    adjusted = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvalues[i]))
        adjusted[i] = running
    return [{"p": pvalues[i], "p_holm": adjusted[i], "reject": adjusted[i] < alpha} for i in range(m)]


# ---------------------------------------------------------------------------
# Coverage study (PILOT C6)
# ---------------------------------------------------------------------------

# Synthetic finite populations with known truth. Two strata ("mobile", "desktop") of
# 1,000 templates each. Per template: reference chars L and an error rate for engine A;
# engine B's rate is A's rate times a template-level multiplicative factor, so paired
# engines are correlated across templates, as real engines are.
SCENARIOS = {
    "S1 moderate skew (draft sim)": {"beta": [(1.2, 30.0), (1.2, 30.0)], "len": "uniform"},
    "S2 low error, heavy skew": {"beta": [(0.5, 40.0), (0.5, 40.0)], "len": "uniform"},
    "S3 high error": {"beta": [(2.0, 12.0), (2.0, 12.0)], "len": "uniform"},
    "S4 strata differ": {"beta": [(1.0, 50.0), (1.5, 15.0)], "len": "uniform"},
    "S5 skewed lengths": {"beta": [(1.2, 30.0), (1.2, 30.0)], "len": "lognormal"},
}


def _population(spec: dict, rng, per_stratum: int = 1_000):
    L, pa = [], []
    for a, bb in spec["beta"]:
        if spec["len"] == "uniform":
            L.append(rng.integers(300, 3001, size=per_stratum))
        else:
            L.append(np.clip(rng.lognormal(6.8, 0.8, size=per_stratum), 50, 20_000).astype(int))
        pa.append(rng.beta(a, bb, size=per_stratum))
    L = np.concatenate(L)
    pa = np.concatenate(pa)
    pb = np.clip(pa * np.exp(rng.normal(0.3, 0.5, size=len(pa))), 0, 1)
    Ea = rng.binomial(L, pa)
    Eb = rng.binomial(L, pb)
    ff = np.array(["mobile"] * per_stratum + ["desktop"] * per_stratum)
    return L, Ea, Eb, ff


def coverage_study(methods=("percentile", "bca", "boot_t", "log_t"), n_per_stratum: int = 20, sims: int = 2_000,
                   b: int = 999, seed: int = SEED, scenarios=None) -> dict:
    scenarios = scenarios or SCENARIOS
    out = {}
    for s_i, (name, spec) in enumerate(scenarios.items()):
        rng = np.random.default_rng(seed + 1000 * s_i)
        L, Ea, Eb, ff = _population(spec, rng)
        truth_r = Ea.sum() / L.sum()
        truth_d = Ea.sum() / L.sum() - Eb.sum() / L.sum()
        half = len(L) // 2
        hits = {("ratio", m): 0 for m in methods}
        hits.update({("diff", m): 0 for m in methods if m != "log_t"})
        width = {k: [] for k in hits}
        for s in range(sims):
            idx = np.concatenate([rng.choice(half, n_per_stratum, replace=False),
                                  half + rng.choice(half, n_per_stratum, replace=False)])
            f = ff[idx]
            for m in methods:
                r = ratio_ci(Ea[idx], L[idx], f, m, b=b, seed=seed + s)
                hits[("ratio", m)] += r["lo"] <= truth_r <= r["hi"]
                width[("ratio", m)].append(r["half_width"])
                if m != "log_t":
                    d = paired_diff_ci(Ea[idx], L[idx], Eb[idx], L[idx], f, m, b=b, seed=seed + s)
                    hits[("diff", m)] += d["lo"] <= truth_d <= d["hi"]
                    width[("diff", m)].append((d["hi"] - d["lo"]) / 2)
        out[name] = {f"{k[0]}:{k[1]}": {"coverage": hits[k] / sims, "mean_half_width": float(np.mean(width[k]))}
                     for k in hits}
        out[name]["truth_ratio"] = float(truth_r)
        out[name]["truth_diff"] = float(truth_d)
    return {"rule": SELECTION_RULE, "band": list(C6_BAND), "n_per_stratum": n_per_stratum, "sims": sims, "b": b,
            "results": out}


# Round 2 (fixed 2026-09-24 after round 1 found no passing method, before round 2 ran):
ROUND2_RULE = (
    "Round 1 selected nothing. Round 2 adds candidates: ratio 'boot_t' (retained), difference "
    "'boot_t_sym', relative effect 'log_boot_t' and 'log_boot_t_sym'. A method set passes only if "
    "every chosen interval is within [0.93, 0.97] in all 5 round-1 scenarios AND in 3 held-out "
    "scenarios (H1-H3, fresh seeds, not used for selection), at 20 templates per stratum, 2,000 "
    "simulations each. Band not relaxed. If the difference interval fails but the relative-effect "
    "interval passes, confirmatory tests move to the relative scale and absolute differences are "
    "reported descriptively, labelled with their measured coverage."
)

HELD_OUT = {
    "H1 engine B better but noisier": {"beta": [(0.8, 20.0), (0.8, 20.0)], "len": "uniform", "b_factor": (-0.2, 0.8)},
    "H2 very skewed lengths": {"beta": [(3.0, 40.0), (3.0, 40.0)], "len": "lognormal_wide"},
    "H3 bimodal templates": {"beta": "bimodal", "len": "uniform"},
}


def _population_r2(spec: dict, rng, per_stratum: int = 1_000):
    L, pa = [], []
    for s in range(2):
        if spec["len"] == "uniform":
            L.append(rng.integers(300, 3001, size=per_stratum))
        elif spec["len"] == "lognormal":
            L.append(np.clip(rng.lognormal(6.8, 0.8, size=per_stratum), 50, 20_000).astype(int))
        else:
            L.append(np.clip(rng.lognormal(6.8, 1.2, size=per_stratum), 30, 40_000).astype(int))
        if spec["beta"] == "bimodal":
            hi = rng.random(per_stratum) < 0.2
            pa.append(np.where(hi, rng.beta(4.0, 10.0, per_stratum), rng.beta(1.0, 80.0, per_stratum)))
        else:
            a, bb = spec["beta"][s]
            pa.append(rng.beta(a, bb, size=per_stratum))
    L = np.concatenate(L)
    pa = np.concatenate(pa)
    mu, sd = spec.get("b_factor", (0.3, 0.5))
    pb = np.clip(pa * np.exp(rng.normal(mu, sd, size=len(pa))), 0, 1)
    ff = np.array(["mobile"] * per_stratum + ["desktop"] * per_stratum)
    return L, rng.binomial(L, pa), rng.binomial(L, pb), ff


def coverage_study_r2(n_per_stratum: int = 20, sims: int = 2_000, b: int = 999, seed: int = SEED + 7) -> dict:
    scen = {**{k: v for k, v in SCENARIOS.items()}, **HELD_OUT}
    out = {}
    for s_i, (name, spec) in enumerate(scen.items()):
        rng = np.random.default_rng(seed + 1000 * s_i)
        L, Ea, Eb, ff = _population_r2(spec, rng)
        tr = Ea.sum() / L.sum()
        tb = Eb.sum() / L.sum()
        truth = {"ratio": tr, "diff": tr - tb, "rel": tr / tb}
        half = len(L) // 2
        keys = ["ratio:boot_t", "diff:boot_t", "diff:boot_t_sym", "rel:log_boot_t", "rel:log_boot_t_sym"]
        hits = dict.fromkeys(keys, 0)
        undefined = 0
        for s in range(sims):
            idx = np.concatenate([rng.choice(half, n_per_stratum, replace=False),
                                  half + rng.choice(half, n_per_stratum, replace=False)])
            f = ff[idx]
            ea, la, eb = Ea[idx], L[idx], Eb[idx]
            r = ratio_ci(ea, la, f, "boot_t", b=b, seed=seed + s)
            hits["ratio:boot_t"] += r["lo"] <= truth["ratio"] <= r["hi"]
            d = paired_diff_ci(ea, la, eb, la, f, "boot_t", b=b, seed=seed + s)
            hits["diff:boot_t"] += d["lo"] <= truth["diff"] <= d["hi"]
            d = diff_ci_sym(ea, la, eb, la, f, b=b, seed=seed + s)
            hits["diff:boot_t_sym"] += d["lo"] <= truth["diff"] <= d["hi"]
            for sym, key in ((False, "rel:log_boot_t"), (True, "rel:log_boot_t_sym")):
                q = rate_ratio_ci(ea, la, eb, la, f, symmetric=sym, b=b, seed=seed + s)
                if q.get("undefined"):
                    undefined += 1
                    continue
                hits[key] += q["lo"] <= truth["rel"] <= q["hi"]
        out[name] = {k: hits[k] / sims for k in keys}
        out[name]["held_out"] = name in HELD_OUT
        out[name]["undefined_relative"] = undefined
    passing = {k: all(C6_BAND[0] <= out[s][k] <= C6_BAND[1] for s in out)
               for k in ["ratio:boot_t", "diff:boot_t", "diff:boot_t_sym", "rel:log_boot_t", "rel:log_boot_t_sym"]}
    return {"rule": ROUND2_RULE, "band": list(C6_BAND), "n_per_stratum": n_per_stratum, "sims": sims, "b": b,
            "results": out, "passes_all_scenarios": passing}


def choose_method(study: dict) -> dict:
    """Apply SELECTION_RULE to a coverage_study() result."""
    lo, hi = study["band"]
    methods = sorted({k.split(":")[1] for r in study["results"].values() for k in r if ":" in k})
    verdict = {}
    for m in methods:
        covs = []
        for r in study["results"].values():
            for target in ("ratio", "diff"):
                key = f"{target}:{m}"
                if key in r:
                    covs.append(r[key]["coverage"])
        needs_both = all(f"diff:{m}" in r for r in study["results"].values())
        passes = needs_both and all(lo <= c <= hi for c in covs)
        verdict[m] = {"min": min(covs), "max": max(covs), "worst_gap": max(abs(c - 0.95) for c in covs),
                      "covers_both_targets": needs_both, "passes": passes}
    passing = [m for m, v in verdict.items() if v["passes"]]
    chosen = min(passing, key=lambda m: verdict[m]["worst_gap"]) if passing else None
    return {"verdict": verdict, "chosen": chosen}


def sample_size_rule(pilot_ci: dict, n_pilot_per_stratum: int, n_full_per_stratum: int) -> dict:
    """PREREGISTRATION §2: projected 95% half-width for the full set vs
    max(0.2 percentage points, 25% of the pilot M1). Projection assumes the
    half-width scales with 1/sqrt(templates per stratum)."""
    projected = pilot_ci["half_width"] * np.sqrt(n_pilot_per_stratum / n_full_per_stratum)
    threshold = max(0.002, 0.25 * pilot_ci["point"])
    return {"pilot_m1": pilot_ci["point"], "pilot_half_width": pilot_ci["half_width"],
            "projected_half_width_full": float(projected), "threshold": float(threshold),
            "increase_templates": bool(projected > threshold), "method": pilot_ci.get("method")}
