"""
network.py — NetworkDetector opakowujący network_stego_detector z steg-lab/
"""

import sys
import os
import json
from pathlib import Path

from .common import SharedResult, now_iso

# Add steg-lab to path for imports
_STEG_LAB = Path(__file__).parent.parent / "steg-lab"
if str(_STEG_LAB) not in sys.path:
    sys.path.insert(0, str(_STEG_LAB))

from network_stego_detector import (
    DnsTunnelingDetector,
    IcmpTunnelingDetector,
    IATStegoDetector,
)


class NetworkDetector:
    """Unified detector for network traffic (DNS, ICMP, IAT steganography)."""

    SUPPORTED_FORMATS = {".json", ".pcap", ".pcapng"}

    def __init__(self):
        self.dns_detector = DnsTunnelingDetector()
        self.icmp_detector = IcmpTunnelingDetector()
        self.iat_detector = IATStegoDetector()

    def analyze_dns_json(self, filepath: str) -> SharedResult:
        """
        Analyze DNS queries from JSON file.

        Expected JSON format: list of dicts with keys:
          - query_name (str)
          - timestamp (float, unix)
          - source_ip (str)
        """
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                queries = json.load(f)

            if not isinstance(queries, list):
                queries = [queries]

            result = self.dns_detector.analyze(queries)

            return SharedResult(
                timestamp=now_iso(),
                source_module="network",
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                file_size_bytes=os.path.getsize(filepath),
                file_format="JSON",
                verdict=result.get("verdict", "CLEAN"),
                risk_score=int(result.get("risk_score", 0)),
                detectors_triggered=result.get("detectors_triggered", 0),
                detectors_total=1,
                detectors={
                    "dns_tunneling": {
                        "confidence": result.get("confidence", 0.0),
                        "detected": result.get("detected", False),
                        "entropy": result.get("entropy"),
                        "subdomain_length": result.get("subdomain_length"),
                        "subdomain_alphabet": result.get("subdomain_alphabet"),
                        "base32_matches": result.get("base32_matches", 0),
                        "rate_confidence": result.get("rate_confidence", 0.0),
                        "rate_anomaly": result.get("rate_anomaly"),
                    },
                },
            )

        except Exception as e:
            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"DNS analysis failed: {str(e)}",
                source_module="network",
            )

    def analyze(self, filepath: str, mode: str = "auto") -> SharedResult:
        """
        Analyze network traffic file.

        Args:
            filepath: path to network traffic file (JSON, PCAP, etc.)
            mode: detection mode ("dns", "icmp", "iat", or "auto")

        Returns:
            SharedResult with detection verdict and risk score
        """
        try:
            if not os.path.exists(filepath):
                return SharedResult(
                    timestamp=now_iso(),
                    file_name=os.path.basename(filepath),
                    file_path=os.path.abspath(filepath),
                    verdict="CLEAN",
                    risk_score=0,
                    errors=f"File not found: {filepath}",
                    source_module="network",
                )

            ext = os.path.splitext(filepath)[1].lower()
            if ext not in self.SUPPORTED_FORMATS:
                return SharedResult(
                    timestamp=now_iso(),
                    file_name=os.path.basename(filepath),
                    file_path=os.path.abspath(filepath),
                    verdict="CLEAN",
                    risk_score=0,
                    errors=f"Unsupported format: {ext}",
                    source_module="network",
                )

            # For now, support DNS JSON analysis
            if ext == ".json":
                return self.analyze_dns_json(filepath)

            # PCAP support would go here
            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"Format {ext} not yet implemented",
                source_module="network",
            )

        except Exception as e:
            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"Analysis failed: {str(e)}",
                source_module="network",
            )
