"""
common.py — SharedResult dataclass i logika werdyktu dla wszystkich detektorów.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from datetime import datetime, timezone


@dataclass
class SharedResult:
    """
    Ujednolicony format wyniku z każdego detektora.
    Serializowalny bezpośrednio do JSON.
    """
    timestamp: str  # ISO 8601 UTC
    event_type: str = "stego_scan"
    source_module: str = "unknown"  # image, audio, video, network

    # File/source metadata
    file_name: str = ""
    file_path: str = ""
    file_size_bytes: Optional[int] = None
    file_format: str = ""

    # Detection results
    verdict: str = "CLEAN"  # CLEAN, SUSPICIOUS, DETECTED
    risk_score: int = 0  # 0-100
    detectors_triggered: int = 0
    detectors_total: int = 0

    # Detector-specific fields (dynamic dict for flexibility)
    detectors: Dict[str, Any] = field(default_factory=dict)

    # Additional metadata
    warnings: list = field(default_factory=list)
    errors: Optional[str] = None

    def to_json_dict(self) -> dict:
        """Convert to dict for JSON serialization, excluding None values."""
        data = asdict(self)
        # Remove None values for cleaner JSON
        return {k: v for k, v in data.items() if v is not None or k in ["errors"]}

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
