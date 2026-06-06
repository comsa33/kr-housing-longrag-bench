#!/usr/bin/env python3
"""v0.7 provider-agnostic LLM baseline runner (scaffold).

Generates prediction JSONL compatible with scripts/eval_harness_v06.py:

    {"qa_id": "...", "prediction": "..."}

from the PUBLIC locator-only prompt file (data/qa_v0.6_prompts.jsonl). The prompt carries the
instruction + question + `context_spec` locators (where the evidence is) but NO raw document text — so
this runner is a closed-book / locator-only baseline. A later INTERNAL full-context mode (embedding bundle
text) would be a separate, explicitly-requested addition.

Supported providers: openai, azure_openai, anthropic, gemini, ollama.

Safety / policy:
  * Predictions, run logs, and metadata are written ONLY under workspace_local/audit/baselines/
    (gitignored). The runner refuses an --out path outside workspace_local/.
  * Splits dev and test_public only. test_hidden requires the explicit INTERNAL flag
    --allow-internal-hidden (clearly marked internal; never publish hidden predictions/answers).
  * --dry-run prints the planned requests WITHOUT importing any SDK, reading any key, or calling an API.
  * --mock runs the full loop with a deterministic fake response (no SDK / no key) so the
    runner -> write -> eval loop is smoke-testable offline.
  * Provider SDKs are OPTIONAL (pyproject extra `baseline`) and imported lazily inside each adapter, so
    --help / --dry-run work with a plain python3 and no SDKs installed.

This is a baseline *scaffold*. It does not assert leaderboard-ready, human-validated, sealed-hidden,
perfect, or hallucination-free results.

Examples:
    python3 scripts/run_llm_baseline_v07.py --provider openai --model gpt-4o-mini --split dev --limit 3 --dry-run
    python3 scripts/run_llm_baseline_v07.py --provider ollama --model llama3.1 --split dev --limit 3 --mock
    python3 scripts/eval_harness_v06.py --pred workspace_local/audit/baselines/<file>.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_FILE = "data/qa_v0.6_prompts.jsonl"
BASELINES_DIR = ROOT / "workspace_local" / "audit" / "baselines"
PUBLIC_SPLITS = ("dev", "test_public")
INTERNAL_SPLITS = ("test_hidden",)
PROVIDERS = ("openai", "azure_openai", "anthropic", "gemini", "ollama")
MOCK_PREDICTION = "[MOCK] locator-only baseline placeholder — no model was called"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- prompt construction
def build_prompt(rec: dict) -> str:
    """Deterministic, simple closed-book prompt: instruction + question + locator hints (no doc text)."""
    instr = rec.get("instruction", "주어진 근거 자료로 질문에 답하라.")
    question = rec.get("question", "")
    spec = rec.get("context_spec", {}) or {}

    def _ids(key: str, limit: int = 20) -> str:
        vals = spec.get(key) or []
        if not isinstance(vals, list):
            vals = [vals]
        if not vals:
            return ""
        shown = vals[:limit]
        more = f" (+{len(vals) - limit} more)" if len(vals) > limit else ""
        return ", ".join(str(v) for v in shown) + more

    lines = []
    for label, key in (
        ("retrieval_mode", "retrieval_mode"),
        ("source_ids", "source_ids"),
        ("page_ids", "page_ids"),
        ("row_ids", "row_ids"),
        ("table_ids", "table_ids"),
        ("cell_ids", "cell_ids"),
        ("bundle_id", "bundle_id"),
        ("context_tier", "context_tier"),
        ("evidence_position", "evidence_position"),
        ("predicate_source", "predicate_source"),
    ):
        if key in ("retrieval_mode", "bundle_id", "context_tier", "evidence_position", "predicate_source"):
            v = spec.get(key)
            if v:
                lines.append(f"- {label}: {v}")
        else:
            s = _ids(key)
            if s:
                lines.append(f"- {label}: {s}")
    locator_block = "\n".join(lines) if lines else "- (근거 위치 메타데이터 없음)"

    return (
        f"{instr}\n\n"
        f"[질문]\n{question}\n\n"
        f"[근거 위치 정보] (원문 텍스트는 제공되지 않습니다. 아래 위치 식별자만 참고하세요.)\n"
        f"{locator_block}\n\n"
        f"[지시] 추측을 최소화하고, 답을 알 수 없으면 '제공된 자료만으로는 확정할 수 없음'이라고 답하세요. "
        f"군더더기 없이 최종 답만 간단히 출력하세요."
    )


# --------------------------------------------------------------------------- provider adapters
class BaseProvider:
    name = "base"

    def __init__(self, model: str, temperature: float, max_output_tokens: int, mock: bool = False,
                 reasoning: bool | None = None):
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.mock = mock
        # None = auto-detect reasoning model from the name; True/False = force (for Azure, where the
        # deployment name may not reveal the underlying model).
        self.reasoning = reasoning
        self._client = None

    def required_env(self) -> list[str]:
        return []

    def env_help(self) -> str:
        return ""

    def missing_env(self) -> list[str]:
        return [v for v in self.required_env() if not os.environ.get(v)]

    def ensure_ready(self) -> None:
        """Validate env + lazily build the client. Not called in --dry-run / --mock."""
        miss = self.missing_env()
        if miss:
            raise SystemExit(
                f"[{self.name}] missing required environment variable(s): {', '.join(miss)}\n"
                f"{self.env_help()}"
            )
        self._init_client()

    def _init_client(self) -> None:  # pragma: no cover - exercised only with SDK + keys
        raise NotImplementedError

    def generate(self, prompt: str) -> str:
        if self.mock:
            return MOCK_PREDICTION
        return self._generate(prompt)

    def _generate(self, prompt: str) -> str:  # pragma: no cover - exercised only with SDK + keys
        raise NotImplementedError


def _openai_reasoning_model(model: str) -> bool:
    """Newer OpenAI 'reasoning' models (gpt-5*, o1/o3/o4*) require `max_completion_tokens` (and reject
    `max_tokens`); many also reject a non-default `temperature`, so we omit it for them."""
    m = model.lower()
    return m.startswith("gpt-5") or m.startswith("o1") or m.startswith("o3") or m.startswith("o4")


def _openai_chat_kwargs(model: str, prompt: str, temperature: float, max_output_tokens: int,
                        reasoning: bool | None = None) -> dict:
    """Shared OpenAI/Azure chat.completions kwargs, switching params for reasoning models.

    reasoning: None = auto-detect from the model name; True/False = force. Use the explicit form for
    Azure, where --model is an arbitrary deployment name the name heuristic cannot classify (e.g. a
    deployment named `prod-baseline` backed by a gpt-5/o-series model)."""
    is_reasoning = _openai_reasoning_model(model) if reasoning is None else reasoning
    kw = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if is_reasoning:
        kw["max_completion_tokens"] = max_output_tokens  # reasoning model; temperature left at default
    else:
        kw["max_tokens"] = max_output_tokens
        kw["temperature"] = temperature
    return kw


class OpenAIProvider(BaseProvider):
    name = "openai"

    def required_env(self):
        return ["OPENAI_API_KEY"]

    def env_help(self):
        return "Set OPENAI_API_KEY. Install the SDK with: pip install 'kr-housing-longrag-bench[baseline]' (or pip install openai)."

    def _init_client(self):
        import openai  # lazy

        self._client = openai.OpenAI()

    def _generate(self, prompt):
        resp = self._client.chat.completions.create(
            **_openai_chat_kwargs(self.model, prompt, self.temperature, self.max_output_tokens, self.reasoning)
        )
        return (resp.choices[0].message.content or "").strip()


class AzureOpenAIProvider(BaseProvider):
    name = "azure_openai"

    def required_env(self):
        return ["AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_VERSION"]

    def env_help(self):
        return (
            "Set AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION. "
            "--model is the Azure DEPLOYMENT name. Install: pip install 'kr-housing-longrag-bench[baseline]' (openai SDK)."
        )

    def _init_client(self):
        from openai import AzureOpenAI  # lazy

        self._client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ["AZURE_OPENAI_API_VERSION"],
        )

    def _generate(self, prompt):
        # model = Azure deployment name; reasoning detection is best-effort on the deployment name.
        resp = self._client.chat.completions.create(
            **_openai_chat_kwargs(self.model, prompt, self.temperature, self.max_output_tokens, self.reasoning)
        )
        return (resp.choices[0].message.content or "").strip()


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def required_env(self):
        return ["ANTHROPIC_API_KEY"]

    def env_help(self):
        return "Set ANTHROPIC_API_KEY. Install: pip install 'kr-housing-longrag-bench[baseline]' (or pip install anthropic)."

    def _init_client(self):
        import anthropic  # lazy

        self._client = anthropic.Anthropic()

    def _generate(self, prompt):
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=self.max_output_tokens,
            temperature=self.temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return ("".join(parts)).strip()


class GeminiProvider(BaseProvider):
    name = "gemini"

    def required_env(self):
        # Either GEMINI_API_KEY or GOOGLE_API_KEY is acceptable (handled in missing_env).
        return ["GEMINI_API_KEY", "GOOGLE_API_KEY"]

    def env_help(self):
        return (
            "Set GEMINI_API_KEY or GOOGLE_API_KEY. "
            "Install: pip install 'kr-housing-longrag-bench[baseline]' (or pip install google-generativeai)."
        )

    def missing_env(self):
        if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
            return []
        return ["GEMINI_API_KEY or GOOGLE_API_KEY"]

    def _init_client(self):
        import google.generativeai as genai  # lazy

        genai.configure(api_key=os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
        self._client = genai.GenerativeModel(self.model)

    def _generate(self, prompt):
        resp = self._client.generate_content(
            prompt,
            generation_config={
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            },
        )
        return (getattr(resp, "text", "") or "").strip()


class OllamaProvider(BaseProvider):
    """Local Ollama server via stdlib HTTP (no third-party SDK, no API key)."""

    name = "ollama"

    def base_url(self) -> str:
        return os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")

    def required_env(self):
        return []  # OLLAMA_BASE_URL is optional (defaults to http://localhost:11434)

    def env_help(self):
        return "Optionally set OLLAMA_BASE_URL (default http://localhost:11434). Start a local server: `ollama serve`."

    def _init_client(self):
        # Fail fast at startup if the server is unreachable (a setup error) so we don't log one
        # failure per prompt. Transient per-request errors during the run raise RuntimeError instead
        # (caught by the per-item handler in main()).
        self._client = self.base_url()
        try:
            urllib.request.urlopen(self.base_url(), timeout=5)
        except urllib.error.HTTPError:
            pass  # server responded (reachable) even if the root path is non-200
        except urllib.error.URLError as exc:  # pragma: no cover - needs a live server
            raise SystemExit(
                f"[ollama] cannot reach server at {self.base_url()}: {exc}. Start it with `ollama serve`."
            )

    def _generate(self, prompt):
        body = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self.temperature, "num_predict": self.max_output_tokens},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url()}/api/generate", data=body, headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
        except urllib.error.URLError as exc:  # pragma: no cover - needs a live server
            # per-request failure: RuntimeError so main()'s per-item handler logs it and continues
            raise RuntimeError(
                f"[ollama] request to {self.base_url()} failed: {exc}. Is `ollama serve` running and the model pulled?"
            )
        return str(data.get("response", "")).strip()


PROVIDER_CLASSES = {
    "openai": OpenAIProvider,
    "azure_openai": AzureOpenAIProvider,
    "anthropic": AnthropicProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


_REASONING_OVERRIDE = {"auto": None, "on": True, "off": False}


def make_provider(args) -> BaseProvider:
    cls = PROVIDER_CLASSES[args.provider]
    return cls(args.model, args.temperature, args.max_output_tokens, mock=args.mock,
               reasoning=_REASONING_OVERRIDE[getattr(args, "reasoning", "auto")])


# --------------------------------------------------------------------------- io helpers
def safe_name(s: str) -> str:
    return "".join(c if (c.isalnum() or c in "-._") else "-" for c in s)


def resolve_out_path(args) -> Path:
    if args.out:
        out = Path(args.out)
        if not out.is_absolute():
            out = ROOT / out
        out = out.resolve()
        # Enforce: predictions only under workspace_local/ (gitignored).
        wl = (ROOT / "workspace_local").resolve()
        if not out.is_relative_to(wl):
            raise SystemExit(
                f"--out must be under workspace_local/ (predictions are internal). Got: {out}"
            )
        return out
    fname = f"{args.provider}_{safe_name(args.model)}_{args.split}.jsonl"
    return BASELINES_DIR / fname


def load_prompt_records(args) -> list[dict]:
    path = ROOT / args.prompt_file if not Path(args.prompt_file).is_absolute() else Path(args.prompt_file)
    if not path.exists():
        raise SystemExit(f"prompt file not found: {path} (run scripts/make_prompt_v06.py first)")
    recs = []
    for line in path.open(encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("split") == args.split:
            recs.append(r)
    if args.limit is not None:
        recs = recs[: args.limit]
    return recs


def already_done(out_path: Path) -> set:
    done = set()
    if out_path.exists():
        for line in out_path.open(encoding="utf-8"):
            if line.strip():
                try:
                    done.add(json.loads(line)["qa_id"])
                except (json.JSONDecodeError, KeyError):
                    continue
    return done


# --------------------------------------------------------------------------- main
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="v0.7 provider-agnostic LLM baseline runner (scaffold).")
    ap.add_argument("--provider", required=True, choices=PROVIDERS)
    ap.add_argument("--model", required=True, help="model name (Azure: deployment name)")
    ap.add_argument("--split", required=True, choices=list(PUBLIC_SPLITS) + list(INTERNAL_SPLITS))
    ap.add_argument("--prompt-file", default=DEFAULT_PROMPT_FILE)
    ap.add_argument("--out", default=None, help="output JSONL (must be under workspace_local/); default auto")
    ap.add_argument("--limit", type=int, default=None, help="only the first N prompts (smoke tests)")
    ap.add_argument("--dry-run", action="store_true", help="print planned requests; no SDK/key/API calls")
    ap.add_argument("--mock", action="store_true", help="run the loop with a deterministic fake response (offline)")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-output-tokens", type=int, default=512)
    ap.add_argument("--reasoning", choices=["auto", "on", "off"], default="auto",
                    help="OpenAI/Azure token-param mode: auto = detect reasoning models (gpt-5*/o-series) "
                         "by name; on/off = force (use for Azure deployments whose name hides the model).")
    ap.add_argument("--resume", action="store_true", help="skip qa_ids already present in the output file")
    ap.add_argument("--sleep-seconds", type=float, default=0.0, help="pause between calls (rate limiting)")
    ap.add_argument(
        "--allow-internal-hidden",
        action="store_true",
        help="INTERNAL ONLY: permit --split test_hidden. Hidden predictions stay internal; never publish them.",
    )
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    if args.split in INTERNAL_SPLITS and not args.allow_internal_hidden:
        print(
            f"refusing --split {args.split}: hidden split is INTERNAL. "
            f"Re-run with --allow-internal-hidden only for internal use (never publish hidden predictions).",
            file=sys.stderr,
        )
        return 2
    if args.dry_run and args.mock:
        print("choose at most one of --dry-run / --mock", file=sys.stderr)
        return 2

    records = load_prompt_records(args)
    out_path = resolve_out_path(args)
    provider = make_provider(args)

    if args.dry_run:
        print(f"== DRY RUN — provider={args.provider} model={args.model} split={args.split} ==")
        print(f"prompt_file: {args.prompt_file}")
        print(f"planned out: {out_path.relative_to(ROOT) if ROOT in out_path.parents else out_path}")
        print(f"temperature={args.temperature} max_output_tokens={args.max_output_tokens} "
              f"limit={args.limit} planned_requests={len(records)}")
        for i, r in enumerate(records, 1):
            prompt = build_prompt(r)
            preview = prompt.replace("\n", " ")[:160]
            print(f"  [{i}] qa_id={r.get('qa_id')} task={r.get('task_type')} prompt~= {preview}…")
        print("== no SDK imported, no API called, no files written ==")
        return 0

    # Real or mock run: write predictions under workspace_local/audit/baselines/.
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = already_done(out_path) if args.resume else set()
    todo = [r for r in records if r.get("qa_id") not in done]

    if not args.mock:
        provider.ensure_ready()  # env check + lazy SDK/client; clear error if missing

    log_path = out_path.with_suffix(".log")
    meta_path = out_path.with_suffix(".meta.json")
    started = now_iso()
    written, errors = 0, 0

    mode = "w" if not args.resume else "a"
    with out_path.open(mode, encoding="utf-8") as out_f, log_path.open(mode, encoding="utf-8") as log_f:
        log_f.write(f"# run start {started} provider={args.provider} model={args.model} "
                    f"split={args.split} mock={args.mock} todo={len(todo)} (skipped_resume={len(records) - len(todo)})\n")
        for i, r in enumerate(todo, 1):
            qid = r.get("qa_id")
            prompt = build_prompt(r)
            try:
                pred = provider.generate(prompt)
            except SystemExit:
                raise
            except Exception as exc:  # noqa: BLE001 - per-item resilience; logged, qa_id left for --resume
                errors += 1
                log_f.write(f"{now_iso()} ERROR qa_id={qid}: {exc!r}\n")
                log_f.flush()
                continue
            out_f.write(json.dumps({"qa_id": qid, "prediction": pred}, ensure_ascii=False) + "\n")
            out_f.flush()
            written += 1
            if args.sleep_seconds > 0 and i < len(todo):
                time.sleep(args.sleep_seconds)
    finished = now_iso()

    metadata = {
        "provider": args.provider,
        "model": args.model,
        "split": args.split,
        "prompt_file": args.prompt_file,
        "out_file": str(out_path.relative_to(ROOT)) if ROOT in out_path.parents else str(out_path),
        "started_at": started,
        "finished_at": finished,
        "limit": args.limit,
        "temperature": args.temperature,
        "max_output_tokens": args.max_output_tokens,
        "mock": args.mock,
        "resume": args.resume,
        "split_prompt_count": len(records),
        "attempted": len(todo),
        "written": written,
        "skipped_resume": len(records) - len(todo),
        "errors": errors,
        "cost_usd": None,  # not computed in this scaffold; record provider invoice separately
        "args": vars(args),
        "argv": sys.argv,
    }
    meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    tag = "MOCK" if args.mock else "LIVE"
    print(f"== baseline run ({tag}) — {written} predictions written, {errors} errors ==")
    print(f"predictions: {out_path.relative_to(ROOT) if ROOT in out_path.parents else out_path}")
    print(f"metadata:    {meta_path.relative_to(ROOT) if ROOT in meta_path.parents else meta_path}")
    print(f"score with:  python3 scripts/eval_harness_v06.py --pred {out_path.relative_to(ROOT) if ROOT in out_path.parents else out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
