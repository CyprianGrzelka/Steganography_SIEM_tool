"""
audio_detector.py — detektor steganografii audio (group parity LSB)
Metoda statystyczna bez znajomości wiadomości.

Format wyniku zgodny z chi_square.py (pola: detector, confidence, suspicious, score, interpretation).
Obsługiwane: WAV 8-bit unsigned (sampwidth=1), 16-bit signed (sampwidth=2).

Trzy testy komplementarne:
  1. Parity chi-square  — rozkład parzystości grup 8 próbek (test ogólny).
  2. Value-pair chi-square — pary (n, n+1) dolnego bajtu próbek-liderów
     (co 8. próbka — jedyna modyfikowana przez embedder).
  3. Header plausibility — czy grupy 0-31 kodują sensowną 32-bitową długość
     wiadomości (test specyficzny dla formatu audio_lsb.py).

Ograniczenie: testy 1 i 2 są skuteczne dopiero przy wypełnieniu >= ~10%.
Test 3 jest skuteczny dla rzadkich ładunków ale jest specyficzny dla embeddera.
"""

import sys
import wave
import struct
import datetime
import logging
import numpy as np
from scipy.stats import chisquare

logger = logging.getLogger(__name__)


class AudioGroupParityDetector:
    """
    Detektor group-parity LSB dla plików WAV.

    group_size  : rozmiar grupy próbek (domyślnie 8, jak w audio_lsb.py)
    threshold   : próg istotności — detekcja gdy confidence > (1 - threshold)
    """

    def __init__(self, group_size: int = 8, threshold: float = 0.05):
        self.group_size = group_size
        self.threshold  = threshold

    # ── Publiczny interfejs ──────────────────────────────────────────

    def analyze(self, filepath: str) -> dict:
        result = {
            "detector":         "audio_group_parity",
            "suspicious":       False,
            "confidence":       0.0,
            "score":            0.0,
            "p_value_parity":   None,
            "p_value_pairs":    None,
            "header_score":     None,
            "n_samples":        0,
            "n_groups":         0,
            "sampwidth":        None,
            "interpretation":   "",
            "timestamp":        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        try:
            samples, sampwidth, meta = self._read_wav(filepath)
        except Exception as e:
            result["error"] = str(e)
            logger.error("[BŁĄD] audio_detector: %s", e)
            return result

        n_samples = len(samples)
        n_groups  = n_samples // self.group_size

        result["n_samples"] = n_samples
        result["n_groups"]  = n_groups
        result["sampwidth"] = sampwidth
        result["wav_meta"]  = meta

        if n_groups < 64:
            result["error"] = (
                f"Za mało próbek do analizy: {n_samples} "
                f"(min. {64 * self.group_size})."
            )
            return result

        # Test 1 — rozkład parzystości grup
        p_parity = self._parity_chi_square(samples, n_groups)

        # Test 2 — pary wartości dolnego bajtu liderów grup (co 8. próbka)
        # Dolny bajt: 256 binów → stabilne chi-square niezależnie od częstotliwości
        # i liczby kanałów. Dla 16-bit pełny zakres (65536 binów) jest zbyt rzadki.
        leaders = samples[::self.group_size]
        p_pairs = self._value_pair_lower_byte(leaders)

        # Test 3 — plausibility nagłówka długości
        # audio_lsb.py zawsze zapisuje 32-bitową długość wiadomości w grupach 0-31.
        # Czyste audio: losowe bity → prawdopodobnie nierealistyczna długość.
        # Stego: rzeczywista długość wiadomości → sensowna wartość.
        header_score = self._header_plausibility(samples, n_groups)

        # p_pairs nie wchodzi do confidence — test Westfeld&Pfitzmann jest
        # nieefektywny dla audio o wysokim zakresie dynamicznym (16-bit stereo),
        # gdzie dolny bajt jest z natury równomiernie rozłożony nawet w czystym pliku.
        # Zachowujemy p_pairs jako wartość diagnostyczną/porównawczą.
        confidence = max(p_parity, header_score)
        suspicious = confidence > (1.0 - self.threshold)
        score      = round(confidence * 100, 1)

        sources = []
        if p_parity     > (1.0 - self.threshold): sources.append(f"parity(p={p_parity:.3f})")
        if header_score > (1.0 - self.threshold): sources.append(f"header({header_score:.3f})")
        pairs_note = (
            " [Uwaga: p_pairs=1.0 nie jest sygnałem stego — "
            "dolny bajt 16-bit audio jest z natury równomierny.]"
            if p_pairs > 0.99 and not sources else ""
        )

        if suspicious:
            interp = (
                f"Wykryto sygnał steganograficzny [{', '.join(sources)}]. "
                f"Nagłówek długości lub rozkład parzystości grup sugerują "
                f"modyfikację metodą group-parity LSB.{pairs_note}"
            )
        else:
            interp = (
                f"Brak statystycznych oznak steganografii group-parity LSB "
                f"(p_parity={p_parity:.4f}, header={header_score:.4f}).{pairs_note} "
                f"Uwaga: testy statystyczne wykrywają rzadkie ładunki (<5% fill) "
                f"z ograniczoną pewnością."
            )

        result.update({
            "suspicious":     suspicious,
            "confidence":     round(float(confidence), 4),
            "score":          score,
            "p_value_parity": round(float(p_parity), 4),
            "p_value_pairs":  round(float(p_pairs), 4),
            "header_score":   round(float(header_score), 4),
            "interpretation": interp,
        })

        logger.debug(
            "[AUDIO] suspicious=%s p_parity=%.4f p_pairs=%.4f header=%.4f "
            "n_groups=%d sampwidth=%d",
            suspicious, p_parity, p_pairs, header_score, n_groups, sampwidth,
        )
        return result

    # ── Prywatne metody ──────────────────────────────────────────────

    def _read_wav(self, filepath: str):
        """Wczytaj plik WAV, zwróć (próbki, sampwidth, meta)."""
        with wave.open(filepath, "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth  = wf.getsampwidth()
            framerate  = wf.getframerate()
            n_frames   = wf.getnframes()
            frames     = wf.readframes(n_frames)

        if sampwidth not in (1, 2):
            raise ValueError(
                f"Nieobsługiwany sampwidth={sampwidth}. "
                "Obsługiwane: 1 (8-bit unsigned), 2 (16-bit signed)."
            )

        fmt_char  = {1: "B", 2: "h"}[sampwidth]
        n_samples = n_frames * n_channels
        fmt       = f"<{n_samples}{fmt_char}"
        samples   = list(struct.unpack(fmt, frames))

        meta = {
            "channels":   n_channels,
            "sampwidth":  sampwidth,
            "framerate":  framerate,
            "n_frames":   n_frames,
            "duration_s": round(n_frames / framerate, 3),
        }
        return samples, sampwidth, meta

    def _parity_chi_square(self, samples: list, n_groups: int) -> float:
        """
        Chi-square na rozkładzie parzystości grup (suma LSB mod 2).

        H0: parzystości są równomiernie rozkłone (50/50).
        W stego: parzystości = bity wiadomości (losowe ~50/50) → p_value wysokie.
        W czystym audio: parzystości zależą od sygnału — często też ~50/50.
        Test ma niską moc dla rzadkich ładunków.
        """
        ones = 0
        for i in range(n_groups):
            start  = i * self.group_size
            grp    = samples[start:start + self.group_size]
            parity = sum(s & 1 for s in grp) % 2
            ones  += parity

        zeros    = n_groups - ones
        expected = n_groups / 2.0

        obs = np.array([zeros, ones], dtype=float)
        exp = np.array([expected, expected], dtype=float)

        _, p_value = chisquare(obs, f_exp=exp)
        return float(p_value)

    def _value_pair_lower_byte(self, leaders: list) -> float:
        """
        Chi-square na parach (n, n+1) dolnego bajtu próbek-liderów.

        Analogia do chi-square Westfeld & Pfitzmann (2000) dla obrazów,
        ale tylko na liderach grup (co 8. próbka) — jedynych modyfikowanych
        przez audio_lsb.py.

        Dolny bajt (bity 0-7): 256 wartości, 128 par — daje stabilne chi-square
        nawet dla krótkiego audio (w odróżnieniu od pełnego 16-bit = 65536 binów).

        Modyfikacja LSB (XOR 1) zmienia parzyste→nieparzyste i odwrotnie,
        co wyrównuje pary (n, n+1) — ten sam efekt co w analizie obrazów.
        """
        arr = np.array(leaders, dtype=np.int64) & 0xFF   # dolny bajt, 0-255

        histogram = np.bincount(arr, minlength=256)

        obs, exp = [], []
        for i in range(0, 256, 2):
            n1, n2 = int(histogram[i]), int(histogram[i + 1])
            total  = n1 + n2
            if total > 0:
                obs.extend([n1, n2])
                exp.extend([total / 2.0, total / 2.0])

        obs = np.array(obs, dtype=float)
        exp = np.array(exp, dtype=float)
        mask = exp > 0
        obs, exp = obs[mask], exp[mask]

        if len(obs) < 2:
            return 0.0

        _, p_value = chisquare(obs, f_exp=exp)
        return float(p_value)

    def _header_plausibility(self, samples: list, n_groups: int) -> float:
        """
        Sprawdza czy grupy 0-31 kodują sensowną 32-bitową długość wiadomości.

        audio_lsb.py zawsze umieszcza 32-bitowy licznik bitów na początku pliku
        (grupy 0-31). Dla stego: licznik = rzeczywista długość (mała, dodatnia).
        Dla czystego audio: licznik = losowe 32-bitowe wartości → nierealistyczne.

        P(losowe 32-bit in [1, max_valid]) = max_valid / 2^32 ≈ 0.01-0.07
        → niskie prawdopodobieństwo fałszywego pozytywu dla krótkich plików.

        Zwraca:
          0.0              jeśli claimed_length poza zakresem [1, max_valid]
          1 - L/2^32 ≈ 1.0 jeśli claimed_length jest sensowny (zwykle 1.0)
        """
        if n_groups < 33:
            return 0.0

        bits = ""
        for i in range(32):
            start  = i * self.group_size
            grp    = samples[start:start + self.group_size]
            parity = sum(s & 1 for s in grp) % 2
            bits  += str(parity)

        claimed_length = int(bits, 2)
        max_valid      = (n_groups - 32) * 8   # maks. bitów jakie zmieści plik

        if 0 < claimed_length <= max_valid:
            # im mniejsza długość, tym bardziej "konkretna" i mniej prawdopodobna losowo
            return 1.0 - (claimed_length / (2 ** 32))
        return 0.0


# ─────────────────────────────────────────────────────────────────
# Uruchomienie: python audio_detector.py plik.wav
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json

    if len(sys.argv) < 2:
        print("Użycie: python audio_detector.py plik.wav")
        sys.exit(1)

    det   = AudioGroupParityDetector()
    wynik = det.analyze(sys.argv[1])
    print(json.dumps(wynik, indent=2, ensure_ascii=False))
