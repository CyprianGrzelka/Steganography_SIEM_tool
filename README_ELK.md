# Integracja detektorów steganografii z ELK Stack

Instrukcja end-to-end do uruchomienia systemu detekcji steganografii z Kibana dashboard.

## Wymagania

- Python 3.8+
- Elasticsearch 8.x
- Kibana 8.x
- Filebeat 8.x
- Docker & Docker Compose (opcjonalnie — do szybkiego startu)

## Krok 1: Instalacja zależności Python

```bash
# Zainstaluj wymagane pakiety
pip install pillow numpy scipy

# Opcjonalnie (dla wideo - wymaga OpenCV)
pip install opencv-python
```

## Krok 2: Wdrażanie index template w Elasticsearch

Index template definiuje strukturę i typy danych dla dokumentów w ES.

### Opcja A: Za pomocą curl

```bash
curl -X PUT "localhost:9200/_index_template/stego-events-template" \
  -H 'Content-Type: application/json' \
  -d @elk/index_template.json
```

### Opcja B: Za pomocą Kibana Dev Tools

1. Otwórz Kibana: http://localhost:5601
2. Idź do **Dev Tools** → **Console**
3. Wklej zawartość `elk/index_template.json` i wykonaj (Ctrl+Enter)

### Weryfikacja

```bash
# Sprawdź czy template został zainstalowany
curl -X GET "localhost:9200/_index_template/stego-events-template"
```

## Krok 3: Uruchomienie Filebeat

Filebeat monitoruje plik `stego_events.ndjson` i wysyła zdarzenia do Elasticsearch.

### Konfiguracja Filebeat

1. Skopiuj `elk/filebeat.yml` do katalogu Filebeat:
   ```bash
   cp elk/filebeat.yml /path/to/filebeat/filebeat.yml
   ```

2. Jeśli używasz Docker:
   ```bash
   docker run -d \
     --name=filebeat \
     --user=root \
     -v $(pwd)/elk/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro \
     -v $(pwd)/stego_events.ndjson:/stego_events.ndjson:ro \
     docker.elastic.co/beats/filebeat:8.11.0
   ```

3. Jeśli masz zainstalowany Filebeat lokalnie:
   ```bash
   filebeat -c elk/filebeat.yml
   ```

## Krok 4: Uruchomienie agenta detekcji (tryb watch)

Agent monitoruje folder i dopisuje wyniki do `stego_events.ndjson`.

```bash
# Monitoruj folder ./incoming co 5 sekund
python stego_agent.py --watch ./incoming --poll-interval 5

# Lub z custom logfile
python stego_agent.py --watch ./incoming --logfile my_agent.log
```

## Krok 5: Import dashboarda w Kibanie

Kibana dashboard zawiera 4 wizualizacje:
- Timeline ryzyka
- Rozkład werdyktów (pie chart)
- Ostatnie alerty (SUSPICIOUS/DETECTED)
- Licznik DETECTED w ostatnich 24h

### Import via Kibana UI

1. Otwórz Kibana: http://localhost:5601
2. Idź do **Stack Management** → **Saved Objects**
3. Kliknij **Import**
4. Wybierz plik `elk/kibana_dashboard.ndjson`
5. Kliknij **Import**

### Weryfikacja

Po imporcie zobaczysz dashboard **"Steganography Detection - SIEM Dashboard"** w sekcji Dashboards.

## Krok 6: Test end-to-end

### Analiza pojedynczego pliku

```bash
# Testuj na przykładowym czystym obrazie
python stego_agent.py steg-lab/sample_images/clean/example.png

# Wynik powinien trafić do stego_events.ndjson
tail stego_events.ndjson
```

### Weryfikacja w Elasticsearch

```bash
# Sprawdź czy indeks został utworzony
curl -X GET "localhost:9200/_cat/indices?v" | grep stego-events

# Pobierz ostatnie 10 dokumentów
curl -X GET "localhost:9200/stego-events-*/_search?size=10&sort=timestamp:desc"
```

### Wizualizacja w Kibanie

1. Otwórz Kibana: http://localhost:5601
2. Idź do **Dashboards**
3. Otwórz **"Steganography Detection - SIEM Dashboard"**
4. Powinieneś zobaczyć zdarzenia w tabelach i wykresach

## Tryby agenta

### Tryb interaktywny (domyślny)

```bash
python stego_agent.py
# Pyta o ścieżkę do pliku na każdym kroku
```

### Tryb pojedynczego pliku

```bash
python stego_agent.py /path/to/file.png
# Analizuje i loguje wynik
```

### Tryb monitorowania (watch)

```bash
python stego_agent.py --watch /path/to/folder
# Monitoruje folder, oczekuje na nowe pliki (polling co 5s)
```

## Troubleshooting

### Problem: "Błąd importu chi_square.py"

**Rozwiązanie:** Upewnij się, że folder `steg-lab/` zawiera wszystkie wymagane detektory (`chi_square.py`, `rs_analysis.py`, `shannon_entropy.py`).

```bash
ls -la steg-lab/*.py | grep -E "(chi_square|rs_analysis|shannon_entropy)"
```

### Problem: "Filebeat nie wysyła zdarzeń"

1. Sprawdź czy `stego_events.ndjson` istnieje i zawiera dane:
   ```bash
   tail stego_events.ndjson
   ```

2. Sprawdź logi Filebeat:
   ```bash
   tail -f filebeat/filebeat
   ```

3. Upewnij się że Elasticsearch nasłuchuje na `localhost:9200`:
   ```bash
   curl -X GET "localhost:9200/"
   ```

### Problem: "Indeks nie został utworzony"

Prawdopodobnie index template nie został zainstalowany. Powtórz **Krok 2**.

## Format danych NDJSON

Każda linia w `stego_events.ndjson` to kompletny dokument JSON:

```json
{
  "timestamp": "2026-05-23T14:30:00+00:00",
  "event_type": "stego_scan",
  "source_module": "image",
  "file_name": "example.png",
  "file_path": "/home/user/steg-lab/sample_images/clean/example.png",
  "file_size_bytes": 456789,
  "file_format": "PNG",
  "verdict": "CLEAN",
  "risk_score": 8,
  "detectors_triggered": 0,
  "detectors_total": 3,
  "detectors": {
    "chi_square": {"p_value": 0.42, "detected": false, "confidence": 0.1},
    "rs_analysis": {"rs_difference": -0.005, "detected": false, "confidence": 0.05},
    "shannon_entropy": {"entropy": 7.3, "detected": false, "confidence": 0.02}
  },
  "warnings": []
}
```

## Architektura

```
stego_agent.py
     ↓
[Image|Audio|Network]Detector
     ↓
SharedResult (dataclass)
     ↓
stego_events.ndjson (append)
     ↓
Filebeat (monitoring)
     ↓
Elasticsearch (index: stego-events-YYYY.MM.dd)
     ↓
Kibana (visualization)
```

## Dalsza konfiguracja

### Zmiana interwału Filebeat

Edytuj `elk/filebeat.yml`, sekcja `filebeat.inputs[0]`:

```yaml
scan.frequency: 10s  # Dodaj tę linię, domyślnie 10s
```

### Zmiana okresu przechowywania indeksów

Dodaj ILM policy w Kibana → Stack Management → Index Lifecycle Policies

### Zmiana adresu Elasticsearch

Edytuj `elk/filebeat.yml`:

```yaml
output.elasticsearch:
  hosts:
    - "elastic.example.com:9200"
```

---

**Wersja:** 1.0  
**Ostatnia aktualizacja:** 2026-05-23
