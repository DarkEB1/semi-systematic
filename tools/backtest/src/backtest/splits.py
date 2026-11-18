"""Train/test index splits over T ordered dates: walk-forward and purged K-fold."""

from __future__ import annotations

from collections.abc import Iterator

import numpy as np
import numpy.typing as npt

Split = tuple[npt.NDArray[np.intp], npt.NDArray[np.intp]]


def walk_forward(
    n: int, train: int, test: int, gap: int = 0, expanding: bool = False
) -> Iterator[Split]:
    """Yield (train, test) date indices where training is strictly in the past.

    Each fit is used for `test` dates, then refit: set `test` to the production refit frequency.
    `gap` dates are dropped between train and test (labels that overlap the test period).
    Rolling keeps the latest `train` dates; expanding keeps everything from date 0.
    """
    start = train + gap
    while start < n:
        fit_end = start - gap
        fit_start = 0 if expanding else fit_end - train
        yield np.arange(fit_start, fit_end), np.arange(start, min(start + test, n))
        start += test


def purged_kfold(n: int, k: int, purge: int = 0, embargo: int = 0) -> Iterator[Split]:
    """Yield (train, test) date indices for K contiguous folds with gaps on both sides.

    Training surrounds the test fold, so `purge` dates before it (labels overlapping the test
    period) and `embargo` dates after it (features looking back into it) are removed.
    """
    idx = np.arange(n)
    for fold in np.array_split(idx, k):
        keep = (idx < fold[0] - purge) | (idx > fold[-1] + embargo)
        yield idx[keep], fold
