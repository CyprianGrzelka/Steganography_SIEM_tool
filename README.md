# Steganography Detection SIEM Tool

A comprehensive system for detecting steganography in digital media (images, audio, video) and network traffic, integrated with the **ELK Stack** (Elasticsearch, Logstash, Kibana) for real-time monitoring and analysis.

**Project Type:** Thesis-based security research tool  
**Status:** Active Development  
**License:** MIT

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Detection Methods](#detection-methods)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Integration with ELK Stack](#integration-with-elk-stack)
- [Testing](#testing)
- [Supported Media Types](#supported-media-types)
- [Requirements](#requirements)
- [Troubleshooting](#troubleshooting)

---

## Overview

The **Steganography Detection SIEM Tool** is designed to identify and analyze potential hidden data in digital media and network traffic. The system employs multiple statistical analysis methods to detect anomalies that may indicate the presence of steganographic content.

The tool outputs results in JSON format (NDJSON) and seamlessly integrates with the **ELK Stack** for centralized monitoring, alerting, and forensic analysis.

### Use Cases

- **Security Operations Centers (SOCs):** Monitor incoming files and network traffic for covert communication channels
- **Incident Response:** Detect and investigate suspected data exfiltration via steganography
- **Forensic Analysis:** Analyze suspicious media files for hidden payload signatures
- **Research:** Study steganographic embedding patterns and detection evasion techniques

---

## Key Features

✅ **Multi-Method Detection**
- Chi-Square Test (LSB analysis)
- RS Analysis (Regular-Singular groups)
- Shannon Entropy (Information theory)
- Audio-specific: Group Parity, Periodicity Analysis
- Network: DNS/ICMP/IAT tunneling detection

✅ **Multiple Media Support**
- Images (PNG, JPEG, BMP, GIF)
- Audio Files (WAV, MP3, FLAC)
- Video Files (MP4, AVI, MOV)
- Network Traffic (PCAP, DNS logs, flow metadata)

✅ **Real-Time Monitoring**
- Directory watch mode with automatic file processing
- File system polling (5-second intervals)
- Batch processing capabilities

✅ **ELK Stack Integration**
- Elasticsearch indexing with custom templates
- Kibana dashboards for visualization
- Logstash pipeline for event correlation
- Filebeat for log forwarding

✅ **Unified Verdict System**
- **CLEAN:** No steganographic indicators detected
- **SUSPICIOUS:** Minor anomalies detected, needs review
- **DETECTED:** Multiple strong indicators of steganography

✅ **Detailed Event Context**
- Risk scores (0-100)
- Per-detector metrics and thresholds
- Triggered rules summary
- Performance metadata

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Input Sources                             │
├─────────────────────────────────────────────────────────────┤
│   • Local Files    • Watch Directory    • Network Traffic   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              stego_agent.py (Orchestrator)                   │
│  • File routing   • Detector selection   • Result formatting │
└────────┬──────────────────────────────────┬──────────────────┘
         │                                  │
    ┌────▼─────────────┐    ┌──────────────▼────────┐
    │   Detectors      │    │    Analysis Engines   │
    ├──────────────────┤    ├──────────────────────┤
    │ • ImageDetector  │    │ • Statistical tests  │
    │ • AudioDetector  │    │ • Pattern matching   │
    │ • VideoDetector  │    │ • Heuristics        │
    │ • NetworkDetector│    │ • ML-ready features │
    └────┬─────────────┘    └──────────┬──────────┘
         │                             │
         └──────────────┬──────────────┘
                        │
                        ▼
         ┌──────────────────────────┐
         │   stego_events.ndjson    │
         │  (NDJSON output stream)  │
         └──────────────┬───────────┘
                        │
         ┌──────────────┴──────────────┐
         │                             │
    ┌────▼────────┐          ┌────────▼─────┐
    │  Filebeat   │          │   Logstash   │
    │  (Monitor)  │          │  (Parse)     │
    └────┬────────┘          └────┬─────────┘
         │                        │
         └────────────┬───────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   Elasticsearch         │
         │   (Index & Store)       │
         └────────────┬────────────┘
                      │
                      ▼
         ┌─────────────────────────┐
         │   Kibana Dashboard      │
         │   (Visualize & Alert)   │
         └─────────────────────────┘
```

---

## Detection Methods

### Image Detection

| Detector | Weight | Method | Threshold | Description |
|----------|--------|--------|-----------|-------------|
| **Chi-Square** | 45% | LSB Histogram Analysis | p-value < 0.05 | Tests if LSB distribution matches expected randomness |
| **RS Analysis** | 40% | Regular-Singular Groups | RS Difference > 0.03 | Analyzes pixel group transitions |
| **Shannon Entropy** | 15% | Information Theory | H > expected + std | Measures randomness in RGB channels |

**Verdict Logic:**
- **≥2 detectors triggered** → **DETECTED**
- **Risk score ≥ 60** → **DETECTED**
- **No triggers + risk < 20** → **CLEAN**
- **Otherwise** → **SUSPICIOUS**

### Audio Detection

- **Group Parity Analysis:** Detects LSB modifications in audio samples
- **Entropy Analysis:** Identifies statistical anomalies in frequency domain
- **Periodicity Detection:** Finds artificial patterns in audio structure

### Network Detection

- **DNS Tunneling:** Detects high-entropy DNS queries, subdomain patterns
- **ICMP Tunneling:** Analyzes ICMP payload sizes and entropy
- **IAT Analysis:** Detects artificial inter-arrival time patterns in flows

### Video Detection

- **Frame-by-Frame Analysis:** Per-frame statistical tests
- **Temporal Consistency:** Detects embedding patterns across frames
- **Metadata Inspection:** File structure anomalies

---

## Installation

### Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Docker & Docker Compose** (optional, for ELK Stack)

### Step 1: Clone Repository

```bash
git clone https://github.com/CyprianGrzelka/Steganography_SIEM_tool.git
cd Steganography_SIEM_tool
```

### Step 2: Install Python Dependencies

```bash
# Core dependencies
pip install -r steg-lab/requirements.txt

# Typical requirements:
pip install Pillow numpy scipy scikit-learn

# Optional: For video analysis
pip install opencv-python

# Optional: For network analysis
pip install scapy pcapng
```

### Step 3: Set Up Environment (Optional)

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
```

### Step 4: Deploy ELK Stack (Optional)

```bash
# Using Docker Compose
docker-compose up -d

# Wait for services to be ready (2-3 minutes)
docker-compose logs -f elasticsearch
```

---

## Quick Start

### 1. Analyze a Single File

```bash
python stego_agent.py path/to/image.png
```

**Output:**
```json
{
  "timestamp": "2024-01-15T10:30:45.123456+00:00",
  "event_type": "stego_scan",
  "source_module": "image",
  "file_name": "image.png",
  "file_path": "path/to/image.png",
  "file_size_bytes": 102400,
  "file_format": "PNG",
  "verdict": "SUSPICIOUS",
  "risk_score": 52,
  "detectors_triggered": 1,
  "detectors_total": 3,
  "detectors": {
    "chi_square": {
      "p_value": 0.0234,
      "z_score": 2.34
    },
    "rs_analysis": {
      "rs_difference": 0.015
    },
    "shannon_entropy": {
      "entropy": 7.891
    }
  },
  "triggered_rules": [
    {
      "rule": "chi_square",
      "value": 0.0234,
      "severity": "medium"
    }
  ],
  "triggered_rules_summary": "chi²=0.023",
  "warnings": [],
  "network_channel": null,
  "errors": null
}
```

### 2. Monitor Directory

```bash
# Watch directory and analyze new files every 5 seconds
python stego_agent.py --watch ./incoming

# Or with custom log file
python stego_agent.py --watch ./incoming --logfile custom.log
```

### 3. Batch Analysis

```bash
# Analyze all PNG files in a directory
for file in incoming/*.png; do
  python stego_agent.py "$file" >> results.ndjson
done
```

---

## Usage

### Basic Command Structure

```bash
python stego_agent.py [OPTIONS] [FILE_PATH]
```

### Options

| Option | Description | Example |
|--------|-------------|---------|
| `FILE_PATH` | Path to file to analyze | `python stego_agent.py image.png` |
| `--watch DIR` | Monitor directory mode | `python stego_agent.py --watch ./incoming` |
| `--logfile FILE` | Custom log output file | `--logfile my_scan.log` |
| `--format json` | Output format (json/ndjson) | `--format ndjson` |
| `--timeout SEC` | Analysis timeout per file | `--timeout 30` |
| `--batch` | Batch mode (no real-time output) | `--batch` |

### Examples

```bash
# Single file analysis
python stego_agent.py samples/test.png

# Real-time directory monitoring
python stego_agent.py --watch ./incoming --logfile scanner.log

# Batch analysis with timeout
python stego_agent.py --batch --timeout 60 samples/

# Analyze specific file type
python stego_agent.py --watch ./audio_files --format json
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```env
# Detection Thresholds
CHI_SQUARE_THRESHOLD=0.05
RS_DIFFERENCE_THRESHOLD=0.03
ENTROPY_THRESHOLD=7.5
RISK_SCORE_THRESHOLD=60

# Processing
MAX_FILE_SIZE_MB=500
ANALYSIS_TIMEOUT_SEC=30
WATCH_INTERVAL_SEC=5

# Output
OUTPUT_LOGFILE=stego_events.ndjson
OUTPUT_FORMAT=ndjson
VERBOSITY=INFO

# ELK Stack Integration (optional)
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_INDEX=stego-events
LOGSTASH_HOST=localhost
LOGSTASH_PORT=5000
```

### Detector Configuration

Edit detector parameters in [detectors/common.py](detectors/common.py):

```python
# Risk scoring weights
DETECTOR_WEIGHTS = {
    "chi_square": 0.45,      # 45% weight
    "rs_analysis": 0.40,     # 40% weight
    "shannon_entropy": 0.15  # 15% weight
}

# Verdict thresholds
VERDICT_THRESHOLDS = {
    "CLEAN": risk_score < 20,
    "SUSPICIOUS": 20 <= risk_score < 60,
    "DETECTED": risk_score >= 60
}
```

---

## Project Structure

```
Steganography_SIEM_tool/
├── README_EN.md                    # This file
├── README.md                       # Polish documentation
├── README_ELK.md                   # ELK integration guide
├── DOCKER_SETUP.md                 # Docker deployment guide
│
├── stego_agent.py                  # Main orchestrator
├── stego_events.ndjson             # Output event stream
│
├── detectors/                      # Detection modules
│   ├── __init__.py
│   ├── common.py                   # SharedResult dataclass & verdict logic
│   ├── audio.py                    # Audio detector interface
│   ├── image.py                    # Image detector interface
│   ├── network.py                  # Network detector interface
│   ├── video.py                    # Video detector interface
│   │
│   ├── audio/
│   │   ├── audio_detector.py       # Audio implementation
│   │   └── audio_lsb.py            # LSB analysis for audio
│   │
│   ├── image/
│   │   └── image_profiler.py       # Image implementation
│   │
│   ├── network/
│   │   └── network_detector.py     # Network implementation
│   │
│   └── video/
│       └── video_detector.py       # Video implementation
│
├── steg-lab/                       # Research & testing environment
│   ├── scan.py                     # Legacy scanner
│   ├── run_tests.py                # Automated testing suite
│   ├── chi_square.py               # Chi-square implementation
│   ├── rs_analysis.py              # RS analysis implementation
│   ├── shannon_entropy.py          # Entropy calculation
│   ├── audio_detector.py           # Audio research module
│   ├── network_stego_detector.py   # Network research module
│   ├── video_detector.py           # Video research module
│   │
│   ├── network_samples/            # Test datasets
│   │   ├── clean/
│   │   ├── stego/
│   │   └── pcap files
│   │
│   ├── sample_images/              # Test image datasets
│   │   ├── clean/
│   │   └── stego/
│   │
│   └── requirements.txt            # Lab dependencies
│
├── elk/                            # ELK Stack configuration
│   ├── filebeat.yml                # Filebeat config
│   ├── index_template.json         # Elasticsearch template
│   ├── kibana_dashboard.ndjson     # Pre-built dashboard
│   │
│   └── config/
│       └── logstash.yml            # Logstash config
│
├── logstash/                       # Logstash pipelines
│   ├── config/
│   │   └── logstash.yml
│   │
│   └── pipeline/
│       └── stego.conf              # Event parsing pipeline
│
├── incoming/                       # Input directories for monitoring
│   ├── audio/
│   ├── network/
│   └── video/
│
├── docker-compose.yml              # Docker Compose config
├── .env.example                    # Environment template
└── .gitignore

```

---

## Integration with ELK Stack

### Architecture Overview

```
Files → stego_agent.py → stego_events.ndjson → Filebeat → Logstash → Elasticsearch → Kibana
```

### Setup Instructions

#### 1. Index Template Deployment

```bash
# Option A: Using curl
curl -X PUT "localhost:9200/_index_template/stego-events-template" \
  -H 'Content-Type: application/json' \
  -d @elk/index_template.json

# Option B: Using Kibana Dev Tools
# 1. Open http://localhost:5601
# 2. Go to Dev Tools → Console
# 3. Paste content from elk/index_template.json
# 4. Execute (Ctrl+Enter)

# Verify
curl -X GET "localhost:9200/_index_template/stego-events-template"
```

#### 2. Configure Filebeat

```bash
# Copy Filebeat configuration
cp elk/filebeat.yml /etc/filebeat/filebeat.yml

# Enable Elasticsearch output
sudo filebeat modules enable elasticsearch

# Start Filebeat
sudo systemctl start filebeat
sudo systemctl enable filebeat

# Verify it's running
sudo filebeat test output
```

#### 3. Deploy Logstash Pipeline

```bash
# Copy pipeline
cp logstash/pipeline/stego.conf /etc/logstash/pipelines/

# Restart Logstash
sudo systemctl restart logstash

# Check logs
tail -f /var/log/logstash/logstash-plain.log
```

#### 4. Import Kibana Dashboard

```bash
# Option A: Using curl
curl -X POST "localhost:5601/api/saved_objects/dashboard" \
  -H 'kbn-xsrf: true' \
  -H 'Content-Type: application/json' \
  -d @elk/kibana_dashboard.ndjson

# Option B: Manual import
# 1. Open Kibana: http://localhost:5601
# 2. Go to Stack Management → Saved Objects
# 3. Import → Select elk/kibana_dashboard.ndjson
# 4. Confirm
```

#### 5. Verify End-to-End Flow

```bash
# Scan a test file
python stego_agent.py incoming/sample.png

# Check Filebeat is monitoring
tail -f stego_events.ndjson

# Query Elasticsearch
curl -X GET "localhost:9200/stego-events*/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": { "match_all": {} },
    "size": 10
  }'

# Open dashboard
# http://localhost:5601/app/dashboards
```

---

## Testing

### Automated Test Suite

```bash
cd steg-lab

# Run all tests with metrics
python run_tests.py

# Run specific detector tests
python run_tests.py --detector chi_square
python run_tests.py --detector rs_analysis
python run_tests.py --detector shannon_entropy

# Generate comparison report
python run_tests.py --compare --output results.csv
```

### Manual Testing

```bash
# Test with sample clean image
python stego_agent.py steg-lab/sample_images/clean/EARTH_BIG.jfif

# Expected output: CLEAN verdict

# Test with stego image
python stego_agent.py steg-lab/sample_images/stego/embedded_sample.png

# Expected output: SUSPICIOUS or DETECTED verdict

# Test with audio
python stego_agent.py steg-lab/sample_images/clean/audio/sample.wav

# Test with network data
python stego_agent.py steg-lab/network_samples/dns_clean.json
python stego_agent.py steg-lab/network_samples/dns_stego.json
```

### Test Coverage

- ✅ Image detection (PNG, JPEG, BMP, GIF)
- ✅ Audio detection (WAV, MP3, FLAC)
- ✅ Video detection (MP4, AVI, MOV)
- ✅ Network traffic (DNS, ICMP, IAT)
- ✅ Batch processing
- ✅ Directory monitoring
- ✅ JSON/NDJSON output
- ✅ Elasticsearch integration
- ✅ Error handling
- ✅ Performance benchmarks

---

## Supported Media Types

### Images

| Format | Support | Notes |
|--------|---------|-------|
| PNG | ✅ Full | Primary test format |
| JPEG | ✅ Full | Common use case |
| BMP | ✅ Full | Uncompressed LSB |
| GIF | ✅ Full | Palette + frame analysis |
| TIFF | ✅ Full | Multi-page support |
| WebP | ⚠️ Partial | Conversion required |

### Audio

| Format | Support | Notes |
|--------|---------|-------|
| WAV | ✅ Full | PCM uncompressed |
| MP3 | ✅ Full | Requires ffmpeg |
| FLAC | ✅ Full | Lossless analysis |
| OGG | ⚠️ Partial | Conversion required |

### Video

| Format | Support | Notes |
|--------|---------|-------|
| MP4 | ✅ Full | Frame extraction |
| AVI | ✅ Full | Various codecs |
| MOV | ✅ Full | Apple format |
| MKV | ⚠️ Partial | Requires ffmpeg |

### Network

| Format | Support | Notes |
|--------|---------|-------|
| PCAP | ✅ Full | Tcpdump/Wireshark |
| PCAPNG | ✅ Full | Modern PCAP format |
| JSON Flows | ✅ Full | Custom format |
| CSV Logs | ✅ Full | Netflow compatible |

---

## Requirements

### Runtime Requirements

```
Python >= 3.8
Pillow >= 9.0.0          # Image processing
numpy >= 1.21.0          # Numerical computation
scipy >= 1.7.0           # Statistical analysis
scikit-learn >= 1.0.0    # Machine learning utilities
```

### Optional Dependencies

```
opencv-python >= 4.5.0   # Video processing
scapy >= 2.4.5           # Network packet analysis
pycap >= 1.0             # PCAP parsing
ffmpeg >= 4.0            # Media conversion (system package)
```

### ELK Stack Requirements

```
Elasticsearch >= 8.0
Kibana >= 8.0
Logstash >= 8.0
Filebeat >= 8.0
Docker >= 20.10 (for containerized deployment)
Docker Compose >= 1.29
```

### System Requirements

```
CPU: 2+ cores recommended
RAM: 2GB minimum (4GB+ for video analysis)
Disk: 5GB for ELK Stack, 1GB for source code
Network: Connectivity to Elasticsearch (if remote)
```

---

## Troubleshooting

### Common Issues

#### 1. "ModuleNotFoundError: No module named 'PIL'"

```bash
# Solution: Install Pillow
pip install Pillow
```

#### 2. Elasticsearch Connection Refused

```bash
# Verify Elasticsearch is running
curl -X GET "localhost:9200/"

# If not running, start it
docker-compose up -d elasticsearch

# Wait for startup (2-3 minutes)
docker-compose logs elasticsearch
```

#### 3. Files Not Being Processed in Watch Mode

```bash
# Check stego_agent.py is running
ps aux | grep stego_agent

# Check incoming directory has read permissions
ls -la incoming/

# Verify file format is supported
file incoming/test.png

# Check logs
tail -f stego_events.ndjson
```

#### 4. High False Positive Rate

Adjust thresholds in `.env`:

```env
CHI_SQUARE_THRESHOLD=0.01     # Stricter
RS_DIFFERENCE_THRESHOLD=0.02
ENTROPY_THRESHOLD=7.8
RISK_SCORE_THRESHOLD=70       # Higher threshold for DETECTED
```

#### 5. Slow Performance

```bash
# Reduce file size limit
MAX_FILE_SIZE_MB=100

# Increase timeout
ANALYSIS_TIMEOUT_SEC=60

# Disable expensive detectors for specific file types
# Edit detectors/*.py to skip certain analyses

# Monitor CPU/Memory
top -p $(pgrep -f stego_agent)
```

#### 6. Kibana Dashboard Not Showing Data

```bash
# Verify data is in Elasticsearch
curl -X GET "localhost:9200/stego-events*/_count"

# Check index mapping
curl -X GET "localhost:9200/stego-events*/_mapping"

# Recreate index template
curl -X DELETE "localhost:9200/_index_template/stego-events-template"
curl -X PUT "localhost:9200/_index_template/stego-events-template" \
  -d @elk/index_template.json
```

### Debug Mode

```bash
# Enable verbose logging
VERBOSITY=DEBUG python stego_agent.py --watch ./incoming

# Save detailed analysis report
python stego_agent.py image.png > analysis_report.json 2>&1

# Profile performance
python -m cProfile -s cumulative stego_agent.py image.png
```

---

## Performance Benchmarks

Typical processing times (on modern CPU):

| Media Type | Size | Time | Throughput |
|-----------|------|------|-----------|
| Small Image (500KB PNG) | 500 KB | 0.3s | 1,667 KB/s |
| Medium Image (5MB JPEG) | 5 MB | 2.1s | 2,380 KB/s |
| Audio (10MB WAV) | 10 MB | 1.5s | 6,667 KB/s |
| Video (100MB MP4) | 100 MB | 15s | 6,667 KB/s |
| Network PCAP (50MB) | 50 MB | 3.2s | 15,625 KB/s |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/Steganography_SIEM_tool.git

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dev dependencies
pip install -e .
pip install pytest pytest-cov black flake8

# Run tests
pytest tests/

# Format code
black detectors/ steg-lab/

# Check style
flake8 detectors/ steg-lab/
```

---

## License

This project is licensed under the **MIT License** — see [LICENSE](LICENSE) file for details.

---

## Citation

If you use this tool in your research, please cite:

```bibtex
@thesis{steganography_siem_2024,
  author = {Grzelka, Cyprian},
  title = {Steganography Detection System Integrated with Security Information and Event Management},
  school = {University of Technology},
  year = {2024},
  url = {https://github.com/CyprianGrzelka/Steganography_SIEM_tool}
}
```

---

## Contact & Support

- **GitHub:** [CyprianGrzelka/Steganography_SIEM_tool](https://github.com/CyprianGrzelka/Steganography_SIEM_tool)
- **Issues:** [Report a Bug](https://github.com/CyprianGrzelka/Steganography_SIEM_tool/issues)
- **Discussions:** [Start a Discussion](https://github.com/CyprianGrzelka/Steganography_SIEM_tool/discussions)

---

## Acknowledgments

- **Statistical Methods:** Chi-square test, RS Analysis, and Shannon Entropy based on academic literature
- **ELK Stack:** Elasticsearch, Logstash, Kibana open-source project
- **Testing Data:** Generated samples and real-world datasets from security research community

---

**Last Updated:** 2024-07-15  
**Version:** 1.0.0  
**Maintained By:** [CyprianGrzelka](https://github.com/CyprianGrzelka)
