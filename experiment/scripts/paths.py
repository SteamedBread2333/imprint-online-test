"""Shared paths for the imprint token / retrieval experiment."""
import os

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(SCRIPTS)
PROJECT = os.path.dirname(BASE)
DATA = os.path.join(BASE, "data")
REPORT_DIR = os.path.join(BASE, "report")
TOKEN_VAULT = ".imprint-token-bench"
RETRIEVAL_VAULT = ".imprint-retrieval"
LINK_VAULT = ".imprint-link-bench"


def find_top_k(project=None) -> int:
    """Document budget for find; control Read cap must use the same k."""
    root = project or PROJECT
    path = os.path.join(root, "imprint.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.split("#", 1)[0]
                if "find_top_k" in line and ":" in line:
                    return int(line.split(":", 1)[1].strip())
    except (OSError, ValueError):
        pass
    return 3


def imprint_mcp() -> str:
    env = os.environ.get("IMPRINT_MCP", "").strip()
    if env:
        return env
    for candidate in (
        os.path.join(BASE, "bin", "imprint-mcp"),
        os.path.expanduser("~/go/bin/imprint-mcp"),
    ):
        if os.path.isfile(candidate):
            return candidate
    raise FileNotFoundError("imprint-mcp not found; set IMPRINT_MCP")


def public_bin(path=None):
    """Name only — never write the operator's home directory into artifacts."""
    name = os.path.basename(path or imprint_mcp())
    return name or "imprint-mcp"
