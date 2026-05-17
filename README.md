# stego-siem

System detekcji steganografii zintegrowany z SIEM (Logstash/Elasticsearch/Kibana).
Projekt realizowany w ramach pracy magisterskiej.

## Opis

Narzędzie analizuje pliki obrazów pod kątem ukrytych danych (steganografii) przy użyciu trzech metod statystycznych:

| Detektor | Waga | Metoda |
|---|---|---|
| Chi-Square | 45% | Test chi-kwadrat na histogramie LSB |
| RS Analysis | 40% | Analiza grup regularnych i osobliwych |
| Shannon Entropy | 15% | Entropia informacyjna kanałów RGB |

Wyniki są wypisywane jako JSON i mogą być przesyłane do Logstash w celu korelacji zdarzeń w SIEM.

## Struktura projektu

```
stego-siem/
├── detectors/                  # Detektory według typu mediów
│   ├── audio/
│   │   ├── audio_detector.py
│   │   └── audio_lsb.py
│   ├── image/
│   │   └── image_profiler.py
│   ├── network/
│   └── video/
├── logstash/
│   ├── config/
│   │   └── logstash.yml        # Konfiguracja Logstash
│   └── pipeline/
│       └── stego.conf          # Pipeline parsujący zdarzenia skanera
├── steg-lab/                   # Środowisko testowe
│   ├── scan.py                 # Główny skaner (wejście do systemu)
│   ├── run_tests.py            # Testy automatyczne z metrykami
│   ├── lsb_embed.py            # Osadzanie danych LSB (generowanie próbek)
│   ├── chi_square.py
│   ├── rs_analysis.py
│   ├── shannon_entropy.py
│   └── debug_rs.py
├── docker-compose.yml          # ELK stack
└── .env.example                # Przykładowe zmienne środowiskowe
```

## Wymagania

```bash
pip install Pillow numpy scipy
```

Opcjonalnie (stack SIEM):
- Docker + Docker Compose
- Elasticsearch 8.x, Logstash 8.x, Kibana 8.x

## Uruchomienie

### scan.py — skanowanie pojedynczego pliku

```bash
cd steg-lab/

# Tryb interaktywny (pyta o ścieżkę)
python scan.py

# Bezpośrednie podanie pliku
python scan.py obraz.png

# Zapis wyniku do pliku logu (stego_scan.log)
python scan.py obraz.png --log
```

Skaner obsługuje formaty: `.png`, `.bmp`, `.tiff`, `.tif`, `.pgm`, `.jpg`, `.jpeg`, `.jfif`, `.webp`

Przykładowy wynik:

```json
{
  "file": "obraz.png",
  "verdict": "STEGO_DETECTED",
  "risk_score": 0.82,
  "detectors": {
    "chi_square":      { "detected": true,  "confidence": 0.91 },
    "rs_analysis":     { "detected": true,  "confidence": 0.78 },
    "shannon_entropy": { "detected": false, "confidence": 0.21 }
  }
}
```

### run_tests.py — testy automatyczne

```bash
cd steg-lab/

# Testy na wszystkich progach wypełnienia (25%, 50%, 75%, 100%)
python run_tests.py

# Tylko wybrany próg wypełnienia
python run_tests.py --fill 0.50
```

Generuje wyniki w `wyniki_testy.csv` i `wyniki_testy.json` (pliki te są wykluczone z repozytorium — generuj lokalnie).

### Stack SIEM (Docker)

```bash
# Kopiuj i uzupełnij zmienne środowiskowe
cp .env.example .env

# Uruchom ELK stack
docker compose up -d
```

Logstash nasłuchuje na porcie `5044`. Wyniki `scan.py` można przesyłać przez Filebeat lub bezpośrednio przez TCP.

## Licencja

MIT
