"""
common.py — SharedResult dataclass i logika werdyktu dla wszystkich detektorów.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any, ClassVar
from datetime import datetime, timezone


_RULE_SHORT: dict = {
    "chi_square":           "chi²",
    "rs_analysis":          "RS",
    "shannon_entropy":      "H",
    "group_parity":         "parity_dev",
    "parity_chi_test":      "parity_chi",
    "dns_entropy":          "DNS_entropy",
    "dns_subdomain_length": "subdomain_len",
    "dns_base32":           "DNS_b32",
    "dns_query_rate":       "DNS_rate",
    "icmp_payload":         "ICMP",
    "iat_periodicity":      "IAT",
}

# Rules whose metric value is a count — formatted as integer, not float
_INT_VALUE_RULES: frozenset = frozenset({"dns_subdomain_length", "dns_base32"})

# Mapping: detector key → (short_label, candidate_metric_fields_tuple, is_int)
# Candidate fields are tried in order; first non-None wins.
# chi_square and rs_analysis differ between image (p_value/rs_difference)
# and video (detection_rate), so both are listed.
_DETECTOR_SHORT: dict = {
    "chi_square":         ("chi²",       ("p_value", "detection_rate"),        False),
    "rs_analysis":        ("RS",         ("rs_difference", "detection_rate"),   False),
    "shannon_entropy":    ("H",          ("entropy",),                          False),
    "temporal":           ("temporal",   ("variance",),                         False),
    "audio_group_parity": ("parity_dev", ("score",),                            False),
    "dns_tunneling":      ("DNS_H",      ("entropy",),                          False),
    "icmp_tunneling":     ("ICMP",       ("confidence",),                       False),
    "iat_steganography":  ("IAT",        ("confidence",),                       False),
}

# Keys in `detectors` dict that are metadata, not detection results — skip in summary
_SKIP_DETECTOR_KEYS: frozenset = frozenset({"video_meta"})


def build_triggered_rules_summary(triggered_rules: list) -> str:
    """Compact display string built from triggered_rules list (rule + value only)."""
    parts = []
    for r in triggered_rules:
        rule = r.get("rule", "")
        short = _RULE_SHORT.get(rule, rule)
        val = r.get("value", 0)
        fmt = str(int(val)) if rule in _INT_VALUE_RULES else f"{val:.3f}"
        parts.append(f"{short}={fmt}")
    return " | ".join(parts)


def build_all_detectors_summary(detectors: dict) -> str:
    """
    Compact summary for events where no rule triggered (CLEAN verdict).
    Shows each detector's primary metric value in the same format as
    build_triggered_rules_summary. Example: "chi²=0.000 | RS=0.008 | H=4.347"
    Metadata-only keys (video_meta) are skipped.
    """
    parts = []
    for det_name, det_data in detectors.items():
        if det_name in _SKIP_DETECTOR_KEYS or not isinstance(det_data, dict):
            continue
        entry = _DETECTOR_SHORT.get(det_name)
        if entry is None:
            short, candidate_fields, is_int = det_name, (), False
        else:
            short, candidate_fields, is_int = entry
        val = None
        for field in candidate_fields:
            val = det_data.get(field)
            if val is not None:
                break
        if val is None:
            val = 0.0
        fmt = str(int(val)) if is_int else f"{float(val):.3f}"
        parts.append(f"{short}={fmt}")
    return " | ".join(parts) if parts else "all_detectors_passed"


@dataclass
class SharedResult:
    """
    Ujednolicony format wyniku z każdego detektora.
    Serializowalny bezpośrednio do JSON.

    Każde zdarzenie (obraz, audio, wideo, sieć) ma identyczne pola najwyższego
    poziomu — null tam gdzie pole nie ma zastosowania.  Dzięki temu Elasticsearch
    buduje spójne mapowanie, a Kibana nie duplikuje wykresów.

    Pola stałe (zawsze obecne):
      timestamp, event_type, source_module,
      file_name, file_path, file_size_bytes, file_format,
      verdict, risk_score, detectors_triggered, detectors_total,
      detectors, warnings, network_channel

    Pole opcjonalne (pomijane gdy None):
      errors  — komunikat błędu analizy
    """
    timestamp: str  # ISO 8601 UTC
    event_type: str = "stego_scan"
    source_module: str = "unknown"  # image | audio | video | network

    # File/source metadata — null for pure network-traffic events
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    file_format: Optional[str] = None

    # Detection results
    verdict: str = "CLEAN"  # CLEAN | SUSPICIOUS | DETECTED
    risk_score: int = 0     # 0-100
    detectors_triggered: int = 0
    detectors_total: int = 0

    # Detector-specific details (structure varies by source_module)
    detectors: Dict[str, Any] = field(default_factory=dict)

    # Ordered list of rules that exceeded their threshold and contributed to the verdict
    triggered_rules: list = field(default_factory=list)

    # Compact display string for Kibana columns — auto-computed in __post_init__
    triggered_rules_summary: str = ""

    # Metadata
    warnings: list = field(default_factory=list)

    # Network-only: which covert channel was analysed
    # null for image / audio / video events
    network_channel: Optional[str] = None

    # Analysis error message — omitted from JSON when None
    errors: Optional[str] = None

    # Ordered list of fields that are always present in the serialised event.
    # Guarantees a consistent Elasticsearch mapping regardless of source_module.
    _SCHEMA_FIELDS: ClassVar[tuple] = (
        "timestamp", "event_type", "source_module",
        "file_name", "file_path", "file_size_bytes", "file_format",
        "verdict", "risk_score", "detectors_triggered", "detectors_total",
        "detectors", "triggered_rules", "triggered_rules_summary", "warnings", "network_channel",
    )

    def __post_init__(self):
        if not self.triggered_rules_summary:
            if self.triggered_rules:
                self.triggered_rules_summary = build_triggered_rules_summary(self.triggered_rules)
            elif self.detectors:
                self.triggered_rules_summary = build_all_detectors_summary(self.detectors)
            else:
                self.triggered_rules_summary = "all_detectors_passed"

    def to_json_dict(self) -> dict:
        """
        Serialize to dict with a fixed field order.

        All _SCHEMA_FIELDS are always present (null when not applicable).
        The 'errors' field is appended only when not None.
        """
        data = asdict(self)
        result = {key: data[key] for key in self._SCHEMA_FIELDS}
        if data["errors"] is not None:
            result["errors"] = data["errors"]
        return result

    def to_ndjson_line(self) -> str:
        """Return single-line JSON suitable for NDJSON format."""
        return json.dumps(self.to_json_dict(), ensure_ascii=False)


def get_verdict(
    detectors_triggered: int,
    risk_score: int,
    detectors_total: int = 3,
) -> str:
    """
    Logika werdyktu dla obrazów/audio/video (CLEAN/SUSPICIOUS/DETECTED).

    Args:
        detectors_triggered: liczba detektorów które dały pozytywny sygnał
        risk_score: łączny risk score 0-100
        detectors_total: ile detektorów uruchomiono (domyślnie 3)

    Returns:
        "CLEAN", "SUSPICIOUS", lub "DETECTED"
    """
    # Dwa lub więcej detektorów → DETECTED
    if detectors_triggered >= 2:
        return "DETECTED"

    # Risk score >= 60 → DETECTED
    if risk_score >= 60:
        return "DETECTED"

    # Żaden detektor + niska ryzyka → CLEAN
    if detectors_triggered == 0 and risk_score < 20:
        return "CLEAN"

    # Pośredni przypadek → SUSPICIOUS
    return "SUSPICIOUS"


def now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()
