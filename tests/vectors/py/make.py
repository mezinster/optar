"""Writes the vectors made by the Python code: python -m tests.vectors.py.make

The files pin what optar 0.3.1 does today. The functions here compute every
result from the inputs stored in the files, and the tests call them again.
"""

import json
import random
from pathlib import Path

import numpy as np

from optar.container import Header, padding, plan, plan_for, positions, wrap
from optar.format import LAYOUTS, PARITY
from optar.rs import RSCode
from optar.tag import make_tag, tagged_label
from tests.helpers import seeded_bytes
from tests.vectors.load import array_digest, digest

HERE = Path(__file__).parent

PARITIES = (32, 64)
MESSAGE_KINDS = ("zeros", "ones", "ramp", "seed1", "seed2")
CONTAINER_PARITIES = tuple(PARITY.values())
FILE_NAME = "vector.bin"
FILE_SEED = 41
HEADER_ARGS = {
    "page": 3,
    "total": 7,
    "size": 552508,
    "fingerprint": bytes(range(16)).hex(),
    "parity": 64,
}
PADDING_ARGS = {"first": 0, "count": 100}
PADDING_ARGS_OFFSET = {"first": 45, "count": 70}
TAG_INPUTS = [
    {"name": "empty", "size": 0, "seed": None},
    {"name": "x", "size": 1, "seed": None},
    {"name": "seed5", "size": 300_000, "seed": 5},
]
TAG_FILE_NAME = "name.tar"
TAG_PAGES = (1, 2)
TAG_TOTAL = 2


def message(kind: str, k: int) -> bytes:
    if kind == "zeros":
        return bytes(k)
    if kind == "ones":
        return b"\xff" * k
    if kind == "ramp":
        return bytes(range(k))
    return seeded_bytes(int(kind[-1]), k)


def parity_case(parity: int, kind: str) -> dict:
    data = np.frombuffer(message(kind, 255 - parity), dtype=np.uint8)[None, :]
    return {
        "parity": parity,
        "message": kind,
        "parity_hex": RSCode(parity).encode(data)[0].tobytes().hex(),
    }


def repair_specs() -> list[dict]:
    """The damage of each repair case: fixed positions and nonzero xor masks."""
    specs = []
    for parity in PARITIES:
        limit = parity // 2
        kinds = [
            ("errors at the limit", limit, 0),
            ("erasures at the limit", 0, parity),
            ("5 errors and the erasures that fill the rest", 5, parity - 10),
            ("one error beyond the limit", limit + 1, 0),
        ]
        for n, (what, errors, erasures) in enumerate(kinds):
            rng = random.Random(f"{parity}:{n}")
            spots = rng.sample(range(255), errors + erasures)
            masks = [rng.randrange(1, 256) for _ in spots]
            specs.append(
                {
                    "parity": parity,
                    "what": what,
                    "seed": 3,
                    "error_positions": spots[:errors],
                    "error_xor": masks[:errors],
                    "erasure_positions": spots[errors:],
                    "erasure_xor": masks[errors:],
                }
            )
    return specs


def repair_outcome(spec: dict) -> dict:
    parity = spec["parity"]
    code = RSCode(parity)
    data = np.frombuffer(seeded_bytes(spec["seed"], 255 - parity), dtype=np.uint8)[None, :]
    word = np.hstack([data, code.encode(data)])
    received = word.copy()
    erased = np.zeros(word.shape, dtype=bool)
    for at, xor in zip(spec["error_positions"], spec["error_xor"], strict=True):
        received[0, at] ^= xor
    for at, xor in zip(spec["erasure_positions"], spec["erasure_xor"], strict=True):
        received[0, at] ^= xor
        erased[0, at] = True
    result = code.decode(received, erased)
    return {
        "ok": bool(result.ok[0]),
        "errors": int(result.errors[0]),
        "erasures": int(result.erasures[0]),
        "words_sha256": digest(result.words[0].tobytes()),
        "original_sha256": digest(word[0].tobytes()),
        "received_sha256": digest(received[0].tobytes()),
    }


def header_hex(args: dict) -> str:
    header = Header(
        args["page"], args["total"], args["size"], bytes.fromhex(args["fingerprint"]),
        args["parity"],
    )
    return header.pack().hex()


def padding_hex(args: dict) -> str:
    return padding(args["first"], args["count"]).tobytes().hex()


def layout_names() -> list[str]:
    return [f"{paper}-{dots}" for paper, dots in LAYOUTS]


def layout_format(layout_name: str):
    paper, dots = layout_name.split("-")
    return LAYOUTS[(paper, dots)].fmt


def stream_input(layout_name: str, parity: int) -> bytes:
    fmt = layout_format(layout_name)
    size = int(1.5 * plan_for(1, fmt, parity).data_bytes)
    return seeded_bytes(FILE_SEED, size)


def stream_case(layout_name: str, parity: int) -> dict:
    fmt = layout_format(layout_name)
    data = stream_input(layout_name, parity)
    p = plan(len(data), FILE_NAME, fmt, parity)
    stream = wrap(data, FILE_NAME, fmt, parity)
    pos = positions(p)
    last = p.codewords - 1
    return {
        "layout": layout_name,
        "format": fmt.to_string(),
        "parity": parity,
        "size": len(data),
        "pages": p.total,
        "codewords": p.codewords,
        "stream_bytes": len(stream),
        "stream_sha256": digest(stream),
        "positions": {
            str(j): {"first16": pos[j][:16].tolist(), "sha256": array_digest(pos[j], np.int64)}
            for j in (0, 1, last)
        },
    }


def tag_data(spec: dict) -> bytes:
    if spec["seed"] is not None:
        return seeded_bytes(spec["seed"], spec["size"])
    return b"x" * spec["size"]


def tag_case(spec: dict) -> dict:
    tag = make_tag(tag_data(spec))
    # An empty file is printed as page 1 of 0, the only form the tools print for it.
    total, pages = (TAG_TOTAL, TAG_PAGES) if spec["size"] else (0, (1,))
    return {
        "input": spec,
        "total": total,
        "size": tag.size,
        "fingerprint": tag.fingerprint,
        "page_texts": {str(p): tag.page_text(p, total) for p in pages},
        "labels": {str(p): tagged_label(tag, TAG_FILE_NAME, p, total) for p in pages},
    }


def build_reed_solomon() -> dict:
    return {
        "pins": "The parity bytes of the (255, 255 - parity) Reed-Solomon code and the outcome "
        "of repairing damaged codewords.",
        "source": "python",
        "cases": {
            "parity": [parity_case(p, kind) for p in PARITIES for kind in MESSAGE_KINDS],
            "repairs": [dict(spec, outcome=repair_outcome(spec)) for spec in repair_specs()],
        },
    }


def build_container() -> dict:
    return {
        "pins": "The container's header bytes, padding stream, wrapped streams and spread "
        "codeword positions.",
        "source": "python",
        "cases": {
            "header": {"args": HEADER_ARGS, "hex": header_hex(HEADER_ARGS)},
            "padding": {"args": PADDING_ARGS, "hex": padding_hex(PADDING_ARGS)},
            "padding_offset": {
                "args": PADDING_ARGS_OFFSET,
                "hex": padding_hex(PADDING_ARGS_OFFSET),
            },
            "streams": [stream_case(n, p) for n in layout_names() for p in CONTAINER_PARITIES],
        },
    }


def build_tag() -> dict:
    return {
        "pins": "The document tag made from a file and the labels printed with it.",
        "source": "python",
        "cases": {
            "file_name": TAG_FILE_NAME,
            "total": TAG_TOTAL,
            "tags": [tag_case(s) for s in TAG_INPUTS],
        },
    }


def write(name: str, obj: dict) -> None:
    (HERE / f"{name}.json").write_text(json.dumps(obj, sort_keys=True, indent=1) + "\n")


def main() -> None:
    write("reed_solomon", build_reed_solomon())
    write("container", build_container())
    write("tag", build_tag())


if __name__ == "__main__":
    main()
