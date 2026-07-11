#!/usr/bin/env bash
# One-download "download-and-run" release package.
# Ships parsed context bundles + EVAL pipeline only (no acquire/extract/build-bundle
# code — that's for rebuild-from-raw, unneeded once bundles are shipped).
# Bundles are md5-identical to the paper's experiments. Mirrors the
# workspace_local/processed/bundles-v06/ path the eval scripts expect.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/dist/kr-housing-longrag-bench-package}"
BUNDLES="$ROOT/workspace_local/processed/bundles-v06"
EVAL_SCRIPTS=(attach_bundles_v06 build_baseline_fullcontext_v09 build_baseline_rag_v09 \
  build_baseline_sample_v09 make_prompt_v06 run_llm_baseline_v07 run_batch_baseline_v09 \
  fetch_openai_completions_v09 providers_v05 llm_judge_v09 score_judge_v09 score_answers_v09 \
  score_retrieval_v09 run_variance_v09 rag_retrieval_diagnostics_v07 eval_harness_v06 \
  catalog_baselines_v09 validate_dataset verify_qa qa_common qa_v03_common qa_v04_common qa_v05_common)
rm -rf "$OUT"
mkdir -p "$OUT/data" "$OUT/scripts" "$OUT/docs" "$OUT/workspace_local/processed/bundles-v06"
cp "$ROOT"/data/*.jsonl "$ROOT"/data/*.json "$OUT/data/"
cp "$BUNDLES"/*.txt "$OUT/workspace_local/processed/bundles-v06/" 2>/dev/null || true
cp "$BUNDLES"/*.jsonl "$OUT/workspace_local/processed/bundles-v06/" 2>/dev/null || true
for s in "${EVAL_SCRIPTS[@]}"; do cp "$ROOT/scripts/$s.py" "$OUT/scripts/"; done
for d in evaluation_protocol baseline_protocol_v06 public_reconstruction quickstart_v06 license_audit_v09; do
  [ -f "$ROOT/docs/$d.md" ] && cp "$ROOT/docs/$d.md" "$OUT/docs/"
done
mkdir -p "$OUT/workspace_local/audit/baselines"
# locked eval sample (so build_baseline_fullcontext renders prompts out of the box)
cp "$ROOT"/workspace_local/audit/baselines/baseline_sample_v09*.jsonl "$OUT/workspace_local/audit/baselines/" 2>/dev/null || true
cp "$ROOT"/workspace_local/audit/baselines/baseline_sample_v09.manifest.json "$OUT/workspace_local/audit/baselines/" 2>/dev/null || true
cp "$ROOT/LICENSE" "$OUT/LICENSE"
( cd "$OUT/workspace_local/processed/bundles-v06" && \
  { md5sum ./*.txt 2>/dev/null || for f in ./*.txt; do echo "$(md5 -q "$f")  $f"; done; } | sort ) > "$OUT/BUNDLE_CHECKSUMS.md5"
echo "package: $OUT"
echo "  data=$(ls "$OUT"/data|wc -l|tr -d ' ') scripts=$(ls "$OUT"/scripts/*.py|wc -l|tr -d ' ') bundles=$(ls "$OUT"/workspace_local/processed/bundles-v06|wc -l|tr -d ' ') size=$(du -sh "$OUT"|cut -f1)"
