"""
image.py — ImageDetector opakowujący chi_square, rs_analysis, shannon_entropy
"""

import sys
import os
import io
from pathlib import Path
from PIL import Image

from .common import SharedResult, get_verdict, now_iso

# Add steg-lab to path for imports
_STEG_LAB = Path(__file__).parent.parent / "steg-lab"
if str(_STEG_LAB) not in sys.path:
    sys.path.insert(0, str(_STEG_LAB))

from chi_square import ChiSquareDetector as _ChiSquareDetector
from rs_analysis import RSAnalysisDetector as _RSAnalysisDetector
from shannon_entropy import ShannonEntropyDetector as _ShannonEntropyDetector


class ImageDetector:
    """Unified detector for images using chi-square, RS analysis, and Shannon entropy."""

    SUPPORTED_FORMATS = {".png", ".bmp", ".tiff", ".tif", ".pgm",
                        ".jpg", ".jpeg", ".jfif", ".webp"}
    LOSSY_FORMATS = {".jpg", ".jpeg", ".jfif", ".webp"}

    # Default weights (can be overridden by image_profiler if needed)
    DEFAULT_WEIGHTS = {
        "chi_square": 0.45,
        "rs_analysis": 0.40,
        "shannon_entropy": 0.15,
    }

    def __init__(self):
        self.chi_detector = _ChiSquareDetector(threshold=0.05)
        self.rs_detector = _RSAnalysisDetector(threshold=0.02)
        self.ent_detector = _ShannonEntropyDetector(threshold=7.8)

    def analyze(self, filepath: str) -> SharedResult:
        """
        Analyze image for steganography.

        Args:
            filepath: path to image file

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
                    source_module="image",
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
                    source_module="image",
                )

            stat = os.stat(filepath)
            warnings = []
            pil_image = None

            # Convert lossy formats to PNG in memory for analysis
            if ext in self.LOSSY_FORMATS:
                src = Image.open(filepath)
                buf = io.BytesIO()
                src.convert("RGB").save(buf, format="PNG")
                buf.seek(0)
                pil_image = Image.open(buf)
                pil_image.load()
                warnings.append(
                    f"Format {ext.lstrip('.').upper()} is lossy (DCT/WebP). "
                    "LSBs may have been modified by compression. "
                    "Image converted to PNG in memory before analysis."
                )

            # Run three detectors
            chi_result = self.chi_detector.analyze(filepath, pil_image)
            rs_result = self.rs_detector.analyze(filepath, pil_image)
            ent_result = self.ent_detector.analyze(filepath, pil_image)

            # Calculate risk score
            risk = int(round((
                chi_result["confidence"] * self.DEFAULT_WEIGHTS["chi_square"] +
                rs_result["confidence"] * self.DEFAULT_WEIGHTS["rs_analysis"] +
                ent_result["confidence"] * self.DEFAULT_WEIGHTS["shannon_entropy"]
            ) * 100))

            # Count detectors triggered
            triggered = sum([chi_result["detected"], rs_result["detected"], ent_result["detected"]])

            # Determine verdict
            verdict = get_verdict(triggered, risk, detectors_total=3)

            return SharedResult(
                timestamp=now_iso(),
                source_module="image",
                file_name=os.path.basename(filepath),
                file_path=os.path.abspath(filepath),
                file_size_bytes=stat.st_size,
                file_format=ext.upper().lstrip(".") or "UNKNOWN",
                verdict=verdict,
                risk_score=risk,
                detectors_triggered=triggered,
                detectors_total=3,
                warnings=warnings,
                detectors={
                    "chi_square": {
                        "p_value": chi_result.get("p_value"),
                        "detected": chi_result.get("detected", False),
                        "confidence": chi_result.get("confidence", 0.0),
                    },
                    "rs_analysis": {
                        "rs_difference": rs_result.get("rs_difference"),
                        "detected": rs_result.get("detected", False),
                        "confidence": rs_result.get("confidence", 0.0),
                    },
                    "shannon_entropy": {
                        "entropy": ent_result.get("entropy"),
                        "detected": ent_result.get("detected", False),
                        "confidence": ent_result.get("confidence", 0.0),
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
                errors=f"Analysis failed: {str(e)}",
                source_module="image",
            )
