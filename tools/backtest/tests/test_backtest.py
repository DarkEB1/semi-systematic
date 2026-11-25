"""backtest: every expected number below is a worked example from the source lecture."""

from __future__ import annotations

import backtest as bt
import numpy as np
import pytest

HAND = np.array([[1, 1, -1], [1, 1, -1], [-1, -1, 1], [-1, -1, 1]], dtype=float)


def test_walk_forward_rolling_trains_only_on_the_past():
    splits = list(bt.walk_forward(10, train=4, test=2, gap=1))
    assert [(tr.tolist(), te.tolist()) for tr, te in splits] == [
        ([0, 1, 2, 3], [5, 6]),
        ([2, 3, 4, 5], [7, 8]),
        ([4, 5, 6, 7], [9]),
    ]


def test_walk_forward_expanding_keeps_all_history():
    splits = list(bt.walk_forward(10, train=4, test=3, expanding=True))
    assert [tr.tolist() for tr, _ in splits] == [[0, 1, 2, 3], [0, 1, 2, 3, 4, 5, 6]]
    assert [te.tolist() for _, te in splits] == [[4, 5, 6], [7, 8, 9]]


def test_purged_kfold_gaps_both_sides():
    splits = list(bt.purged_kfold(10, k=5, purge=1, embargo=2))
    train, test = splits[2]
    assert test.tolist() == [4, 5]
    assert train.tolist() == [0, 1, 2, 8, 9]
    assert np.concatenate([te for _, te in splits]).tolist() == list(range(10))


def test_net_pnl_pairs_position_at_t_with_return_at_t_plus_1():
    weights = np.array([[1.0, 0.0], [0.0, 2.0], [9.0, 9.0]])
    returns = np.array([[9.0, 9.0], [0.1, 0.5], [0.3, -0.2]])
    assert bt.net_pnl(weights, returns).tolist() == pytest.approx([0.1, -0.4])
    assert bt.net_pnl(weights, returns, costs=[0.01, 0.02, 9.0]).tolist() == pytest.approx(
        [0.09, -0.42]
    )
    assert bt.risk_scaled(weights, returns, vol=[0.1, 0.2, 9.0]).tolist() == pytest.approx(
        [1.0, -2.0]
    )


def test_information_coefficient_is_lagged_cosine():
    alpha = np.array([[1.0, -1.0], [1.0, 1.0], [9.0, 9.0]])
    resid = np.array([[9.0, 9.0], [2.0, -2.0], [-3.0, -3.0]])
    assert bt.information_coefficient(alpha, resid).tolist() == pytest.approx([1.0, -1.0])


def test_rademacher_hand_example_and_copies():
    assert bt.rademacher(HAND) == pytest.approx(0.375, abs=0.01)
    assert bt.rademacher(np.tile(HAND, 100)) == bt.rademacher(HAND)
    assert bt.rademacher(HAND, B=2_500, batch=1_000) == pytest.approx(0.375, abs=0.02)
    assert bt.massart_bound(HAND) == pytest.approx(0.741, abs=1e-3)
    assert bt.massart_bound(np.tile(HAND, 100)) == pytest.approx(1.689, abs=1e-3)


def test_ras_lower_bound_estimation_term():
    # one constant column: R is ~0, so the bound is the mean minus 3 kappa sqrt(2 log(2/d) / T)
    X = np.full((2_500, 1), 0.004)
    L, R = bt.ras_lower_bounds(X, kappa=0.02, delta=0.01)
    assert R == pytest.approx(0.0, abs=1e-4)
    assert L[0] + 2 * R == pytest.approx(0.004 - 0.003906, abs=1e-6)
    L_mc, _ = bt.ras_lower_bounds(X, kappa=0.02, delta=0.01, mc_delta=0.01)
    assert L[0] - L_mc[0] == pytest.approx(2 * 0.02 * np.sqrt(2 * np.log(100) / 10_000))


def test_ras_null_family_is_not_certified():
    X = np.random.default_rng(1).standard_normal((2_500, 500)).clip(-4, 4)
    L, R = bt.ras_lower_bounds(X, kappa=4.0, B=1_000)
    assert R == pytest.approx(0.0595, abs=0.005)  # sqrt(1/T) * E max of 500 normals (3.037)
    assert (X.mean(axis=0) > 2 * R).sum() == 0
    assert (L > 0).sum() == 0


def test_subgaussian_comparator():
    X = np.zeros((2_500, 10))
    assert bt.subgaussian_lower_bounds(X, sigma=0.032)[0] == pytest.approx(-0.0024, abs=5e-5)


def test_block_means_drops_partial_block():
    X = np.arange(14, dtype=float).reshape(7, 2)
    assert bt.block_means(X, 3).tolist() == [[2.0, 3.0], [8.0, 9.0]]


def test_sharpe_needs_a_time_unit():
    daily = 3 / np.sqrt(251)
    assert bt.annualize(daily) == pytest.approx(3.0)
    assert bt.annualize(2.32635 * bt.sharpe_se(daily, 2_500)) == pytest.approx(0.7437, abs=1e-3)
    assert 2.32635 * bt.sharpe_se(3.0, 2_500) * np.sqrt(251) == pytest.approx(1.7287, abs=1e-3)
