import importlib.util
import json
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location("voice_latency_report", Path(__file__).parents[1] / "scripts" / "voice_latency_report.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class VoiceLatencyReportTests(unittest.TestCase):
    def test_percentiles_and_consent_sample_pairing_are_transcript_free(self):
        rows = [
            {"transcription_provider": "Gnani Cloud", "sample_id": "commands-a-01", "activation_to_final_transcript_ms": 410, "transcription_error": False, "transcript": "private words"},
            {"transcription_provider": "Gnani Cloud", "sample_id": "commands-a-02", "activation_to_final_transcript_ms": 510, "transcription_error": True},
            {"transcription_provider": "Local Whisper", "sample_id": "commands-a-01", "activation_to_final_transcript_ms": 640, "transcription_error": False},
        ]
        result = report.summary(rows)
        self.assertEqual(result["providers"]["Gnani Cloud"]["metrics"]["activation_to_final_transcript_ms"], {"p50_ms": 410.0, "p95_ms": 510.0})
        self.assertEqual(result["providers"]["Gnani Cloud"]["transcription_errors"], 1)
        self.assertEqual(result["paired_sample_ids"], ["commands-a-01"])
        self.assertNotIn("private words", json.dumps(result))
