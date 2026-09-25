"""PILOT A6: whitespace reconstruction through the real extractor in real Chromium.

Needs Playwright + Chromium (run inside the tools image). Expected strings are
written by hand from CSS white-space rules, not produced by the code under test.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

playwright = pytest.importorskip("playwright.sync_api")

import render_chromium as rc  # noqa: E402

EXPECTED = [
    ["double spaced text"],
    ["non breaking space"],
    ["first line", "second line"],
    ["indented code"],
    ["leading and trailing"],
    ["source newline collapses"],
    ["alpha", "beta", "gamma", "delta"],
    ["splitword and two words"],
]


@pytest.fixture(scope="module")
def geometry():
    server, port = rc.start_server()
    with playwright.sync_playwright() as p:
        browser = p.chromium.launch()
        out = rc.render_once(
            browser, f"http://127.0.0.1:{port}/templates/_fixtures/whitespace/index.html?theme=light",
            "desktop", 1, "light", full=False,
        )
        browser.close()
    server.shutdown()
    return out["geometry"]


def test_whitespace_lines_exact(geometry):
    got = [[line["text"] for line in el["lines"]] for el in geometry["elements"]]
    assert got == EXPECTED


def test_no_untagged_text(geometry):
    assert geometry["untagged_text"] == []
