"""Token counting for Grok 4.6-class models.

xAI does not publish a Grok 4.6 tokenizer file. Exact counts require the
xAI tokenize API (`client.tokenize.tokenize_text(..., model="grok-4.6")`).

Default (offline, reproducible): Grok-2 tokenizer
(alvarobartt/grok-2-tokenizer), the closest public Grok-family encoder.

  IMPRINT_TOKENIZER=grok2          local Grok-2 (default)
  IMPRINT_TOKENIZER=grok46         xAI API grok-4.6 (needs XAI_API_KEY)
  IMPRINT_TOKENIZER=tiktoken-o200k GPT-4o encoding, for a second baseline
"""
from __future__ import annotations

import os
from functools import lru_cache

GROK2_LABEL = "grok-2-tokenizer（Grok 家族公开编码器；Grok 4.6 官方词表未公开）"
GROK46_LABEL = "xAI tokenize API · grok-4.6"
HF_REPO = "alvarobartt/grok-2-tokenizer"
HF_FILE = "tokenizer.json"


class TokenizerError(RuntimeError):
    pass


def _kind():
    return os.environ.get("IMPRINT_TOKENIZER", "grok2").strip().lower()


def _grok2_encode():
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer
    path = hf_hub_download(HF_REPO, HF_FILE)
    tok = Tokenizer.from_file(path)
    return GROK2_LABEL, lambda s, _tok=tok: _tok.encode(s).ids


def _xai_encode():
    key = os.environ.get("XAI_API_KEY", "").strip()
    if not key:
        raise TokenizerError("IMPRINT_TOKENIZER=grok46 需要环境变量 XAI_API_KEY")
    try:
        from xai_sdk import Client
    except ImportError as exc:
        raise TokenizerError(
            "IMPRINT_TOKENIZER=grok46 需要 pip install xai-sdk"
        ) from exc
    client = Client(api_key=key)

    @lru_cache(maxsize=4096)
    def encode(s: str):
        tokens = client.tokenize.tokenize_text(s or " ", model="grok-4.6")
        return [t.token_id for t in tokens]

    return GROK46_LABEL, encode


@lru_cache(maxsize=1)
def _backend():
    kind = _kind()
    if kind in ("tiktoken", "tiktoken-o200k", "o200k"):
        import tiktoken
        enc = tiktoken.get_encoding("o200k_base")
        return "tiktoken/o200k_base", enc.encode
    if kind in ("grok46", "grok-4.6", "grok4.6", "xai"):
        return _xai_encode()
    try:
        return _grok2_encode()
    except Exception as exc:
        raise TokenizerError(
            "无法加载 Grok-2 tokenizer。请 pip install -r requirements.txt，"
            "并允许 huggingface_hub 下载 alvarobartt/grok-2-tokenizer。"
        ) from exc


def label() -> str:
    name, _ = _backend()
    return name


def encode(text: str):
    _, fn = _backend()
    return fn(text or "")


def count(text: str) -> int:
    return len(encode(text))
