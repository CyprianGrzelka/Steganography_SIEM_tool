"""
Detektor steganografii — metoda chi-kwadrat
Autorzy metody: Westfeld & Pfitzmann (2000)

Uruchom: python chi_square.py ścieżka/do/obrazu.png
"""

import sys
import datetime
import logging
import numpy as np
from PIL import Image
from scipy.stats import chisquare

logger = logging.getLogger(__name__)


class ChiSquareDetector:
    """
    Jak działa chi-square w jednym zdaniu:
      mierzymy czy pary pikseli (0,1), (2,3), (4,5)... są "za bardzo równe".
      Jeśli tak → ktoś wpisał tam dane metodą LSB.

    Parametr threshold (domyślnie 0.05):
      próg istotności statystycznej.
      Detekcja gdy p_value > (1 - threshold), czyli p_value > 0.95.
    """

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold

    def analyze(self, filepath: str, pil_image=None) -> dict:
        """
        Główna metoda — przyjmuje ścieżkę do pliku, zwraca słownik wyników.
        """
        result = {
            "method": "chi_square",
            "detected": False,
            "p_value": None,
            "confidence": 0.0,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        try:
            # Analizujemy każdy kanał RGB osobno.
            #
            # DLACZEGO NIE grayscale?
            # lsb_embed wpisuje bity w kanałach R, G, B niezależnie.
            # Konwersja do grayscale: L = 0.299*R + 0.587*G + 0.114*B
            # Zmiana R o 1 bit (±1) zmienia L o ±0.299 → zaokrągla się do 0.
            # Chi-square na grayscale NIE widzi zmiany → zawsze p=0.
            #
            # Rozwiązanie: analizuj każdy kanał osobno, weź maksymalne p_value.
            # Jeśli chociaż jeden kanał ma wyrównane pary → wykrywamy stego.
            if pil_image is None:
                image = Image.open(filepath).convert("RGB")
            else:
                image = pil_image.convert("RGB")
            r_ch, g_ch, b_ch = image.split()

            p_r = self._chi_square_test(np.array(r_ch).flatten())
            p_g = self._chi_square_test(np.array(g_ch).flatten())
            p_b = self._chi_square_test(np.array(b_ch).flatten())

            # Najbardziej "podejrzany" kanał decyduje o wyniku
            p_value = max(p_r, p_g, p_b)
            result["p_value"] = round(float(p_value), 4)
            result["p_value_per_channel"] = {
                "R": round(float(p_r), 4),
                "G": round(float(p_g), 4),
                "B": round(float(p_b), 4),
            }

            if p_value > (1.0 - self.threshold):
                result["detected"] = True
                result["confidence"] = round(float(p_value), 4)
                logger.debug("[WYKRYTO]  p=%.4f (R=%.3f G=%.3f B=%.3f) — steganografia LSB", p_value, p_r, p_g, p_b)
            else:
                result["confidence"] = 0.0
                logger.debug("[CZYSTE]   p=%.4f (R=%.3f G=%.3f B=%.3f) — brak detekcji", p_value, p_r, p_g, p_b)

        except Exception as e:
            result["error"] = str(e)
            logger.error("[BŁĄD] chi_square: %s", e)

        return result

    def _chi_square_test(self, pixels: np.ndarray) -> float:
        """
        Serce algorytmu — oblicza p_value.

        Kroki:
        1. Policz histogram: ile razy pojawia się każda wartość 0-255.
        2. Grupuj wartości w pary: (0,1), (2,3), (4,5), ..., (254,255).
           Te pary to tzw. PoV pairs (Pairs of Values) — różnią się tylko LSB.
        3. Dla każdej pary: policz ile razy wystąpiła wartość parzysta (n1)
           i nieparzysta (n2). Oczekiwana liczność to (n1+n2)/2 dla obu.
        4. Test chi-square: czy obserwowane (n1, n2) pasują do oczekiwanych?
           - Czyste zdjęcie: n1 ≠ n2 → duże odchylenie → mały p_value
           - Zdjęcie ze stego: n1 ≈ n2 → małe odchylenie → duży p_value
        """

        # Krok 1: histogram — tablica 256 elementów
        # histogram[100] = ile razy wartość 100 pojawia się w obrazie
        histogram = np.bincount(pixels, minlength=256)

        observed = []  # co faktycznie widzimy w obrazie
        expected = []  # co byłoby gdyby para była równa (stego)

        # Krok 2 i 3: buduj pary
        for i in range(0, 256, 2):        # i = 0, 2, 4, ..., 254
            n1 = histogram[i]             # liczność wartości parzystej, np. 100
            n2 = histogram[i + 1]         # liczność wartości nieparzystej, np. 101
            total = n1 + n2

            if total > 0:                 # pomijamy pary gdzie oba = 0
                observed.extend([n1, n2])
                # Oczekiwane: gdyby LSB był losowy, obie wartości w parze
                # pojawiałyby się tak samo często → total/2 każda
                expected.extend([total / 2, total / 2])

        observed = np.array(observed, dtype=float)
        expected = np.array(expected, dtype=float)

        # Usuń pozycje gdzie expected = 0 (chi-square nie może dzielić przez 0)
        mask = expected > 0
        observed, expected = observed[mask], expected[mask]

        if len(observed) < 2:
            return 1.0  # za mało danych → nie możemy ocenić

        # Krok 4: test chi-square z scipy
        # chisquare zwraca (statystyka, p_value)
        # Nas interesuje tylko p_value
        _, p_value = chisquare(observed, f_exp=expected)
        return float(p_value)


# ─────────────────────────────────────────────
# Uruchomienie: python chi_square.py obraz.png
# ─────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python chi_square.py obraz.png")
        sys.exit(1)

    detector = ChiSquareDetector(threshold=0.05)
    wynik = detector.analyze(sys.argv[1])
    print(wynik)