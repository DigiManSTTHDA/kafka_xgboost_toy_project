# Kafka-XGBoost-Titanic-Demo

## Projektziel

Demonstration einer skalierbaren ML-Inferenz-Pipeline für Streamingdaten mit Kafka, Docker und XGBoost.  
Als Beispiel wird das bekannte Titanic-Dataset verwendet, um eine Binary Classification („Survived“: 1/0) zu zeigen – unabhängig vom realen Business Case.

---

## Features

- Event-Streaming mit Kafka (Producer/Consumer Pattern)
- ML-Inferenz mit schnellem XGBoost-Modell
- Echtzeit-Ausgabe ins Kafka-Alert-Topic
- Monitoring mit Prometheus & Grafana
- Komplett dockerisiert und reproduzierbar

---

## Verzeichnisstruktur

- `.venv/`            – Python Virtual Environment  
- `model_training/`   – ML-Training, Datenset (`titanic.csv`), XGBoost-Modell  
- `producer/`         – Producer für Streaming-Events  
- `consumer/`         – ML-Consumer inkl. Inferenz, Alert-Topic  
- `monitoring/`       – Prometheus/Grafana-Konfiguration  
- `docker-compose.yml` – Multi-Service Setup

---

## Getting Started

### 1. Titanic Dataset herunterladen

- Gehe zu [Kaggle Titanic Competition](https://www.kaggle.com/competitions/titanic/data)
- Lade die Datei `train.csv` herunter
- Speichere sie als `model_training/titanic.csv`

### 2. Python-Abhängigkeiten installieren

python -m venv .venv
source .venv/bin/activate # oder .venv\Scripts\activate (Windows)

_Mindestpakete: `kafka-python`, `xgboost`, `scikit-learn`, `pandas`, `joblib`_

### 3. XGBoost-Modell trainieren

cd model_training
python train_titanic_model.py
→ erzeugt `titanic_model.pkl` (nicht ins Repo hochladen!)

### 4. Docker-Container starten (Kafka, Prometheus, Grafana)

docker-compose up -d^
Container werden gestartet und Kafka ist unter Port 9092 verfügbar.  
Grafana läuft auf Port 3000, Prometheus auf 9090.

### 5. Producer starten (Streaming-Daten erzeugen)

cd producer
python produce_transactions.py
Erzeugt und sendet Events aus dem Titanic-Dataset an Kafka.

### 6. ML-Consumer starten (Inferenz und Alerts)

cd consumer
python consume_and_score.py

Events werden bewertet, alle „Survived=1“ ins Topic `titanic-alerts` geschrieben.

### 7. Monitoring und Visualisierung

- Besuche Grafana auf http://localhost:3000 (Default-Passwort: admin)
- In Prometheus (`localhost:9090`) sind alle relevanten Metriken beobachtbar


