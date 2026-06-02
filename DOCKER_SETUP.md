# Uruchomienie ELK Stack w Docker - Kompletny Przewodnik

## Wymagania

- Docker zainstalowany i uruchomiony
- Docker Compose 1.27+
- Minimum 4GB RAM dostępne dla Docker

Sprawdzenie:
```bash
docker --version
docker-compose --version
```

---

## Krok 1: Uruchomienie ELK Stack

```bash
cd c:\stego-siem

# Uruchom wszystkie kontenery (Elasticsearch + Logstash + Kibana + Filebeat)
docker-compose up -d

# Pokaż logi wszystkich kontenerów
docker-compose logs -f
```

Czekaj aż zobaczysz w logach:
```
elasticsearch  | {"@timestamp":"...","level":"info","message":"started"}
kibana         | {"log.level":"info","message":"Server running at http://0.0.0.0:5601"}
```

**Oczekiwany czas**: 30-60 sekund (pierwszy start)

---

## Krok 2: Weryfikacja statusu kontenerów

```bash
# Sprawdź czy wszystkie kontenery są "healthy"
docker-compose ps
```

Powinieneś zobaczyć:
```
CONTAINER ID   IMAGE                                      STATUS
...            elasticsearch:8.13.0                       Up (healthy)
...            logstash:8.13.0                           Up
...            kibana:8.13.0                             Up (healthy)
...            filebeat:8.13.0                           Up
```

---

## Krok 3: Test Elasticsearch

```bash
# Sprawdź czy ES nasłuchuje na 9200
curl http://localhost:9200/

# Powinna być odpowiedź z wersją:
# {
#   "name" : "es01",
#   "cluster_name" : "stego-siem",
#   "version" : { "number" : "8.13.0", ... },
#   ...
# }
```

Jeśli działa — Elasticsearch OK ✅

---

## Krok 4: Zainstaluj Index Template

### Opcja A: Programowo (curl)

```bash
curl -X PUT "http://localhost:9200/_index_template/stego-events-template" \
  -H 'Content-Type: application/json' \
  -d @elk/index_template.json

# Powinna być odpowiedź:
# {"acknowledged":true}
```

### Opcja B: W Kibana Dev Tools (interfejs)

1. Otwórz: **http://localhost:5601**
2. Menu → **Stack Management** → **Dev Tools**
3. Wklej ten blok i naciśnij **Ctrl+Enter**:

```
PUT _index_template/stego-events-template
```

Następnie dokleij zawartość z `elk/index_template.json` (od linii `{` do `}`)

Powinna być odpowiedź: `{"acknowledged":true}`

---

## Krok 5: Uruchom agenta detekcji (tryb watch)

W nowym terminalu, w katalogu `c:\stego-siem`:

```bash
python stego_agent.py --watch ./incoming --poll-interval 5
```

Lub jeśli folder `./incoming` nie istnieje, utwórz go:

```bash
mkdir incoming
python stego_agent.py --watch ./incoming
```

Powinno wyświetlić:
```
✓ Monitoring ./incoming for new files (Ctrl+C to stop)
```

---

## Krok 6: Testuj na przykładowych plikach

W trzecim terminalu:

```bash
# Kopiuj przykładowe pliki do folderu monitorowanego
cp steg-lab/sample_images/clean/images/*.png incoming/
cp steg-lab/sample_images/clean/images/*.jpg incoming/
cp steg-lab/sample_images/clean/audio/*.wav incoming/
```

Agent powinien automatycznie analizować pliki i dopisywać do `stego_events.ndjson`.

Sprawdzenie:
```bash
tail stego_events.ndjson
# Powinieneś zobaczyć linie JSON z wynikami
```

---

## Krok 7: Sprawdzenie czy dane trafiły do Elasticsearch

```bash
# Sprawdź ile dokumentów jest w indeksach
curl -X GET "http://localhost:9200/_cat/indices?v"

# Powinna być linia:
# stego-events-2026.05.23  ...  1  docs: 4

# Pobierz ostatnie 5 dokumentów
curl -X GET "http://localhost:9200/stego-events-*/_search?size=5&sort=timestamp:desc" | python -m json.tool
```

Jeśli widać dokumenty — **Elasticsearch otrzymał dane!** ✅

---

## Krok 8: Otwórz Kibana Dashboard

1. Wejdź na: **http://localhost:5601**
2. Poczekaj aż Kibana się załaduje (pierwsze otwarcie ~30 sekund)
3. Jeśli zobaczy "Kibana not ready" — czekaj dalej

### Zarejestruj Index Pattern (jeśli jest wymagane)

1. Gdy wpiszesz pierwszy raz, Kibana poprosi o index pattern
2. Wpisz: `stego-events-*`
3. Wybierz pole **@timestamp** jako Time field
4. Kliknij **Create index pattern**

### Zaimportuj Dashboard

1. Menu → **Stack Management** → **Saved Objects**
2. Kliknij **Import**
3. Wybierz plik: `elk/kibana_dashboard.ndjson`
4. Kliknij **Import**
5. Pokaż się komunikat: "Successfully imported 1 object"

### Otwórz Dashboard

1. Menu → **Dashboards**
2. Szukaj: **"Steganography Detection - SIEM Dashboard"**
3. Kliknij aby otworzyć

Powinieneś zobaczyć:
- **Timeline**: Wykres risk_score po czasie
- **Verdict Distribution**: Pie chart (CLEAN/SUSPICIOUS/DETECTED)
- **Recent Alerts**: Tabela ostatnich zdarzeń
- **DETECTED Events (Last 24h)**: Licznik

---

## Komendy do Debugowania

### Logi kontenerów

```bash
# Wszystkie logi
docker-compose logs -f

# Tylko Elasticsearch
docker-compose logs -f elasticsearch

# Tylko Kibana
docker-compose logs -f kibana

# Tylko Filebeat
docker-compose logs -f filebeat
```

### Sprawdzenie czy Filebeat czyta plik

```bash
# Sprawdź czy filebeat ma dostęp do stego_events.ndjson
docker exec filebeat ls -la /stego_events.ndjson

# Sprawdź czy filebeat wysyła dane
docker exec filebeat cat /usr/share/filebeat/.filebeat
```

### Restart pojedynczego kontenera

```bash
# Restart Elasticsearch
docker-compose restart elasticsearch

# Restart wszystkich
docker-compose restart
```

### Czyszczenie indeksów (jeśli trzeba zacząć od nowa)

```bash
# Usuń wszystkie indeksy stego-events
curl -X DELETE "http://localhost:9200/stego-events-*"

# Usuń template
curl -X DELETE "http://localhost:9200/_index_template/stego-events-template"
```

---

## Troubleshooting

### Problem: "elasticsearch is not healthy"

```bash
# Sprawdzenie statusu
curl http://localhost:9200/_cluster/health

# Jeśli błąd połączenia — elasticsearch się jeszcze startuje
# Czekaj 30-60 sekund i spróbuj ponownie
```

### Problem: Kibana nie się nie ładuje (czarny ekran)

1. Czekaj 30 sekund (pierwszego startu)
2. Odśwież stronę (F5)
3. Sprawdź logi: `docker-compose logs kibana`

### Problem: Filebeat nie wysyła danych

1. Sprawdź czy plik `stego_events.ndjson` istnieje:
   ```bash
   ls -la stego_events.ndjson
   ```

2. Sprawdź logi filebeat:
   ```bash
   docker-compose logs filebeat
   ```

3. Restart filebeat:
   ```bash
   docker-compose restart filebeat
   ```

### Problem: Agent detekcji nie pisze do stego_events.ndjson

```bash
# Sprawdzenie czy agent jest uruchomiony
ps aux | grep stego_agent.py

# Sprawdzenie loga agenta
tail stego_agent.log

# Ręczny test jednego pliku
python stego_agent.py steg-lab/sample_images/clean/images/block50px.png

# Sprawdzenie czy został dopisany
tail stego_events.ndjson
```

---

## Zatrzymanie Stack'u

```bash
# Stop wszystkie kontenery
docker-compose stop

# Stop + usunięcie kontenerów (dane ES pozostają)
docker-compose down

# Stop + usunięcie wszystkiego razem z danymi ES
docker-compose down -v
```

---

## Architektura Flow

```
┌─────────────────┐
│  stego_agent.py │  (Python — local)
│  --watch folder │
└────────┬────────┘
         │
         ├─ Analizuje pliki (ImageDetector, AudioDetector, NetworkDetector)
         │
         ├─ Dopisuje JSON do stego_events.ndjson
         │
         └─ (shared file system)
            │
            ▼
     ┌──────────────────┐
     │  Filebeat        │  (Docker)
     │  monitoring      │
     │  .ndjson file    │
     └────────┬─────────┘
              │
              ├─ Czyta nowe linie z stego_events.ndjson
              │
              ├─ Wysyła do Elasticsearch
              │
              └─ (TCP 9200)
                 │
                 ▼
          ┌──────────────────┐
          │  Elasticsearch   │  (Docker)
          │  (Index storage) │
          └────────┬─────────┘
                   │
                   ├─ Indexuje dokumenty
                   │
                   ├─ Indeksy: stego-events-YYYY.MM.dd
                   │
                   └─ (HTTP 9200)
                      │
                      ▼
               ┌──────────────────┐
               │  Kibana          │  (Docker)
               │  Visualization   │
               └────────┬─────────┘
                        │
                        ├─ Dashboard
                        │
                        └─ http://localhost:5601
```

---

## Czasy startu

| Komponent | Czas startu | Status check |
|-----------|------------|--------------|
| Elasticsearch | 20-30s | `curl localhost:9200/` |
| Kibana | 30-40s | `curl localhost:5601/api/status` |
| Filebeat | 5-10s | `docker-compose ps` |

**Całkowity czas**: ~60 sekund od `docker-compose up -d` do pełnej gotowości

---

**Jeśli coś nie działa — sprawdź logi:**
```bash
docker-compose logs -f
```

Powodzenia!
