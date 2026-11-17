"""Load frozen conformance vectors (no compiler needed)."""

import hashlib
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent


def load(name: str) -> dict:
    """Load tests/vectors/<name>.json."""
    return json.loads((HERE / f"{name}.json").read_text())


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def array_digest(a: np.ndarray, dtype) -> str:
    assert a.dtype == dtype, (a.dtype, dtype)
    return digest(np.ascontiguousarray(a).tobytes())
