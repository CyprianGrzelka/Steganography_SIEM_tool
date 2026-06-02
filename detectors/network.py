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
    SteganographicCostAggregator,
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

            dns_result = self.dns_detector.analyze(queries)
            aggregated = SteganographicCostAggregator().aggregate({"dns": dns_result})

            return SharedResult(
                timestamp=now_iso(),
                source_module="network",
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                file_size_bytes=os.path.getsize(filepath),
                file_format="JSON",
                verdict=aggregated.get("verdict", "CLEAN"),
                risk_score=int(aggregated.get("risk_score", 0)),
                detectors_triggered=aggregated.get("detectors_triggered", 0),
                detectors_total=1,
                detectors={
                    "dns_tunneling": {
                        "confidence": dns_result.get("confidence", 0.0),
                        "detected": dns_result.get("detected", False),
                        "entropy": dns_result.get("entropy"),
                        "subdomain_length": dns_result.get("subdomain_length"),
                        "subdomain_alphabet": dns_result.get("subdomain_alphabet"),
                        "base32_matches": dns_result.get("base32_matches", 0),
                        "query_rate": dns_result.get("query_rate", 0),
                        "domain_concentration": dns_result.get("domain_concentration"),
                    },
                },
                network_channel="dns",
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

    def analyze_pcap(self, filepath: str) -> SharedResult:
        """Analyze PCAP/PCAPng capture for DNS tunneling, ICMP tunneling, and IAT channels."""
        # Lazy import: PcapParser requires dpkt or scapy; avoid breaking JSON analysis
        # if neither library is installed.
        try:
            from pcap_parser import PcapParser
        except ImportError as e:
            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"PCAP library missing (install dpkt or scapy): {e}",
                source_module="network",
            )

        try:
            parsed = PcapParser().parse(filepath)
        except Exception as e:
            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"PCAP parse failed: {e}",
                source_module="network",
            )

        detector_results = {}
        warnings = list(parsed.get("warnings", []))

        if parsed["dns_queries"]:
            detector_results["dns"] = self.dns_detector.analyze(parsed["dns_queries"])
        else:
            warnings.append("No DNS queries in PCAP — DNS detector skipped")

        if parsed["icmp_packets"]:
            detector_results["icmp"] = self.icmp_detector.analyze(parsed["icmp_packets"])
        else:
            warnings.append("No ICMP packets in PCAP — ICMP detector skipped")

        if len(parsed["all_timestamps"]) >= 3:
            detector_results["iat"] = self.iat_detector.analyze(parsed["all_timestamps"])
        else:
            warnings.append("Too few packets for IAT analysis (minimum 3 required)")

        ext = os.path.splitext(filepath)[1].lower()
        file_size = os.path.getsize(filepath)

        pcap_summary = (
            f"PCAP: {parsed['packet_count']} packets, "
            f"{parsed['duration_sec']}s, "
            f"protocols={parsed['protocols_seen']}"
        )
        warnings.insert(0, pcap_summary)
        if parsed.get("skipped_packets", 0):
            warnings.append(f"Skipped {parsed['skipped_packets']} malformed packets")

        if not detector_results:
            return SharedResult(
                timestamp=now_iso(),
                source_module="network",
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                file_size_bytes=file_size,
                file_format=ext.upper().lstrip("."),
                verdict="CLEAN",
                risk_score=0,
                detectors_triggered=0,
                detectors_total=0,
                warnings=warnings + ["No recognized protocols — returning CLEAN"],
                network_channel="pcap",
            )

        aggregated = SteganographicCostAggregator().aggregate(detector_results)

        return SharedResult(
            timestamp=now_iso(),
            source_module="network",
            file_name=os.path.basename(filepath),
            file_path=os.path.abspath(filepath),
            file_size_bytes=file_size,
            file_format=ext.upper().lstrip("."),
            verdict=aggregated.get("verdict", "CLEAN"),
            risk_score=int(aggregated.get("risk_score", 0)),
            detectors_triggered=aggregated.get("detectors_triggered", 0),
            detectors_total=len(detector_results),
            warnings=warnings,
            detectors=aggregated.get("detectors", {}),
            network_channel="pcap",
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

            if ext == ".json":
                return self.analyze_dns_json(filepath)

            if ext in (".pcap", ".pcapng"):
                return self.analyze_pcap(filepath)

            return SharedResult(
                timestamp=now_iso(),
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                verdict="CLEAN",
                risk_score=0,
                errors=f"Unsupported format: {ext}",
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
