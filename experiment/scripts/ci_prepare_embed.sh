#!/usr/bin/env bash
# Prepare embed sidecar for CI rerun (venv + model warm + listen on 4174).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SIDECAR="${IMPRINT_EMBED_SIDECAR:-$ROOT/imprint-embed-sidecar}"
IMPRINT="${IMPRINT_BIN:-$ROOT/experiment/bin/imprint}"
CI_DIR="$ROOT/experiment/.embed-ci"

if [[ ! -f "$SIDECAR/samples.py" ]]; then
  echo "missing sidecar at $SIDECAR (set IMPRINT_EMBED_SIDECAR)" >&2
  exit 1
fi

bash "$SIDECAR/scripts/setup.sh"

mkdir -p "$CI_DIR"
SIDECAR_ESC="${SIDECAR//\\/\\\\}"
cat >"$CI_DIR/imprint.yaml" <<EOF
host:
  listen: 127.0.0.1:9470
plugins:
  embed:
    enabled: true
    package: $SIDECAR_ESC
    config:
      port: 4174
      model: BAAI/bge-small-zh-v1.5
      relate_model: cross-encoder/nli-deberta-v3-base
      duplicate_threshold: 0.65
      relate_contradiction_min: 0.40
      relate_entailment_min: 0.35
      relate_bidirectional: true
      duplicate_high_cosine_block: 0.80
      timeout_seconds: 8
EOF

(cd "$CI_DIR" && "$IMPRINT" embed prepare)
(cd "$CI_DIR" && "$IMPRINT" plugin start embed)

deadline=$((SECONDS + 180))
until curl -sf "http://127.0.0.1:4174/health" | grep -q '"ready": true'; do
  if (( SECONDS > deadline )); then
    echo "sidecar not ready after 180s" >&2
    exit 1
  fi
  sleep 2
done
echo "embed sidecar ready"
