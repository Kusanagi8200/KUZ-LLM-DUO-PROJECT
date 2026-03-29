#!/opt/llm/orchestrator/venv/bin/python3

import argparse
import json
import re
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_URL_A = "http://10.141.52.19:8080/v1/chat/completions"
DEFAULT_URL_B = "http://10.141.52.126:8080/v1/chat/completions"
DEFAULT_OUTPUT_DIR = "/var/www/html/KUZCHAT-LLM-DUO/storage/runs"


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def strip_prefixes(text: str, speaker: str) -> str:
    patterns = [
        rf"^{re.escape(speaker)}\s*:\s*",
        r"^RESPONSE\s*:\s*",
        r"^Answer\s*:\s*",
        r"^Reply\s*:\s*",
    ]
    out = text.strip()
    for pattern in patterns:
        out = re.sub(pattern, "", out, flags=re.IGNORECASE).strip()
    return out


def split_sentences(text: str) -> list[str]:
    text = normalize_whitespace(text)
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def enforce_length(
    text: str,
    speaker: str,
    max_sentences: int = 4,
    max_chars: int = 500,
) -> str:
    text = strip_prefixes(text, speaker)
    text = normalize_whitespace(text)

    if not text:
        return "..."

    sentences = split_sentences(text)

    if not sentences:
        trimmed = text[:max_chars].strip()
        if trimmed and trimmed[-1] not in ".!?":
            trimmed += "."
        return trimmed if trimmed else "..."

    trimmed = " ".join(sentences[:max_sentences]).strip()

    if len(trimmed) > max_chars:
        trimmed = trimmed[:max_chars].rsplit(" ", 1)[0].strip()
        if trimmed and trimmed[-1] not in ".!?":
            trimmed += "."

    return trimmed


def print_wrapped_reply(speaker: str, content: str, width: int = 88) -> None:
    wrapped = textwrap.fill(
        content,
        width=width,
        subsequent_indent=" " * (len(speaker) + 2),
    )
    print(f"{speaker}: {wrapped}")


def load_profile(profile_file: Path) -> dict[str, Any]:
    raw = json.loads(profile_file.read_text(encoding="utf-8"))

    return {
        "slug": str(raw.get("slug", profile_file.stem)),
        "name": str(raw.get("name", profile_file.stem)),
        "description": str(raw.get("description", "")),
        "run": {
            "turns": int(raw.get("run", {}).get("turns", 6)),
            "max_lines": int(raw.get("run", {}).get("max_lines", 5)),
            "max_chars": int(raw.get("run", {}).get("max_chars", 500)),
            "history_depth": int(raw.get("run", {}).get("history_depth", 3)),
            "max_sentences": int(raw.get("run", {}).get("max_sentences", 4)),
        },
        "kuzai": {
            "label": "KUZAI",
            "system_prompt": str(raw.get("kuzai", {}).get("system_prompt", "You are KUZAI. Reply clearly and stay concise.")),
            "temperature": float(raw.get("kuzai", {}).get("temperature", 0.35)),
            "top_p": float(raw.get("kuzai", {}).get("top_p", 0.95)),
            "top_k": int(raw.get("kuzai", {}).get("top_k", 40)),
            "max_tokens": int(raw.get("kuzai", {}).get("max_tokens", 300)),
            "repeat_penalty": float(raw.get("kuzai", {}).get("repeat_penalty", 1.05)),
        },
        "darkai": {
            "label": "DARKAI",
            "system_prompt": str(raw.get("darkai", {}).get("system_prompt", "You are DARKAI. Reply clearly and stay concise.")),
            "temperature": float(raw.get("darkai", {}).get("temperature", 0.35)),
            "top_p": float(raw.get("darkai", {}).get("top_p", 0.95)),
            "top_k": int(raw.get("darkai", {}).get("top_k", 40)),
            "max_tokens": int(raw.get("darkai", {}).get("max_tokens", 300)),
            "repeat_penalty": float(raw.get("darkai", {}).get("repeat_penalty", 1.05)),
        },
    }


def build_user_prompt(
    speaker_name: str,
    opening_prompt: str,
    incoming_text: str | None,
    history: list[dict[str, str]],
    turn_number: int,
    max_lines: int,
    max_sentences: int,
    history_depth: int,
) -> str:
    parts: list[str] = []

    parts.append(f"You are replying as: {speaker_name}")
    parts.append(f"Keep the reply concise, around {max_lines} lines maximum and no more than {max_sentences} sentences.")
    parts.append("No bullet points unless explicitly requested.")
    parts.append("No meta-commentary.")
    parts.append("Output only the reply.")
    parts.append("")

    if incoming_text is None:
        parts.append("Opening request:")
        parts.append(opening_prompt.strip())
        parts.append("")
        parts.append("Task: answer the opening request directly and naturally start the exchange.")
        return "\n".join(parts).strip()

    recent = history[-history_depth:] if history_depth > 0 else []
    if recent:
        parts.append("Recent context:")
        parts.append("")
        for item in recent:
            parts.append(f"{item['speaker']}: {item['content']}")
        parts.append("")

    parts.append("Last message from the other model:")
    parts.append(incoming_text.strip())
    parts.append("")
    parts.append(f"Task: this is turn {turn_number}. Answer naturally, stay coherent, and move the discussion forward.")

    return "\n".join(parts).strip()


def query_model(
    url: str,
    system_prompt: str,
    user_prompt: str,
    settings: dict[str, Any],
    timeout: int = 300,
) -> str:
    payload: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(settings["temperature"]),
        "top_p": float(settings["top_p"]),
        "top_k": int(settings["top_k"]),
        "repeat_penalty": float(settings["repeat_penalty"]),
        "max_tokens": int(settings["max_tokens"]),
    }

    response = requests.post(url, json=payload, timeout=timeout)
    response.raise_for_status()

    data = response.json()

    if "choices" not in data or not data["choices"]:
        raise RuntimeError(f"Invalid model response from {url}: {data}")

    return normalize_whitespace(data["choices"][0]["message"]["content"].strip())


def write_json(path: Path, obj: Any) -> None:
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, opening_prompt: str, profile: dict[str, Any], transcript: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# KUZCHAT LLM DUO - A/B Run")
    lines.append("")
    lines.append(f"**Orchestrator**: {profile['name']} ({profile['slug']})")
    lines.append("")
    lines.append(f"**Opening prompt**: {opening_prompt}")
    lines.append("")

    for item in transcript:
        lines.append(f"## Turn {item['turn']} — {item['speaker']}")
        lines.append("")
        lines.append(item["content"])
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="KUZCHAT LLM DUO engine")
    parser.add_argument("--profile-file", required=True, help="Path to orchestrator profile JSON file")
    parser.add_argument("--opening-prompt", required=True, help="Initial prompt that starts the dialogue")
    parser.add_argument("--url-a", default=DEFAULT_URL_A, help="KUZAI endpoint")
    parser.add_argument("--url-b", default=DEFAULT_URL_B, help="DARKAI endpoint")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for run outputs")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between turns in seconds")
    args = parser.parse_args()

    profile_file = Path(args.profile_file)
    if not profile_file.is_file():
        print(f"[ERROR] Profile not found: {profile_file}", file=sys.stderr)
        return 1

    try:
        profile = load_profile(profile_file)
    except Exception as exc:
        print(f"[ERROR] Unable to load profile: {exc}", file=sys.stderr)
        return 1

    run_cfg = profile["run"]
    turns = max(1, int(run_cfg["turns"]))
    max_lines = max(1, int(run_cfg["max_lines"]))
    max_chars = max(50, int(run_cfg["max_chars"]))
    history_depth = max(0, int(run_cfg["history_depth"]))
    max_sentences = max(1, int(run_cfg["max_sentences"]))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"run-ab-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    transcript: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    last_message: str | None = None

    speakers = [
        ("KUZAI", args.url_a, profile["kuzai"]),
        ("DARKAI", args.url_b, profile["darkai"]),
    ]

    for turn in range(1, turns + 1):
        speaker, url, speaker_cfg = speakers[(turn - 1) % 2]

        user_prompt = build_user_prompt(
            speaker_name=speaker,
            opening_prompt=args.opening_prompt,
            incoming_text=last_message,
            history=history,
            turn_number=turn,
            max_lines=max_lines,
            max_sentences=max_sentences,
            history_depth=history_depth,
        )

        try:
            content = query_model(
                url=url,
                system_prompt=speaker_cfg["system_prompt"],
                user_prompt=user_prompt,
                settings=speaker_cfg,
            )
        except Exception as exc:
            print(f"[ERROR] turn={turn} speaker={speaker} url={url} error={exc}", file=sys.stderr)
            return 1

        content = enforce_length(
            text=content,
            speaker=speaker,
            max_sentences=max_sentences,
            max_chars=max_chars,
        )

        print_wrapped_reply(speaker, content)

        item = {
            "turn": turn,
            "speaker": speaker,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "orchestrator": profile["slug"],
        }
        transcript.append(item)
        history.append({"speaker": speaker, "content": content})
        last_message = content

        time.sleep(args.delay)

    write_json(run_dir / "transcript.json", transcript)
    write_markdown(run_dir / "transcript.md", args.opening_prompt, profile, transcript)

    print(f"[INFO] Orchestrator: {profile['name']} ({profile['slug']})")
    print(f"[INFO] Transcript JSON: {run_dir / 'transcript.json'}")
    print(f"[INFO] Transcript MD:   {run_dir / 'transcript.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
