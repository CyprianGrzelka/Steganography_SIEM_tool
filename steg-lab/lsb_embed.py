"""
Generator obrazów testowych ze steganografią LSB.

Ten skrypt:
  1. Bierze czyste zdjęcie (PNG)
  2. Wpisuje w nie dane metodą LSB (Least Significant Bit)
  3. Zapisuje wynik jako obraz "zainfekowany"

Używaj go do tworzenia par czyste/zainfekowane do testów algorytmów.

Uruchom:
  python lsb_embed.py clean.png stego.png --payload 0.5
  (0.5 = wypełnij 50% pikseli danymi)
"""

import sys
import argparse
import numpy as np
from PIL import Image


def embed_lsb(input_path: str, output_path: str, fill_ratio: float = 0.5) -> dict:
    """
    Wpisuje losowe dane do obrazu metodą LSB.

    Parametry:
      input_path  — czyste zdjęcie źródłowe (najlepiej PNG)
      output_path — gdzie zapisać obraz ze steganografią
      fill_ratio  — ile % pikseli wypełnić danymi (0.1 = 10%, 1.0 = 100%)

    Jak działa LSB embedding:
      Każdy piksel ma wartość 0-255, czyli 8 bitów.
      LSB = Least Significant Bit = ostatni (najmniej ważny) bit.

      Przykład:
        Piksel 100 w binarnym: 0110 0100
                                       ^ tu jest LSB

        Wpisujemy bit '1':
        Krok 1: wyzeruj LSB: 100 AND 254 = 100 AND 11111110 = 0110 0100 (bez zmian bo LSB=0)
        Krok 2: wstaw bit:   wynik OR 1  = 0110 0101 = 101

        Zmiana wartości: 100 → 101 (różnica o 1 — niezauważalna wizualnie)

      fill_ratio = 0.5 oznacza że modyfikujemy LSB połowy pikseli.
      fill_ratio = 1.0 = pełne osadzenie = najlepiej wykrywalne przez chi-square.
    """
    # Wczytaj obraz w RGB (zachowujemy kolory przy zapisie PNG)
    img = Image.open(input_path).convert("RGB")
    pixels = np.array(img, dtype=np.uint8)
    flat = pixels.flatten()  # spłaszcz do 1D: np. 1000x800x3 → 2_400_000 wartości

    n_total = len(flat)
    n_embed = int(n_total * fill_ratio)  # ile pikseli modyfikujemy

    # Generuj losowe bity do wpisania (symulujemy losowe dane ukryte)
    # W prawdziwej steganografii to byłby zaszyfrowany tekst/plik
    random_bits = np.random.randint(0, 2, size=n_embed, dtype=np.uint8)

    # Wpisz bity w LSB kolejnych pikseli
    for i in range(n_embed):
        # AND 0xFE = AND 11111110 = wyzeruj ostatni bit (LSB)
        # OR bit    = wstaw nasz bit na miejsce LSB
        flat[i] = (flat[i] & 0xFE) | random_bits[i]

    # Odtwórz kształt i zapisz
    result_pixels = flat.reshape(pixels.shape)
    result_img = Image.fromarray(result_pixels, mode="RGB")
    result_img.save(output_path, format="PNG")  # PNG = bezstratny (ważne!)

    info = {
        "input":       input_path,
        "output":      output_path,
        "fill_ratio":  fill_ratio,
        "pixels_total":  n_total,
        "pixels_modified": n_embed,
        "percent_modified": round(fill_ratio * 100, 1),
    }
    return info


# ─────────────────────────────────────────────────────────────────
# Uruchomienie:
#  
#   python lsb_embed.py clean.png stego_50pct.png --payload 0.5
#   python lsb_embed.py clean.png stego_100pct.png --payload 1.0
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LSB Steganography Embedder — do testów")
    parser.add_argument("input",   help="Czyste zdjęcie wejściowe (PNG lub JPG)")
    parser.add_argument("output",  help="Obraz wyjściowy ze steganografią (PNG)")
    parser.add_argument("--payload", type=float, default=0.5,
                        help="Współczynnik wypełnienia 0.0-1.0 (domyślnie 0.5 = 50%%)")
    args = parser.parse_args()

    if not (0.0 < args.payload <= 1.0):
        print("Błąd: --payload musi być między 0.01 a 1.0")
        sys.exit(1)

    info = embed_lsb(args.input, args.output, args.payload)
    print(f"\n✓ Gotowe!")
    print(f"  Plik wejściowy:   {info['input']}")
    print(f"  Plik wyjściowy:   {info['output']}")
    print(f"  Pikseli ogółem:   {info['pixels_total']:,}")
    print(f"  Pikseli zmienionych: {info['pixels_modified']:,} ({info['percent_modified']}%)")