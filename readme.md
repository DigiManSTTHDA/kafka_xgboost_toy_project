# Kafka-XGBoost-Titanic-Demo

## Projektziel

Lernprojekt zur Demonstration einer skalierbaren ML-Inferenz-Pipeline für Streamingdaten mit **Kafka**, **Docker** und **XGBoost**.

Als Beispiel wird das Titanic-Dataset verwendet für Binary Classification ("Survived": 1/0). Das Projekt zeigt die Architektur und Konzepte – lediglich eine Skizze eines realen Business Case. Toy-Projekt mit didaktischem Fokus.

---

## Architektur-Überblick

```
Producer (produce_transactions.py)
    ↓ 20 Events/Sek
Kafka Topic: titanic-events (Event Log)
    ↓
Consumer (consume_and_score.py)
    ├→ XGBoost Batch-Inferenz (10 Events)
    ├→ Prometheus Metriken (Port 8000)
    └→ Kafka Topic: titanic-alerts (nur Survived=1)
         ↓
    Prometheus (scrapet Metriken alle 5s)
         ↓
    Grafana (Visualisierung)
```

---

## Kernkonzepte

### 1. Apache Kafka

**Was ist Kafka?**
- **Distributed Event Streaming Platform** – kein einfaches Message Queue System
- Events werden in einem **persistenten Log** gespeichert (nicht gelöscht beim Lesen)
- **Topics** = Kategorien für Events (hier: `titanic-events`, `titanic-alerts`)
- **Producer** schreibt Events ins Topic
- **Consumer** liest Events aus dem Topic (mit Offset-Tracking)

**Unterschied zu RabbitMQ/Redis:**
- RabbitMQ: Message wird konsumiert → weg
- Redis: In-Memory, kein persistenter Log
- Kafka: Events bleiben im Log (Retention), mehrere Consumer können parallel lesen, Replay möglich

**In diesem Projekt:**
- Producer sendet zufällige Titanic-Passagier-Events (JSON)
- Consumer liest Events, führt ML-Inferenz aus
- Alerts gehen zurück in ein anderes Kafka-Topic

### 2. XGBoost (Gradient Boosted Trees)

**Warum XGBoost statt Neural Networks?**
- ✅ Schnelle Inferenz (1-10ms) – keine GPU nötig
- ✅ Exzellent für strukturierte/tabellarische Daten mit Hunderten features
- ✅ Interpretierbar (Feature Importance)
- ✅ Weniger Datenhunger als Deep Learning

**Batching:**
- Consumer sammelt 10 Events → eine Inferenz für alle 10 gleichzeitig
- Effizienter als 10 einzelne Inferenzen (Vektorisierung)

### 3. Prometheus & Grafana

**Monitoring-Stack:**
- **Prometheus:** Time-Series Database für Metriken
- **Grafana:** Visualisierungs-Dashboard

**Wie funktioniert's?**
1. Consumer startet HTTP-Server auf Port 8000 (`/metrics` Endpoint)
2. Prometheus **scraped** (Pull-Modell) alle 5 Sekunden die Metriken
3. Grafana liest aus Prometheus und visualisiert

**Metriken in diesem Projekt:**
- `transactions_processed_total`: Counter (Events verarbeitet)
- `survived_detected_total`: Counter (Überlebende erkannt)
- `processing_latency_seconds`: Histogram (Inferenz-Latenz)
- `survival_rate`: Gauge (Überlebensrate in %)

---

## Event-Flow im Detail

### Producer → Kafka

```python
# 1. Zufällige Zeile aus DataFrame
row = df.sample(1).iloc[0]

# 2. DataFrame → Python Dict
event = {'Pclass': 3, 'Sex_enc': 1, 'Age': 22.0, ...}

# 3. Senden an Kafka
producer.send(TOPIC, event)
# → value_serializer: dict → JSON-String → UTF-8 Bytes
# → landet in Kafka Topic 'titanic-events'
```

### Kafka → Consumer

```python
# 1. Event für Event aus Kafka lesen
msg = next(consumer)
event = msg.value  # value_deserializer: Bytes → JSON → dict

# 2. Batch sammeln (10 Events)
batch.append(event)

# 3. Bei 10 Events: Inferenz
X_batch = np.array([...])  # 10 Zeilen, 6 Spalten
X_batch[:, [2, 5]] = scaler.transform(...)  # Age, Fare skalieren
y_pred = model.predict(X_batch)  # XGBoost: [0,1,1,0,1,...]

# 4. Nur Survived=1 ins Alert-Topic
for e, survived in zip(batch, y_pred):
    if survived:
        producer.send('titanic-alerts', e) #jeder Consumer kann wieder producer sein. Für neues topic. So wie hier.

# 5. Prometheus-Metriken updaten
TRANSACTIONS_PROCESSED.inc(10)
PROCESS_LATENCY.observe(...)
```

---

## Features

- ✅ Event-Streaming mit Kafka (Producer/Consumer Pattern)
- ✅ ML-Inferenz mit XGBoost-Modell (Batch-Processing)
- ✅ Echtzeit-Alerts in separates Kafka-Topic
- ✅ Monitoring mit Prometheus & Grafana
- ✅ Komplett dockerisiert und reproduzierbar

---

## Verzeichnisstruktur

```
.
├── .venv/                      # Python Virtual Environment
├── model_training/
│   ├── titanic.csv             # Kaggle Dataset
│   ├── train_titanic_model.py  # XGBoost Training
│   └── titanic_model.pkl       # Gespeichertes Model (nicht im Repo)
├── producer/
│   └── produce_transactions.py # Event-Generator (20/Sek)
├── consumer/
│   └── consume_and_score.py    # ML-Consumer + Prometheus
├── monitoring/
│   └── prometheus.yml          # Scrape-Konfiguration
├── docker-compose.yml          # Kafka, Prometheus, Grafana
└── readme.md
```

---

## Getting Started

### 1. Titanic Dataset herunterladen

- Gehe zu [Kaggle Titanic Competition](https://www.kaggle.com/competitions/titanic/data)
- Lade `train.csv` herunter
- Speichere als `model_training/titanic.csv`

### 2. Python-Abhängigkeiten installieren

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install kafka-python xgboost scikit-learn pandas joblib prometheus-client
```

### 3. XGBoost-Modell trainieren

```bash
cd model_training
python train_titanic_model.py
```

**Output:** `titanic_model.pkl` (Model + Scaler). In den consumer folder verschieben.

### 4. Docker-Container starten

```bash
docker-compose up -d
```

**Services:**
- Kafka: Port 9092
- Prometheus: Port 9090
- Grafana: Port 3000

### 5. Producer starten

```bash
cd producer
python produce_transactions.py
```

**Was passiert:** 20 Events/Sek werden an Kafka-Topic `titanic-events` gesendet.

### 6. Consumer starten

```bash
cd consumer
python consume_and_score.py
```

**Was passiert:**
- Liest Events aus `titanic-events`
- XGBoost-Inferenz (Batch à 10)
- Alerts → `titanic-alerts` Topic
- Metriken → `localhost:8000/metrics`

### 7. Monitoring ansehen

**Prometheus:**
- http://localhost:9090
- Query-Beispiele:
  - `rate(transactions_processed_total[1m])` → Events/Sek
  - `histogram_quantile(0.5, sum(rate(processing_latency_seconds_bucket[1m])) by (le))` → Median-Latenz

**Grafana:**
- http://localhost:3000 (admin/admin)
- Data Source hinzufügen: Prometheus (`http://prometheus:9090`)
- Dashboard erstellen mit obigen Queries

**Raw Metriken:**
- http://localhost:8000/metrics (Consumer Prometheus Endpoint)

---

## Nützliche Prometheus-Queries

```promql
# Durchsatz (Events/Sekunde)
rate(transactions_processed_total[1m])

# Median Latenz (50. Perzentil)
histogram_quantile(0.5, sum(rate(processing_latency_seconds_bucket[1m])) by (le))

# 95. Perzentil Latenz
histogram_quantile(0.95, sum(rate(processing_latency_seconds_bucket[1m])) by (le))

# Survival Rate in %
(survived_detected_total / transactions_processed_total) * 100

# Durchschnittliche Latenz
rate(processing_latency_seconds_sum[1m]) / rate(processing_latency_seconds_count[1m])
```

---

## Technische Details

### Kafka-Konfiguration

**KRaft-Mode (ohne Zookeeper - legacy):**
- Moderne Kafka-Architektur (ab Version 2.8+)
- Einfachere Verwaltung, weniger Overhead

**Auto-Create Topics:**
- Topics werden automatisch erstellt beim ersten Send
- `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"`

### Consumer-Offset Management

```python
auto_offset_reset='earliest'  # Bei erstem Start: alle Events von Anfang
enable_auto_commit=True       # Offset automatisch speichern
```

**Was bedeutet das?**
- Consumer merkt sich Position (Offset) im Log – **gespeichert in Kafka selbst** (Topic `__consumer_offsets`)
- Bei Restart: Consumer fragt Kafka "Wo war ich?" → macht dort weiter (kein Datenverlust)
- `earliest`: Neuer Consumer (ohne gespeicherten Offset) liest alle historischen Events

**Crash-Szenario:**
1. Consumer verarbeitet Event #247
2. `enable_auto_commit=True` → Offset wird zu Kafka geschrieben
3. Consumer crasht
4. Neuer Consumer startet → liest Offset #247 aus Kafka
5. Macht bei Event #248 weiter ✅

### Resilience & Single Points of Failure

**Achtung: Demo-Setup ist natürlich NICHT production-ready!**

```yaml
# docker-compose.yml
KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1  # Nur 1 Broker, keine Redundanz!
```

**Was passiert bei Kafka-Crash?**
- ❌ Single-Broker → keine Replikation
- ❌ Disk korrupt → Events verloren
- ❌ Kein Automatic Failover

Es ist ein PoC...

### Skalierung

**Was würde bei höherer Last passieren?**
- Mehrere Consumer in gleicher Consumer Group → Kafka verteilt Events automatisch
- Beispiel: 3 Consumer → jeder bearbeitet ~33% der Events
- XGBoost-Inferenz ohne GPU: ~10.000-50.000 Events/Sek möglich (horizontal skaliert)

---

## Warum "Titanic" statt Fraud-Detection?

**Pädagogischer Ansatz:**
- Fraud-Datasets oft unbalanced, schwer zu trainieren
- Titanic: bekannt, sauber, einfach zu verstehen
- Fokus liegt auf **Kafka + ML-Pipeline**, nicht auf Modell-Qualität

**Mapping:**
- `Survived=1` → "legitime Transaktion"
- `Survived=0` → "fraudulente Transaktion"

In Production würdest du ein echtes Fraud-Dataset verwenden (z.B. Credit Card Fraud Detection).

---

## Ist XGBoost nicht Overkill für Titanic?

**Schon, aber...**

**Typischerweise macht man mit Titanic:**
1. **Logistic Regression** (Baseline, interpretierbar)
2. **Decision Tree** (Visualisierbar, einfach zu erklären)
3. **Random Forest** (Ensemble, robuster)

**XGBoost glänzt bei:**
- Kaggle Competitions mit strukturierten Daten
- Hunderte Features (nicht 6 wie hier), deswegen geeignet für Fraud detection
- Komplexe Feature-Interaktionen
- Große Datasets (>100k Zeilen, nicht 900)

**Warum trotzdem XGBoost in diesem Projekt?**
- ✅ Lernziel ist **Kafka + Inferenz-Pipeline**, nicht Modell-Optimierung
- ✅ XGBoost zeigt "Enterprise ML" (wird real bei Fraud Detection verwendet)
- ✅ Schnelle Inferenz demonstrieren (<10ms)
- ✅ Modell-Qualität ist sekundär – Architektur steht im Fokus

**Performance-Vergleich fehlt bewusst** – für Production würdest du mehrere Modelle evaluieren (Accuracy, Precision, Recall, F1). Hier geht es um die Pipeline, nicht um optimale Titanic-Predictions.

---

## Lessons Learned / Konzepte

### 1. Kafka ist kein Queue-System
- Events bleiben im Log (Retention-basiert)
- Mehrere Consumer können parallel lesen
- Replay möglich (Debug, Reprocessing)

### 2. Batching verbessert Throughput
- 10 Events auf einmal inferieren ist schneller als 10x einzeln
- Trade-off: Latenz vs. Throughput

### 3. Monitoring ist essentiell
- Ohne Metriken: keine Ahnung ob System funktioniert
- Prometheus + Grafana = Standard für ML-Pipelines

### 4. XGBoost für strukturierte Daten
- Oft besser als Neural Networks bei Tabellendaten
- Schneller, interpretierbarer, weniger Daten nötig

---

**Happy Learning! 🚀**