"""
Moduł profilowania obrazu — uruchamiany PRZED detektorami.

Mierzy cechy obrazu które wpływają na wiarygodność każdego algorytmu
i zwraca skorygowane wagi detektorów.

Przykład użycia:
    from image_profiler import profile_image
    profile = profile_image("foto.png")
    # profile["weights"] zastępuje domyślne wagi w scannerze
"""

import os
import numpy as np
from PIL import Image


# Domyślne wagi detektorów (gdy obraz jest "normalny")
DEFAULT_WEIGHTS = {
    "chi_square":      0.45,
    "rs_analysis":     0.40,
    "shannon_entropy": 0.15,
}


def profile_image(filepath: str) -> dict:
    """
    Profiluje obraz i zwraca słownik z cechami oraz skorygowanymi wagami.

    Zwracane pola:
      format          — PNG / JPEG / BMP itd.
      size_px         — liczba pikseli
      is_grayscale    — czy obraz jest jednobarwny
      saturation_high — % pikseli przy wartości 255 (jasne nasycenie)
      saturation_low  — % pikseli przy wartości 0 (ciemne nasycenie)
      histogram_cv    — współczynnik zmienności histogramu (0=płaski, 1=szpikaty)
      mean_brightness — średnia jasność 0–255
      std_brightness  — odchylenie standardowe jasności
      warnings        — lista ostrzeżeń (co może zaburzać detekcję)
      weights         — skorygowane wagi detektorów
      reliability     — ocena wiarygodności per detektor: "high"/"medium"/"low"
    """
    img = Image.open(filepath)
    fmt = img.format or os.path.splitext(filepath)[1].upper().lstrip(".")

    # Grayscale do analizy statystycznej
    gray = np.array(img.convert("L"), dtype=np.float32).flatten()
    n_pixels = len(gray)

    # ── Cechy podstawowe ──────────────────────────────────────────
    sat_high = float(np.sum(gray == 255) / n_pixels)  # % pikseli = 255
    sat_low  = float(np.sum(gray == 0)   / n_pixels)  # % pikseli = 0
    mean_b   = float(np.mean(gray))
    std_b    = float(np.std(gray))

    # Histogram i jego jednorodność
    hist = np.bincount(gray.astype(np.uint8), minlength=256).astype(float)
    # Współczynnik zmienności: niski = jednorodny (płaski), wysoki = szpikaty (naturalny)
    hist_cv = float(np.std(hist) / (np.mean(hist) + 1e-9))

    is_grayscale = (img.mode in ("L", "P", "LA"))

    # ── Oceń wiarygodność każdego detektora ───────────────────────

    warnings  = []
    weights   = DEFAULT_WEIGHTS.copy()
    reliability = {
        "chi_square":      "high",
        "rs_analysis":     "high",
        "shannon_entropy": "high",
    }

    # 1. Nasycenie jasne → problemy RS analysis (maska -M nie działa na 255)
    if sat_high > 0.5:
        warnings.append(
            f"Wysoka saturacja jasna ({sat_high:.0%} pikseli = 255) — "
            f"RS analysis mało wiarygodny (Unusable bloków: ~{sat_high:.0%})"
        )
        # Zmniejszamy wagę RS, zwiększamy chi-square
        weights["rs_analysis"]    = 0.10
        weights["chi_square"]     = 0.70
        weights["shannon_entropy"] = 0.20
        reliability["rs_analysis"] = "low"

    elif sat_high > 0.2:
        warnings.append(
            f"Podwyższona saturacja jasna ({sat_high:.0%} pikseli = 255) — "
            f"RS analysis częściowo zaburzony"
        )
        weights["rs_analysis"]    = 0.25
        weights["chi_square"]     = 0.55
        weights["shannon_entropy"] = 0.20
        reliability["rs_analysis"] = "medium"

    # 2. Format JPEG → chi-square mniej wiarygodny (DCT już zaburza pary pikseli)
    if fmt in ("JPEG", "JPG"):
        warnings.append(
            "Format JPEG — kompresja DCT zaburza pary pikseli PoV. "
            "Chi-square może dawać fałszywe alarmy. Zalecany PNG."
        )
        weights["chi_square"]     = max(0.20, weights["chi_square"] - 0.20)
        weights["rs_analysis"]    = min(0.60, weights["rs_analysis"] + 0.10)
        weights["shannon_entropy"] = min(0.30, weights["shannon_entropy"] + 0.10)
        reliability["chi_square"] = "medium"

    # 3. Mały obraz → słaba statystyka
    if n_pixels < 40_000:   # mniej niż ~200x200
        warnings.append(
            f"Mały obraz ({n_pixels:,} pikseli) — "
            f"statystyki mogą być niewiarygodne (zalecane min. 200×200)"
        )
        for k in reliability:
            reliability[k] = "low" if reliability[k] == "medium" else reliability[k]

    # 4. Bardzo jednorodny histogram → chi-square może fałszywie alarmować
    if hist_cv < 0.3:
        warnings.append(
            f"Jednorodny histogram (CV={hist_cv:.2f}) — "
            f"chi-square może mylnie wykryć steganografię w jednolitym tle"
        )
        weights["chi_square"]  = max(0.20, weights["chi_square"] - 0.15)
        reliability["chi_square"] = "medium"

    # 5. Obraz jednobarwny (grayscale) → chi-square analizuje tylko L (OK)
    if is_grayscale:
        warnings.append(
            "Obraz w skali szarości — chi-square analizuje tylko kanał L "
            "(brak kanałów R/G/B do osobnej analizy)"
        )

    # Normalizacja wag do sumy 1.0
    total = sum(weights.values())
    weights = {k: round(v / total, 4) for k, v in weights.items()}

    return {
        # Cechy obrazu
        "format":           fmt,
        "size_px":          n_pixels,
        "is_grayscale":     is_grayscale,
        "mean_brightness":  round(mean_b, 1),
        "std_brightness":   round(std_b,  1),
        "saturation_high":  round(sat_high, 4),
        "saturation_low":   round(sat_low,  4),
        "histogram_cv":     round(hist_cv,  4),

        # Wnioski
        "warnings":    warnings,
        "weights":     weights,
        "reliability": reliability,
    }


def print_profile(profile: dict):
    """Czytelne wypisanie profilu na konsolę (do debugowania)."""
    print(f"  Format:       {profile['format']}")
    print(f"  Pikseli:      {profile['size_px']:,}")
    print(f"  Jasność:      {profile['mean_brightness']:.0f} ± {profile['std_brightness']:.0f}")
    print(f"  Saturacja:    jasna={profile['saturation_high']:.1%}  ciemna={profile['saturation_low']:.1%}")
    print(f"  Histogram CV: {profile['histogram_cv']:.3f}")
    print(f"  Wagi:         chi={profile['weights']['chi_square']}  "
          f"rs={profile['weights']['rs_analysis']}  "
          f"ent={profile['weights']['shannon_entropy']}")
    print(f"  Wiarygodność: {profile['reliability']}")
    if profile["warnings"]:
        print(f"  Ostrzeżenia:")
        for w in profile["warnings"]:
            print(f"    ⚠ {w}")


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Użycie: python image_profiler.py obraz.png")
        sys.exit(1)
    p = profile_image(sys.argv[1])
    print_profile(p)
    print()
    print(json.dumps(p, indent=2, ensure_ascii=False))
