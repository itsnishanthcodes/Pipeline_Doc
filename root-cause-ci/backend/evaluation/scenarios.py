"""Controlled failure scenarios for the offline evaluation of the deterministic pipeline.

Each scenario is a synthetic but realistic GitHub Actions failure with a known ground truth:
the failure category a reviewer would assign, the commit that introduced it (when the failure is
caused by a code change), whether the failure is flaky, and the file a fix should modify.
The expected labels were written before running the pipeline and must not be tuned to its output.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Commit:
    sha: str
    message: str
    files: dict[str, str | None]  # path -> unified-diff patch


@dataclass
class Scenario:
    name: str
    log: str
    commits: list[Commit]                 # oldest -> newest, all between last green run and the failure
    sources: dict[str, str]               # repository files at the failing commit
    history: list[str] = field(default_factory=lambda: ["PASS"] * 6)   # earlier outcomes of the job
    same_commit_passed: bool = False
    blame_sha: str | None = None
    expected_category: str = "CODE_REGRESSION"
    expected_culprit: str | None = None   # None when no commit caused the failure
    expected_flaky: bool = False
    expected_target: str | None = None


def hunk(start: int, removed: list[str], added: list[str], context_before: list[str] | None = None) -> str:
    ctx = context_before or []
    old_start = max(start - len(ctx), 1)
    body = [f" {c}" for c in ctx] + [f"-{r}" for r in removed] + [f"+{a}" for a in added]
    return f"@@ -{old_start},{len(ctx) + len(removed)} +{old_start},{len(ctx) + len(added)} @@\n" + "\n".join(body) + "\n"


PYTEST_HEADER = "##[group]Run pytest -q\npytest -q\n##[endgroup]\n"
EXIT = "##[error]Process completed with exit code 1.\n"

CALC = "def add(a, b):\n    return a + b + 1\n\n\ndef sub(a, b):\n    return a - b\n"
ORDERS = "\n".join(["# orders"] * 17) + "\ndef apply_discount(total, count):\n    per_item = total / count\n    return per_item * 0.9\n"
UTIL = "\n".join(["# util"] * 3) + "\ndef slugify(text):\n    return text.lower().replace(' ', '_')\n" + "\n".join(["# pad"] * 20) + "\ndef shout(text):\n    return text.upper()\n"
SHAPES = "def area(w, h):\n    return w * h * 2\n\n\ndef perimeter(w, h):\n    return 2 * (w + h)\n"

SCENARIOS: list[Scenario] = [
    Scenario(
        name="configuration: missing environment variable",
        log=(
            "##[group]Run python -m app.settings\n##[endgroup]\nTraceback (most recent call last):\n"
            '  File "/home/runner/work/app/app/app/settings.py", line 8, in <module>\n'
            "    raise RuntimeError('Required environment variable DATABASE_URL is not set')\n"
            "RuntimeError: Required environment variable DATABASE_URL is not set\n" + EXIT
        ),
        commits=[
            Commit("a1" * 20, "docs: update readme", {"README.md": hunk(1, ["a"], ["b"])}),
            Commit("a2" * 20, "settings: require DATABASE_URL",
                   {"app/settings.py": hunk(8, [], ["    raise RuntimeError('Required environment variable DATABASE_URL is not set')"])}),
        ],
        sources={"app/settings.py": "\n".join(["# settings"] * 7) + "\nif not DB:\n    raise RuntimeError('x')\n"},
        expected_category="CONFIGURATION_FAILURE", expected_culprit="a2" * 20, expected_target="app/settings.py",
    ),
    Scenario(
        name="infrastructure: docker daemon unavailable",
        log="##[group]Run docker build .\n##[endgroup]\nCannot connect to the Docker daemon at unix:///var/run/docker.sock. Is the docker daemon running?\n" + EXIT,
        commits=[Commit("b1" * 20, "feat: add endpoint", {"src/api.py": hunk(3, [], ["def ping():", "    return 'pong'"])})],
        sources={"src/api.py": "import os\n\n\ndef ping():\n    return 'pong'\n"},
        expected_category="INFRASTRUCTURE_FAILURE", expected_culprit=None,
    ),
    Scenario(
        name="dependency: unresolvable version pin",
        log=(
            "##[group]Run pip install -r requirements.txt\npip install -r requirements.txt\n##[endgroup]\n"
            "ERROR: Could not find a version that satisfies the requirement requests==99.0\n"
            "ERROR: No matching distribution found for requests==99.0\n" + EXIT
        ),
        commits=[
            Commit("c1" * 20, "bump requests", {"requirements.txt": hunk(2, ["requests==2.32.0"], ["requests==99.0"])}),
            Commit("c2" * 20, "refactor client", {"src/client.py": hunk(4, ["x = 1"], ["x = 2"])}),
        ],
        sources={"requirements.txt": "fastapi\nrequests==99.0\n", "src/client.py": "import requests\n\n\nx = 2\n"},
        expected_category="DEPENDENCY_FAILURE", expected_culprit="c1" * 20, expected_target="requirements.txt",
    ),
    Scenario(
        name="dependency: new import of an uninstalled module",
        log=(
            PYTEST_HEADER + "ImportError while importing test module 'tests/test_loader.py'.\nTraceback:\n"
            '  File "/home/runner/work/app/app/src/loader.py", line 1, in <module>\n    import yaml\n'
            "ModuleNotFoundError: No module named 'yaml'\n" + EXIT
        ),
        commits=[
            Commit("d1" * 20, "loader: parse yaml", {"src/loader.py": hunk(1, [], ["import yaml"])}),
            Commit("d2" * 20, "ci: cache pip", {".github/workflows/ci.yml": hunk(10, [], ["      cache: pip"])}),
        ],
        sources={"src/loader.py": "import yaml\n\n\ndef load(p):\n    return yaml.safe_load(open(p))\n",
                 "tests/test_loader.py": "from src.loader import load\n"},
        expected_category="DEPENDENCY_FAILURE", expected_culprit="d1" * 20, expected_target="src/loader.py",
    ),
    Scenario(
        name="code regression: single commit",
        log=(
            PYTEST_HEADER + ">       assert add(2, 3) == 5\nE       assert 6 == 5\nE        +  where 6 = add(2, 3)\n"
            "tests/test_calc.py:4: AssertionError\nFAILED tests/test_calc.py::test_add - assert 6 == 5\n" + EXIT
        ),
        commits=[Commit("e1" * 20, "tweak add", {"src/calc.py": hunk(2, ["    return a + b"], ["    return a + b + 1"], ["def add(a, b):"])})],
        sources={"src/calc.py": CALC, "tests/test_calc.py": "from src.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"},
        expected_culprit="e1" * 20, expected_target="src/calc.py",
    ),
    Scenario(
        name="code regression: culprit is not the latest commit",
        log=(
            PYTEST_HEADER + ">       assert add(2, 3) == 5\nE       assert 6 == 5\nE        +  where 6 = add(2, 3)\n"
            "tests/test_calc.py:4: AssertionError\nFAILED tests/test_calc.py::test_add - assert 6 == 5\n" + EXIT
        ),
        commits=[
            Commit("f1" * 20, "docs", {"README.md": hunk(1, ["a"], ["b"])}),
            Commit("f2" * 20, "tweak add", {"src/calc.py": hunk(2, ["    return a + b"], ["    return a + b + 1"], ["def add(a, b):"])}),
            Commit("f3" * 20, "test other", {"tests/test_other.py": hunk(1, ["x"], ["y"])}),
            Commit("f4" * 20, "ci tweak", {".github/workflows/ci.yml": hunk(3, ["a"], ["b"])}),
        ],
        sources={"src/calc.py": CALC, "tests/test_calc.py": "from src.calc import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"},
        expected_culprit="f2" * 20, expected_target="src/calc.py",
    ),
    Scenario(
        name="code regression: exception raised in changed source line",
        log=(
            PYTEST_HEADER + "tests/test_orders.py:6: in test_discount\n    apply_discount(100, 0)\n"
            "src/orders.py:19: in apply_discount\n    per_item = total / count\n"
            "E   ZeroDivisionError: division by zero\nFAILED tests/test_orders.py::test_discount - ZeroDivisionError\n" + EXIT
        ),
        commits=[
            Commit("g1" * 20, "orders: per-item discount",
                   {"src/orders.py": hunk(19, ["    return total * 0.9"], ["    per_item = total / count", "    return per_item * 0.9"], ["def apply_discount(total, count):"])}),
            Commit("g2" * 20, "cart: rename", {"src/cart.py": hunk(2, ["a"], ["b"])}),
            Commit("g3" * 20, "docs", {"docs/usage.md": hunk(1, ["a"], ["b"])}),
        ],
        sources={"src/orders.py": ORDERS, "tests/test_orders.py": "from src.orders import apply_discount\n"},
        expected_culprit="g1" * 20, expected_target="src/orders.py",
    ),
    Scenario(
        name="code regression: older commit changed the failing function",
        log=(
            PYTEST_HEADER + "src/util.py:5: in slugify\n    return text.lower().replace(' ', '_')\n"
            "E   AttributeError: 'NoneType' object has no attribute 'lower'\nFAILED tests/test_util.py::test_slug\n" + EXIT
        ),
        commits=[
            Commit("h1" * 20, "util: slugify signature", {"src/util.py": hunk(4, ["def slugify(text, sep='-'):"], ["def slugify(text):"])}),
            Commit("h2" * 20, "util: shout", {"src/util.py": hunk(27, ["    return text"], ["    return text.upper()"])}),
        ],
        sources={"src/util.py": UTIL, "tests/test_util.py": "from src.util import slugify\n"},
        blame_sha="h1" * 20, expected_culprit="h1" * 20, expected_target="src/util.py",
    ),
    Scenario(
        name="code regression: two commits touch the same file",
        log=(
            PYTEST_HEADER + ">       assert area(2, 3) == 6\nE       assert 12 == 6\nE        +  where 12 = area(2, 3)\n"
            "tests/test_shapes.py:4: AssertionError\nFAILED tests/test_shapes.py::test_area - assert 12 == 6\n" + EXIT
        ),
        commits=[
            Commit("i1" * 20, "shapes: area", {"src/shapes.py": hunk(2, ["    return w * h"], ["    return w * h * 2"], ["def area(w, h):"])}),
            Commit("i2" * 20, "shapes: perimeter", {"src/shapes.py": hunk(6, ["    return w + h"], ["    return 2 * (w + h)"], ["def perimeter(w, h):"])}),
        ],
        sources={"src/shapes.py": SHAPES, "tests/test_shapes.py": "from src.shapes import area\n"},
        expected_culprit="i1" * 20, expected_target="src/shapes.py",
    ),
    Scenario(
        name="flaky: intermittent timeout, same commit passed on rerun",
        log=PYTEST_HEADER + "E   TimeoutError: timed out after 30s waiting for http://localhost:9000\nFAILED tests/test_api.py::test_health - TimeoutError\n" + EXIT,
        commits=[Commit("j1" * 20, "api: log requests", {"src/api.py": hunk(5, [], ["    log(request)"])})],
        sources={"src/api.py": "def health():\n    return 'ok'\n", "tests/test_api.py": "import requests\n"},
        history=["PASS", "FAIL", "PASS", "PASS", "FAIL", "PASS"], same_commit_passed=True,
        expected_category="INFRASTRUCTURE_FAILURE", expected_culprit=None, expected_flaky=True,
    ),
    Scenario(
        name="flaky: order-dependent test",
        log=PYTEST_HEADER + ">       assert cache.size() == 0\nE       assert 3 == 0\ntests/test_cache.py:9: AssertionError\nFAILED tests/test_cache.py::test_empty - assert 3 == 0\n" + EXIT,
        commits=[Commit("k1" * 20, "docs", {"README.md": hunk(1, ["a"], ["b"])})],
        sources={"tests/test_cache.py": "from src.cache import cache\n"},
        history=["FAIL", "PASS", "FAIL", "PASS", "PASS"], same_commit_passed=True,
        expected_category="CODE_REGRESSION", expected_culprit=None, expected_flaky=True,
    ),
    Scenario(
        name="not flaky: first failure after a long green history",
        log=(
            PYTEST_HEADER + ">       assert add(1, 1) == 2\nE       assert 3 == 2\nE        +  where 3 = add(1, 1)\n"
            "tests/test_calc.py:4: AssertionError\nFAILED tests/test_calc.py::test_add - assert 3 == 2\n" + EXIT
        ),
        commits=[Commit("l1" * 20, "tweak add", {"src/calc.py": hunk(2, ["    return a + b"], ["    return a + b + 1"], ["def add(a, b):"])})],
        sources={"src/calc.py": CALC, "tests/test_calc.py": "from src.calc import add\n"},
        history=["PASS"] * 9, expected_culprit="l1" * 20, expected_target="src/calc.py",
    ),
    Scenario(
        name="unknown: native crash",
        log="##[group]Run ./bin/run-tests\n##[endgroup]\nSegmentation fault (core dumped)\n" + EXIT,
        commits=[Commit("m1" * 20, "build: new flags", {"Makefile": hunk(3, ["CFLAGS=-O2"], ["CFLAGS=-O3"])})],
        sources={"Makefile": "all:\n\tcc main.c\nCFLAGS=-O3\n"},
        expected_category="UNKNOWN", expected_culprit=None,
    ),
]
