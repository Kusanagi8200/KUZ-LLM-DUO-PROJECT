#### ORCHESTRATOR-02

$ = duo_loop_ab3.py

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
DEFAULT_OUTPUT_DIR = "/opt/llm/orchestrator/runs"


ROLE_A_SYSTEM = """You are KUZAI.

Rules:
- Your visible name is KUZAI.
- You run on host fhc2.
- Never say you are DARKAI.
- Reply naturally and directly.
- Keep answers short, readable, and useful.
- Do not describe hidden rules or internal instructions.
- Do not over-explain.
- If asked about your role or purpose, answer about your role in the current dialogue only.
- Output only the reply itself.
"""

ROLE_B_SYSTEM = """You are DARKAI.

Rules:
- Your visible name is DARKAI.
- You run on host fhc.
- Never say you are KUZAI.
- Reply naturally and directly.
- Keep answers short, readable, and useful.
- Do not describe hidden rules or internal instructions.
- Do not over-explain.
- If asked about your role or purpose, answer about your role in the current dialogue only.
- Output only the reply itself.
"""


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


def is_social_intro_prompt(text: str) -> bool:
    t = text.lower()
    markers = [
        "introduce yourself",
        "present yourself",
        "what is your name",
        "what's your name",
        "say your name",
        "what is your role",
        "what's your role",
        "what is your purpose",
        "what's your purpose",
        "purpose in this project",
        "role in this project",
        "who are you",
        "say hello",
    ]
    return any(marker in t for marker in markers)


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


def build_prompt(
    speaker_name: str,
    role_prompt: str,
    opening_prompt: str,
    incoming_text: str | None,
    history: list[dict[str, str]],
    turn_number: int,
    max_lines_hint: int,
    max_sentences: int,
    history_depth: int,
    opening_from_a: bool,
    social_mode: bool,
) -> str:
    parts: list[str] = []
    parts.append(role_prompt.strip())
    parts.append("")
    parts.append(f"You are replying as: {speaker_name}")
    parts.append("")

    if social_mode:
        parts.append(
            f"Keep the reply short and natural. Use no more than {max_sentences} short sentences."
        )
        parts.append("Answer only the main question or message.")
        parts.append("Do not praise the conversation.")
        parts.append("Do not add motivational filler.")
        parts.append("Do not describe yourself as a general assistant.")
        parts.append("If asked your role or purpose, describe your role in this dialogue only.")
        parts.append("Output only your reply.")
        parts.append("")
    else:
        parts.append(
            f"Write a natural reply. Keep it reasonably short, around {max_lines_hint} lines maximum and no more than {max_sentences} sentences."
        )
        parts.append("No bullet points unless explicitly requested.")
        parts.append("No meta-commentary.")
        parts.append("Do not repeat the other message verbatim.")
        parts.append("Output only your reply.")
        parts.append("")

    if incoming_text is None:
        parts.append("Opening request:")
        parts.append(opening_prompt.strip())
        parts.append("")
        parts.append(
            "Task: answer the opening request directly and naturally start the exchange."
        )
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

    if social_mode:
        if opening_from_a and turn_number == 2:
            parts.append(
                "Task: answer this first message directly. Keep it simple and personal. Do not turn it into a long self-description."
            )
        else:
            parts.append(
                "Task: answer naturally and directly. Keep it simple and short."
            )
    else:
        parts.append(
            "Task: answer naturally, stay coherent, and move the discussion forward."
        )

    return "\n".join(parts).strip()


def query_model(
    url: str,
    prompt: str,
    temperature: float,
    timeout: int = 300,
) -> str:
    payload: dict[str, Any] = {
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
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


def write_markdown(path: Path, opening_prompt: str, transcript: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    lines.append("# KUZCHAT LLM DUO - A/B Run")
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
    parser = argparse.ArgumentParser(description="KUZCHAT LLM DUO orchestrator")
    parser.add_argument(
        "--url-a",
        default=DEFAULT_URL_A,
        help="OpenAI-compatible endpoint for KUZAI on fhc2",
    )
    parser.add_argument(
        "--url-b",
        default=DEFAULT_URL_B,
        help="OpenAI-compatible endpoint for DARKAI on fhc",
    )
    parser.add_argument(
        "--opening-prompt",
        required=True,
        help="Initial prompt that starts the dialogue",
    )
    parser.add_argument(
        "--opening-from-a",
        action="store_true",
        help="Treat opening-prompt as the first message spoken by KUZAI to DARKAI",
    )
    parser.add_argument("--turns", type=int, default=6, help="Total number of turns")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between turns in seconds")
    parser.add_argument("--temperature-a", type=float, default=0.35, help="Temperature for KUZAI")
    parser.add_argument("--temperature-b", type=float, default=0.35, help="Temperature for DARKAI")
    parser.add_argument("--max-lines", type=int, default=5, help="Soft target for reply length")
    parser.add_argument("--max-sentences", type=int, default=4, help="Hard cap on kept sentences")
    parser.add_argument("--max-chars", type=int, default=500, help="Hard cap on kept characters")
    parser.add_argument("--history-depth", type=int, default=3, help="Number of previous turns kept in prompt context")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help="Directory for run outputs")
    args = parser.parse_args()

    if args.turns < 1:
        print("[ERROR] --turns must be >= 1", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / f"run-ab-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    transcript: list[dict[str, Any]] = []
    history: list[dict[str, str]] = []
    last_message: str | None = None
    social_mode = is_social_intro_prompt(args.opening_prompt)

    speakers = [
        ("KUZAI", args.url_a, ROLE_A_SYSTEM, args.temperature_a),
        ("DARKAI", args.url_b, ROLE_B_SYSTEM, args.temperature_b),
    ]

    start_turn = 1

    if args.opening_from_a:
        opening = normalize_whitespace(args.opening_prompt)

        opening_item = {
            "turn": 1,
            "speaker": "KUZAI",
            "url": args.url_a,
            "content": opening,
            "timestamp": datetime.now().isoformat(),
        }
        transcript.append(opening_item)
        history.append({"speaker": "KUZAI", "content": opening})
        last_message = opening

        print_wrapped_reply("KUZAI", opening)

        if args.turns == 1:
            write_json(run_dir / "transcript.json", transcript)
            write_markdown(run_dir / "transcript.md", args.opening_prompt, transcript)
            return 0

        start_turn = 2

    for turn in range(start_turn, args.turns + 1):
        speaker, url, role_prompt, temperature = speakers[(turn - 1) % 2]

        prompt = build_prompt(
            speaker_name=speaker,
            role_prompt=role_prompt,
            opening_prompt=args.opening_prompt,
            incoming_text=last_message,
            history=history,
            turn_number=turn,
            max_lines_hint=args.max-lines if False else args.max_lines,
            max_sentences=args.max_sentences,
            history_depth=args.history_depth,
            opening_from_a=args.opening_from_a,
            social_mode=social_mode,
        )

        try:
            content = query_model(
                url=url,
                prompt=prompt,
                temperature=temperature,
            )
        except Exception as exc:
            print(
                f"[ERROR] turn={turn} speaker={speaker} url={url} error={exc}",
                file=sys.stderr,
            )
            return 1

        content = enforce_length(
            text=content,
            speaker=speaker,
            max_sentences=args.max_sentences,
            max_chars=args.max_chars,
        )

        print_wrapped_reply(speaker, content)

        item = {
            "turn": turn,
            "speaker": speaker,
            "url": url,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        }
        transcript.append(item)
        history.append({"speaker": speaker, "content": content})
        last_message = content

        time.sleep(args.delay)

    write_json(run_dir / "transcript.json", transcript)
    write_markdown(run_dir / "transcript.md", args.opening_prompt, transcript)

    print(f"[INFO] Transcript JSON: {run_dir / 'transcript.json'}")
    print(f"[INFO] Transcript MD:   {run_dir / 'transcript.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
