"""Simulate how a coding agent typically searches a docs tree.

Agents do not pass the user utterance to ``grep -F``. They extract a few
keywords, rewrite identifiers (snake / kebab / space), and call ripgrep
case-insensitively. This module is that path, kept deterministic.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "for", "in", "on", "with",
    "vs", "via", "from", "into", "as", "at", "by", "is", "be", "not",
}

# Descriptive fillers an agent drops before calling rg.
WEAK_EN = STOP | {
    "naming", "domain", "data", "access", "exception", "base", "class",
    "timestamp", "storage", "prefix", "version", "structured", "logging",
    "test", "framework", "coverage", "security", "token", "rate", "limit",
    "degradation", "cache", "error", "budget", "freeze", "release",
    "errors", "duration", "metrics", "dead", "letter", "queue", "retry",
    "three", "consumer", "parameterized", "injection", "archive",
    "physical", "public", "function", "type", "annotations", "list",
    "pagination", "total", "database", "connection", "pool", "timeout",
    "two", "reviewers", "contract", "default", "off", "expiry",
    "catalog", "hardcoded", "string", "outbound", "connect", "read",
    "document", "drift", "sync", "health", "probe", "pattern",
    "api",
}

# Too generic to be an rg -e by themselves (and they used to match filler).
WEAK_CJK = {
    "方法", "函数", "变量", "数据", "访问", "场景", "模块", "项目",
    "实现", "改动", "要求", "规范", "方面", "条文", "来源",
}

# Longest-first stems used to unglue identifiers the way an agent rewrites
# ``messageid`` → ``message_id`` before calling rg.
STEMS = tuple(sorted((
    "message", "feature", "string", "delete", "trace", "snake", "case",
    "open", "flag", "soft", "api", "iso", "id",
), key=len, reverse=True))


def _camel_parts(token):
    parts = re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+", token)
    return parts if len(parts) > 1 else [token]


def _glued_parts(token):
    tl = token.lower()
    if not re.fullmatch(r"[a-z][a-z0-9]+", tl):
        return [token]
    parts, i = [], 0
    while i < len(tl):
        hit = next((s for s in STEMS if tl.startswith(s, i)), None)
        if not hit:
            rest = tl[i:]
            suf = next((s for s in STEMS if rest.endswith(s) and len(rest) > len(s)), None)
            if suf:
                prefix = rest[:-len(suf)]
                if prefix:
                    parts.append(prefix)
                parts.append(suf)
                return parts if len(parts) > 1 else [token]
            return [token]
        parts.append(hit)
        i += len(hit)
    return parts if len(parts) > 1 else [token]


def _flex(parts):
    escaped = [re.escape(p) for p in parts if p]
    if not escaped:
        return None
    if len(escaped) == 1:
        return escaped[0]
    return r"[\s_\-]*".join(escaped)


def _ident_score(tok):
    key = tok.lower()
    if key in WEAK_EN:
        return 0
    cjk = bool(re.search(r"[\u4e00-\u9fff]", tok))
    if cjk and len(tok) < 2:
        return 0
    if not cjk and len(tok) <= 3 and not tok.isupper():
        return 0
    score = min(len(tok), 12) / 4
    if re.search(r"[_\-/]", tok):
        score += 8
    if re.search(r"[A-Z].*[a-z]|[a-z].*[A-Z]", tok):
        score += 6
    if tok.isupper() and 2 <= len(tok) <= 8:
        score += 5
    if cjk:
        score += 4 + min(len(tok), 6)
    if len(_glued_parts(tok)) > 1:
        score += 7
    return score


def distill_patterns(query, query_local=None, limit=3):
    """Return rg -i regexes an agent would likely try."""
    scored = []

    def add(score, pat):
        if pat:
            scored.append((score, pat))

    raw_q = (query or "").strip()
    extra = (query_local or "").strip()
    parts = [p for p in re.split(r"[\s_\-]+", raw_q) if p] if raw_q else []

    # Two or three fragments with no filler → identifier rewrite
    # (snake case, ISO 8601, 性能 缓存). Longer descriptive queries are not
    # grepped as one regex.
    used_flex = False
    if 2 <= len(parts) <= 3 and all(p.lower() not in WEAK_EN for p in parts):
        add(12, _flex(parts))
        used_flex = True
    elif raw_q and not re.search(r"\s", raw_q):
        glued = _glued_parts(raw_q)
        camel = _camel_parts(raw_q)
        if len(glued) > 1:
            add(11, _flex(glued))
            used_flex = True
        elif len(camel) > 1:
            add(11, _flex(camel))
            used_flex = True
        else:
            add(8, re.escape(raw_q))

    # Drop short ASCII fragments of a flex rewrite (id, case). query_local
    # CJK terms stay even when the English side already filled a high-score slot.
    flex_bits = set(p.lower() for p in parts) if used_flex else set()
    for src, blob in (("query", raw_q), ("local", extra)):
        for tok in re.split(r"\s+", blob):
            if not tok:
                continue
            if (tok.lower() in flex_bits and len(tok) < 5
                    and not re.search(r"[\u4e00-\u9fff]", tok)):
                continue
            if tok == raw_q and not re.search(r"\s", raw_q):
                continue
            if tok in WEAK_CJK or tok.lower() in WEAK_EN:
                continue
            sc = _ident_score(tok)
            if sc <= 0:
                continue
            if (src != "local"
                    and re.search(r"[\u4e00-\u9fff]", tok)
                    and len(tok) <= 2 and tok != raw_q
                    and tok not in parts
                    and any(s >= 8 for s, _ in scored)):
                continue
            add(sc, re.escape(tok))

    scored.sort(key=lambda x: (-x[0], -len(x[1])))
    out, seen = [], set()
    for _, pat in scored:
        if pat in seen:
            continue
        seen.add(pat)
        out.append(pat)
        if len(out) >= limit:
            break
    if not out and raw_q:
        out.append(re.escape(raw_q) if not re.search(r"\s", raw_q) else _flex(parts) or re.escape(raw_q))
    return out


def _rg_bin():
    return shutil.which("rg")


def search_files(project, patterns):
    """Return doc paths matching any pattern (union), via rg -i or grep -riE."""
    if not patterns:
        return []
    rg = _rg_bin()
    if rg:
        cmd = [rg, "-i", "-l", "--glob", "*.md"]
        for p in patterns:
            cmd.extend(["-e", p])
        cmd.append("docs")
    else:
        cmd = ["grep", "-rilE", "--"] + ["|".join("(%s)" % p for p in patterns), "docs"]
    proc = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    files = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
    rel = []
    for f in files:
        f = f.replace("\\", "/")
        if "docs/" in f:
            rel.append("docs/" + f.split("docs/", 1)[1])
        elif f.startswith("docs"):
            rel.append(f)
        else:
            rel.append("docs/" + os.path.basename(f) if f.endswith(".md") else f)
    return rel


def search_lines(project, patterns):
    """Return matching lines (path:line:text) for token accounting."""
    if not patterns:
        return []
    rg = _rg_bin()
    if rg:
        cmd = [rg, "-i", "-n", "--no-heading", "--glob", "*.md"]
        for p in patterns:
            cmd.extend(["-e", p])
        cmd.append("docs")
    else:
        cmd = ["grep", "-rinE", "--"] + ["|".join("(%s)" % p for p in patterns), "docs"]
    proc = subprocess.run(cmd, cwd=project, capture_output=True, text=True)
    if proc.returncode not in (0, 1):
        return []
    out = []
    for l in proc.stdout.splitlines():
        if not l.strip():
            continue
        l = l.replace("\\", "/")
        if l.startswith("/") and "docs/" in l:
            l = "docs/" + l.split("docs/", 1)[1]
        out.append(l)
    return out


def tool_label():
    return "rg -i" if _rg_bin() else "grep -riE"


def rg_command(patterns, list_files=True):
    """Exact argv string the control actually ran (docs/ glob)."""
    if not patterns:
        return tool_label()
    if _rg_bin():
        extra = ["-l"] if list_files else ["-n", "--no-heading"]
        cmd = ["rg", "-i", *extra, "--glob", "*.md"]
        for p in patterns:
            cmd.extend(["-e", p])
        cmd.append("docs")
        return " ".join(cmd)
    joined = "|".join("(%s)" % p for p in patterns)
    flag = "-rilE" if list_files else "-rinE"
    return f"grep {flag} -- {joined} docs"


# Default; measure_retrieval overwrites with imprint.yaml find_top_k.
MAX_OPEN = 3
MAX_HIT_LINES = 40


def query_needles(query, query_local=None):
    out, seen = [], set()
    for blob in (query, query_local):
        for p in re.split(r"[\s_\-/]+", (blob or "").strip()):
            if not p:
                continue
            key = p.lower()
            if key in STOP or key in WEAK_EN or p in WEAK_CJK:
                continue
            if len(p) < 2 and not re.search(r"[\u4e00-\u9fff]", p):
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
    return out


def parse_hit_path(line):
    line = (line or "").replace("\\", "/")
    if "docs/" in line:
        rest = line.split("docs/", 1)[1]
        m = re.match(r"^([^:]+\.md):\d+:", rest)
        return ("docs/" + m.group(1)) if m else ""
    m = re.match(r"^([^:]+\.md):\d+:", line)
    return ("docs/" + m.group(1)) if m else ""


def filename_score(path, needles):
    """Token match on the latin filename; never substring (base⊂database)."""
    base = os.path.basename(path.replace("\\", "/")).lower()
    stem = re.sub(r"\.md$", "", base)
    parts = set(p for p in re.split(r"[^a-z0-9]+", stem) if p)
    n = 0
    for raw in needles:
        if re.search(r"[\u4e00-\u9fff]", raw):
            continue
        key = re.sub(r"[^a-z0-9]", "", raw.lower())
        if len(key) < 3:
            continue
        if key in parts:
            n += 3
    return n


def pick_open_files(query, files, hits, max_open=MAX_OPEN, query_local=None):
    """Choose at most max_open files from filename tokens + line hit mass.

    Filename match is never exclusive: a weak name hit must not skip the
    line sample, and must not beat a file that actually contains the terms.
    """
    if not files:
        return []
    if len(files) <= max_open:
        return list(files)
    needles = query_needles(query, query_local)
    line_best, line_n = {}, {}
    for h in hits:
        p = parse_hit_path(h)
        if not p:
            continue
        n = sum(1 for nd in needles if nd in h.lower())
        if n > line_best.get(p, 0):
            line_best[p] = n
        line_n[p] = line_n.get(p, 0) + 1

    def score(f):
        return filename_score(f, needles) * 3 + line_best.get(f, 0) * 5 + line_n.get(f, 0)

    ranked = sorted(files, key=lambda f: (-score(f), f))
    return ranked[:max_open]
