"""
Detektor steganografii — entropia Shannona
Autorzy koncepcji: Shannon (1948), zastosowanie do stegoanalizy: Dunbar (2002)

Uruchom: python shannon_entropy.py ścieżka/do/obrazu.png
"""

import sys
import datetime
import logging
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ShannonEntropyDetector:
    """
    Jak działa entropia w jednym zdaniu:
      mierzymy jak "losowy" jest obraz — im bardziej losowy, tym wyższa entropia.
      Steganografia LSB dodaje losowość → entropia rośnie.

    Skala entropii dla obrazu 8-bitowego (0-255):
      0.0 — obraz jednokolorowy (np. cały biały)
      8.0 — idealna losowość (wszystkie wartości 0-255 równo prawdopodobne)

    Typowe wartości:
      Fotografia naturalna:     6.5 – 7.8
      Obraz ze steganografią:   7.8 – 8.0  (bardziej "płaski" histogram)
      Obraz czysto losowy:      ~8.0

    WAŻNE: entropia jest najsłabszym z trzech detektorów.
      Wiele naturalnych zdjęć (np. tekstury, szum aparatu) ma entropię ~7.9.
      Dlatego używamy jej jako DODATKOWEGO sygnału, nie jako głównego kryterium.

    Parametr threshold (domyślnie 7.8):
      detekcja gdy entropia > threshold.
      Wartość 7.8 jest konserwatywna — redukuje fałszywe alarmy.
    """

    def __init__(self, threshold: float = 7.8):
        self.threshold = threshold

    def analyze(self, filepath: str, pil_image=None) -> dict:
        result = {
            "method": "shannon_entropy",
            "detected": False,
            "entropy": None,
            "confidence": 0.0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        try:
            if pil_image is None:
                image = Image.open(filepath).convert("L")
            else:
                image = pil_image.convert("L")
            pixels = np.array(image).flatten()

            entropy = self._shannon_entropy(pixels)
            result["entropy"] = round(float(entropy), 4)

            if entropy > self.threshold:
                result["detected"] = True
                # Confidence: 0 przy threshold, 1.0 przy entropii = 8.0
                # Normalizujemy do przedziału [threshold, 8.0]
                confidence = (entropy - self.threshold) / (8.0 - self.threshold)
                result["confidence"] = round(float(min(confidence, 1.0)), 4)
                logger.debug("[WYKRYTO]  entropy=%.4f — wysoka losowość, podejrzane", entropy)
            else:
                result["confidence"] = 0.0
                logger.debug("[CZYSTE]   entropy=%.4f — entropia w normie", entropy)

        except Exception as e:
            result["error"] = str(e)
            logger.error("[BŁĄD] shannon_entropy: %s", e)

        return result

    def _shannon_entropy(self, pixels: np.ndarray) -> float:
        """
        Wzór Shannona: H = -Σ p(x) * log2(p(x))

        Kroki:
        1. Policz histogram (ile razy pojawia się każda wartość 0-255).
        2. Zamień liczności na prawdopodobieństwa (podziel przez liczbę pikseli).
        3. Zastosuj wzór Shannona.

        Intuicja wzoru:
          log2(p) jest ujemny gdy p < 1 (czyli zawsze).
          -p * log2(p) jest duże gdy p ≈ 0.5 (maksymalna niepewność).
          Suma tych wartości = "ile bitów potrzeba żeby zakodować jeden piksel".
          Idealna losowość = 8 bitów = 8.0.
        """
        # Krok 1: histogram znormalizowany do prawdopodobieństw
        # np.histogram z density=True normalizuje automatycznie do sumy=1
        counts = np.bincount(pixels, minlength=256)
        total = len(pixels)
        probs = counts / total  # prawdopodobieństwo każdej wartości 0-255

        # Krok 2: bierzemy tylko wartości > 0 (log2(0) = -inf → błąd)
        probs = probs[probs > 0]

        # Krok 3: wzór Shannona
        # np.log2 liczy logarytm dwójkowy
        entropy = -np.sum(probs * np.log2(probs))
        return float(entropy)


# ─────────────────────────────────────────────────────
# Uruchomienie: python shannon_entropy.py obraz.png
# ─────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python shannon_entropy.py obraz.png")
        sys.exit(1)

    detector = ShannonEntropyDetector(threshold=7.8)
    wynik = detector.analyze(sys.argv[1])
    print(wynik)
