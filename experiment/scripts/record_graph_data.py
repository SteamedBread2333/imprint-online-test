"""Mini unified-graph payloads for record.html (desk /graph/unified shape)."""

CASE_GRAPHS = {
    "case_a": {
        "nodes": [
            {"id": "r-new", "kind": "rule", "label": "r-canary-v2", "claim": "灰度回滚 v2", "status": "active", "scope": ["aurora", "ops"]},
            {"id": "r-old", "kind": "rule", "label": "r-canary-v1", "claim": "灰度回滚 v1", "status": "superseded", "scope": ["aurora", "ops"]},
            {"id": "doc-dep", "kind": "document", "label": "08-deployment", "path": "docs/08-deployment.md", "heading": "灰度发布"},
            {"id": "doc-err", "kind": "document", "label": "03-error-handling", "path": "docs/03-error-handling.md"},
            {"id": "doc-rev", "kind": "document", "label": "13-review", "path": "docs/13-review.md"},
        ],
        "edges": [
            {"source": "r-new", "target": "r-old", "kind": "supersedes"},
            {"source": "r-new", "target": "doc-dep", "kind": "sources"},
        ],
    },
    "case_b": {
        "nodes": [
            {"id": "r-retry", "kind": "rule", "label": "r-http-retry", "claim": "HTTP retry ×3", "status": "active", "scope": ["aurora", "http"]},
            {"id": "r-post", "kind": "rule", "label": "r-no-post-retry", "claim": "No POST retry", "status": "active", "scope": ["aurora", "http"]},
            {"id": "r-dlq", "kind": "rule", "label": "r-dlq", "claim": "DLQ / visibility", "status": "active", "scope": ["aurora", "http"]},
            {"id": "doc-http", "kind": "document", "label": "16-http-client", "path": "docs/16-http-client.md"},
            {"id": "doc-api", "kind": "document", "label": "05-api-design", "path": "docs/05-api-design.md"},
            {"id": "doc-q", "kind": "document", "label": "12-concurrency", "path": "docs/12-concurrency.md"},
        ],
        "edges": [
            {"source": "r-retry", "target": "r-post", "kind": "conflicts_with"},
            {"source": "r-post", "target": "r-dlq", "kind": "related"},
            {"source": "r-retry", "target": "doc-http", "kind": "sources"},
            {"source": "r-post", "target": "doc-api", "kind": "sources"},
            {"source": "r-dlq", "target": "doc-q", "kind": "sources"},
        ],
    },
    "case_c": {
        "nodes": [
            {"id": "r-new", "kind": "rule", "label": "r-ts-tz", "claim": "timestamptz in DB", "status": "active", "scope": ["aurora", "interface"]},
            {"id": "r-old", "kind": "rule", "label": "r-ts-iso", "claim": "ISO8601 strings", "status": "superseded", "scope": ["aurora", "interface"]},
            {"id": "doc-db", "kind": "document", "label": "04-database", "path": "docs/04-database.md"},
            {"id": "doc-api", "kind": "document", "label": "05-api-design", "path": "docs/05-api-design.md"},
        ],
        "edges": [
            {"source": "r-new", "target": "r-old", "kind": "supersedes"},
            {"source": "r-new", "target": "doc-db", "kind": "sources"},
            {"source": "r-new", "target": "doc-api", "kind": "sources"},
        ],
    },
    "case_d": {
        "nodes": [
            {"id": "r-cache", "kind": "rule", "label": "r-cache-auth", "claim": "Cache authority", "status": "active", "scope": ["aurora", "performance"]},
            {"id": "r-flag", "kind": "rule", "label": "r-feature-exp", "claim": "Feature flag TTL", "status": "active", "scope": ["aurora", "config"]},
            {"id": "doc-perf", "kind": "document", "label": "10-performance", "path": "docs/10-performance.md", "heading": "缓存策略"},
            {"id": "doc-cfg", "kind": "document", "label": "14-config", "path": "docs/14-config.md"},
            {"id": "doc-dep", "kind": "document", "label": "08-deployment", "path": "docs/08-deployment.md"},
        ],
        "edges": [
            {"source": "r-cache", "target": "doc-perf", "kind": "sources"},
            {"source": "r-flag", "target": "r-cache", "kind": "related"},
            {"source": "r-flag", "target": "doc-cfg", "kind": "sources"},
        ],
    },
    "case_e": {
        "nodes": [
            {"id": "r-name", "kind": "rule", "label": "命名", "claim": "snake / Pascal", "status": "active", "scope": ["aurora", "python"]},
            {"id": "r-ruff", "kind": "rule", "label": "ruff-mypy", "claim": "CI clean", "status": "active", "scope": ["aurora", "quality"]},
            {"id": "r-log", "kind": "rule", "label": "log-redact", "claim": "Log redact", "status": "active", "scope": ["aurora", "logging"]},
            {"id": "r-cap", "kind": "rule", "label": "capacity-70", "claim": "Pool watermark", "status": "active", "scope": ["aurora", "ops"]},
            {"id": "r-lim", "kind": "rule", "label": "rate-limit", "claim": "Rate limit", "status": "active", "scope": ["aurora", "performance"]},
            {"id": "doc-py", "kind": "document", "label": "01-python-style", "path": "docs/01-python-style.md"},
            {"id": "doc-test", "kind": "document", "label": "07-testing", "path": "docs/07-testing.md"},
            {"id": "doc-log", "kind": "document", "label": "06-logging", "path": "docs/06-logging.md"},
            {"id": "doc-obs", "kind": "document", "label": "11-observability", "path": "docs/11-observability.md"},
        ],
        "edges": [
            {"source": "r-ruff", "target": "r-log", "kind": "related"},
            {"source": "r-cap", "target": "r-lim", "kind": "related"},
            {"source": "r-name", "target": "doc-py", "kind": "sources"},
            {"source": "r-ruff", "target": "doc-test", "kind": "sources"},
            {"source": "r-log", "target": "doc-log", "kind": "sources"},
            {"source": "r-cap", "target": "doc-obs", "kind": "sources"},
        ],
    },
}
