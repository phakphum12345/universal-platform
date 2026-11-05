"""Deterministic Gaussian-elimination solver for small dense linear systems."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from .errors import SolverError

@dataclass(frozen=True, slots=True)
class LinearSolveResult:
    solution: tuple[float, ...]
    residual_inf: float
    method: str = "gaussian-elimination-partial-pivoting"

def solve_linear(matrix: list[list[float]], rhs: list[float], *, tolerance: float = 1e-12) -> LinearSolveResult:
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        raise SolverError("Expected a non-empty square matrix matching rhs length")
    if tolerance <= 0 or not isfinite(tolerance):
        raise SolverError("Tolerance must be finite and positive")
    a = [[float(v) for v in row] + [float(rhs[i])] for i, row in enumerate(matrix)]
    if any(not isfinite(v) for row in a for v in row):
        raise SolverError("Inputs must be finite")
    scale = max(abs(v) for row in matrix for v in row)
    if scale == 0:
        raise SolverError("Singular matrix")
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) <= tolerance * scale:
            raise SolverError("Singular or numerically rank-deficient matrix")
        a[col], a[pivot] = a[pivot], a[col]
        p = a[col][col]
        for j in range(col, n + 1):
            a[col][j] /= p
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            for j in range(col, n + 1):
                a[row][j] -= factor * a[col][j]
    x = tuple(a[i][n] for i in range(n))
    residual = max(abs(sum(float(matrix[i][j]) * x[j] for j in range(n)) - float(rhs[i])) for i in range(n))
    if not all(isfinite(v) for v in x) or not isfinite(residual):
        raise SolverError("Numerically invalid solution")
    return LinearSolveResult(x, residual)
