"""Summarise local, privacy-preserving Silly speech timing diagnostics.

This tool never reads recordings or transcripts.  To compare providers on a
consented repeatable command set, launch each run with the same harmless
SILLY_VOICE_SAMPLE_ID (for example ``commands-a-01``), then point this tool at
the resulting ``voice-timings.jsonl`` file.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any


METRICS = (
    "activation_to_final_transcript_ms",
    "final_transcript_to_first_action_ms",
    "activation_to_action_completion_ms",
    "activation_to_completion_ms",
)


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values) - 1, max(0, math.ceil(len(values) * fraction) - 1))]


def rows(path: Path) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                result.append(item)
    except FileNotFoundError:
        pass
    return result


def summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    samples: dict[str, set[str]] = defaultdict(set)
    for item in items:
        provider = item.get("transcription_provider")
        provider = provider if isinstance(provider, str) and provider else "Unknown"
        groups[provider].append(item)
        sample_id = item.get("sample_id")
        if isinstance(sample_id, str) and sample_id:
            samples[sample_id].add(provider)

    providers: dict[str, Any] = {}
    for provider, values in sorted(groups.items()):
        metrics: dict[str, Any] = {}
        for metric in METRICS:
            observed = [float(value[metric]) for value in values if isinstance(value.get(metric), (int, float))]
            metrics[metric] = {"p50_ms": percentile(observed, .50), "p95_ms": percentile(observed, .95)}
        providers[provider] = {
            "samples": len(values),
            "transcription_errors": sum(bool(value.get("transcription_error")) for value in values),
            "metrics": metrics,
        }
    paired = sorted(sample_id for sample_id, providers_seen in samples.items()
                    if any("Gnani" in provider for provider in providers_seen)
                    and any("Local Whisper" in provider for provider in providers_seen))
    return {"providers": providers, "paired_sample_ids": paired}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Silly speech timings without reading audio or transcripts.")
    parser.add_argument("path", type=Path, help="A local voice-timings.jsonl file")
    parser.add_argument("--json", action="store_true", help="Print machine-readable output")
    args = parser.parse_args()
    report = summary(rows(args.path))
    if args.json:
        print(json.dumps(report, indent=2))
        return
    for provider, data in report["providers"].items():
        print(f"{provider}: {data['samples']} samples, {data['transcription_errors']} transcription errors")
        for metric, values in data["metrics"].items():
            print(f"  {metric}: p50={values['p50_ms']} ms p95={values['p95_ms']} ms")
    paired = report["paired_sample_ids"]
    print("Comparable consented sample IDs: " + (", ".join(paired) if paired else "none"))


if __name__ == "__main__":
    main()
