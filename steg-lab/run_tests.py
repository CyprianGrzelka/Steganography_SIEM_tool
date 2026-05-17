"""
run_tests.py — automatyczny test skanera na obrazach czystych i stego.

Uruchom z folderu steg-lab/:
  python run_tests.py                 # wszystkie progi: 25%, 50%, 75%, 100%
  python run_tests.py --fill 0.50     # tylko jeden wybrany prog

Generuje:
  wyniki_testy.csv
  wyniki_testy.json
"""

import os
import sys
import json
import csv
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scan import scan, SUPPORTED_FORMATS
from lsb_embed import embed_lsb

CLEAN_DIR   = Path(__file__).parent / "sample_images" / "clean"
STEGO_DIR   = Path(__file__).parent / "sample_images" / "stego"
ALL_FILLS   = [0.25, 0.50, 0.75, 1.00]

CSV_FIELDS = [
    "source_file", "label", "fill_ratio", "format", "lossy_source",
    "verdict", "risk_score", "detectors_triggered",
    "chi_detected", "chi_confidence", "chi_p_value",
    "rs_detected",  "rs_confidence",  "rs_difference",
    "ent_detected", "ent_confidence", "ent_entropy",
    "warnings",
]


def get_clean_images() -> list:
    return sorted(
        f for f in CLEAN_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_FORMATS
    )


def create_stego(clean_path: Path, fill_ratio: float) -> Path:
    STEGO_DIR.mkdir(parents=True, exist_ok=True)
    pct = int(fill_ratio * 100)
    stego_path = STEGO_DIR / f"{clean_path.stem}_stego_{pct:03d}pct.png"
    embed_lsb(str(clean_path), str(stego_path), fill_ratio=fill_ratio)
    return stego_path


def report_to_row(report: dict, label: str, source_file: str, fill_ratio: float) -> dict:
    if "error" in report:
        return {f: "" for f in CSV_FIELDS} | {
            "source_file": source_file,
            "label":       label,
            "fill_ratio":  fill_ratio,
            "verdict":     "ERROR",
            "warnings":    report["error"],
        }
    d = report["detectors"]
    return {
        "source_file":         source_file,
        "label":               label,
        "fill_ratio":          fill_ratio,
        "format":              report["file"]["format"],
        "lossy_source":        report["file"]["lossy_source"],
        "verdict":             report["verdict"],
        "risk_score":          report["risk_score"],
        "detectors_triggered": report["detectors_triggered"],
        "chi_detected":        d["chi_square"]["detected"],
        "chi_confidence":      d["chi_square"]["confidence"],
        "chi_p_value":         d["chi_square"]["p_value"],
        "rs_detected":         d["rs_analysis"]["detected"],
        "rs_confidence":       d["rs_analysis"]["confidence"],
        "rs_difference":       d["rs_analysis"]["rs_difference"],
        "ent_detected":        d["shannon_entropy"]["detected"],
        "ent_confidence":      d["shannon_entropy"]["confidence"],
        "ent_entropy":         d["shannon_entropy"]["entropy"],
        "warnings":            "; ".join(report.get("warnings", [])),
    }


def print_fill_stats(csv_rows: list, fills: list):
    false_pos = sum(
        1 for r in csv_rows
        if r["label"] == "clean" and r["verdict"] == "DETECTED"
    )
    n_clean = sum(1 for r in csv_rows if r["label"] == "clean")
    print(f"\nStatystyki detekcji stego:")
    print(f"  {'Fill':>5}  {'DETECTED':>8}  {'SUSPICIOUS':>10}  {'MISSED':>6}")
    print("  " + "-" * 36)
    for fill in fills:
        stego = [r for r in csv_rows if r["label"] == "stego" and r["fill_ratio"] == fill]
        det  = sum(1 for r in stego if r["verdict"] == "DETECTED")
        sus  = sum(1 for r in stego if r["verdict"] == "SUSPICIOUS")
        mis  = sum(1 for r in stego if r["verdict"] == "CLEAN")
        print(f"  {fill:>4.0%}  {det:>8}  {sus:>10}  {mis:>6}")
    print(f"\n  Falszywe pozytywy (clean -> DETECTED): {false_pos} / {n_clean}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fill", type=float, default=None,
        help="Pojedynczy prog wypelnienia 0.0-1.0. Bez argumentu: 0.25 0.50 0.75 1.00"
    )
    args = parser.parse_args()

    if args.fill is not None:
        if not (0.0 < args.fill <= 1.0):
            print(f"Blad: --fill musi byc z przedzialu (0, 1]. Podano: {args.fill}")
            sys.exit(1)
        fills = [args.fill]
    else:
        fills = ALL_FILLS

    clean_images = get_clean_images()
    if not clean_images:
        print(f"Brak obrazow w {CLEAN_DIR}")
        sys.exit(1)

    fills_str = "  ".join(f"{f:.0%}" for f in fills)
    print(f"Obrazy: {len(clean_images)}  |  Progi: {fills_str}\n")

    all_reports = []
    csv_rows    = []

    # ── Skan czystych obrazow — tylko raz ────────────────────────────
    print("== Czyste obrazy ==")
    for clean_path in clean_images:
        report = scan(str(clean_path))
        report["_test_label"] = "clean"
        all_reports.append(report)
        csv_rows.append(report_to_row(report, "clean", clean_path.name, fill_ratio=0.0))
        verdict = report.get("verdict", "ERROR")
        risk    = report.get("risk_score", "-")
        print(f"  {clean_path.name:<40} {verdict:<10} risk={risk}")

    # ── Stego per prog wypelnienia ────────────────────────────────────
    for fill in fills:
        print(f"\n== Stego {fill:.0%} ==")
        for clean_path in clean_images:
            stego_path = create_stego(clean_path, fill)
            report = scan(str(stego_path))
            report["_test_label"] = f"stego_{fill:.0%}"
            all_reports.append(report)
            csv_rows.append(report_to_row(report, "stego", clean_path.name, fill_ratio=fill))
            verdict = report.get("verdict", "ERROR")
            risk    = report.get("risk_score", "-")
            print(f"  {clean_path.name:<40} {verdict:<10} risk={risk:<4}  {stego_path.name}")

    # ── Zapis wynikow ─────────────────────────────────────────────────
    out_json = Path(__file__).parent / "wyniki_testy.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(all_reports, f, indent=2, ensure_ascii=False)

    out_csv = Path(__file__).parent / "wyniki_testy.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"\n{'=' * 55}")
    print(f"Zapisano: {out_json.name}  ({len(all_reports)} rekordow)")
    print(f"Zapisano: {out_csv.name}")

    print_fill_stats(csv_rows, fills)


if __name__ == "__main__":
    main()
