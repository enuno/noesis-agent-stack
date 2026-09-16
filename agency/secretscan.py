"""secretscan.py — shared secret-shape scan for the agency integration.

Single definition of the secret-shape patterns (ralplan nit N3: no dual
regexes). Imported by convert.py (layer 1, generation time) and
validate-specs.py (layer 2, verification time). The apply script carries
the third (runtime assertion) layer in Phase 2.

Scan is shape-based (no live secret values are ever expected in-repo):
it flags credential-ASSIGNMENT shapes, PEM blocks, and well-known key
prefixes. Prose that merely mentions "API keys" does not match.
"""
from __future__ import annotations

import re

# Assignment shape: keyword, optional quotes/spaces, ': ' or '=', then a
# contiguous token of >= 20 credential-ish characters.
_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password|passwd|bearer[_-]?token|"
    r"authorization|private[_-]?key|access[_-]?key|client[_-]?secret)\b"
    r"[\s\"']*[:=][\s\"']*"
    r"([A-Za-z0-9+/=_\-]{20,})"
)

_PEM_BLOCK = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")

_KNOWN_PREFIXES = [
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),          # AWS access key id
    re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"),       # GitHub PAT
    re.compile(r"\bgho_[A-Za-z0-9]{30,}\b"),       # GitHub OAuth
    re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}\b"),  # Slack
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),        # OpenAI-style
    re.compile(r"\bAIza[0-9A-Za-z_\-]{30,}\b"),    # Google API
]


def scan_text(text: str) -> list[str]:
    """Return human-readable findings; empty list means clean."""
    findings: list[str] = []
    for m in _PEM_BLOCK.finditer(text):
        findings.append(f"PEM private key block at offset {m.start()}")
    for m in _ASSIGNMENT.finditer(text):
        findings.append(
            f"credential-assignment shape {m.group(1)!r} at offset {m.start()}"
        )
    for pattern in _KNOWN_PREFIXES:
        for m in pattern.finditer(text):
            findings.append(f"known key prefix at offset {m.start()}")
    return findings


def scan_file(path) -> list[str]:
    text = open(path, encoding="utf-8", errors="replace").read()
    return [f"{path}: {f}" for f in scan_text(text)]
