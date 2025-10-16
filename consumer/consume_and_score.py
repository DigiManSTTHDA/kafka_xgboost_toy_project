import json
import time
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
import joblib
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# Prometheus Metrics
start_http_server(8000) #expose metrics at localhost:8000/metrics (prometheus default)
TRANSACTIONS_PROCESSED = Counter('transactions_processed_total', 'Anzahl verarbeiteter Transaktionen') # wird unter localhost:8000/metrics als transactions_processed_total angezeigt
SURVIVED_DETECTED = Counter('survived_detected_total', 'Anzahl Überlebende')
PROCESS_LATENCY = Histogram('processing_latency_seconds', 'Verarbeitungsdauer pro Batch', buckets=(.01, .025, .05, .075, .1, .15, .2, .5, 1, 5))
SURVIVAL_RATE = Gauge('survival_rate', 'Anteil Überlebende / Gesamt (%)')
# prometheus (prometheus.yml) muss so konfiguriert sein, dass es diesen Port abfragt, also 8000 in diesem Fall
KAFKA_BROKER = 'localhost:9092' #hardcoded, aber ok for demo. Sonst in env var aus docker-compose.yml lesen (z.B)
INPUT_TOPIC = 'titanic-events'
OUTPUT_TOPIC = 'titanic-alerts'

consumer = KafkaConsumer(
    INPUT_TOPIC, # Das ist ein consumer für Kafka events im Topic 'titanic-events'
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER, # das hier ist aber auch ein producer für kafka events im Topic 'titanic-alerts'
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)
model_bundle = joblib.load('titanic_model.pkl')
model = model_bundle['model']
scaler = model_bundle['scaler']

def features_from_event(event):
    arr = [
      event['Pclass'],
      event['Sex_enc'],
      event['Age'],
      event['SibSp'],
      event['Parch'],
      event['Fare'],
    ]
    return arr

batch = []
BATCH_SIZE = 10
while True:
    msg = next(consumer) #get next event from kafka topic
    event = msg.value
    batch.append(event) #aggregate events to batch
    if len(batch) < BATCH_SIZE: #until batch is full,
        continue
    start = time.time()
    X_batch = np.array([features_from_event(e) for e in batch]) # Liste von event dicts → NumPy Matrix (10x6)
    X_batch[:, [2, 5]] = scaler.transform(X_batch[:, [2, 5]]) #nur Age und Fare skalieren
    y_pred = model.predict(X_batch) # xgboost macht batch inferenz
    n_survived = np.sum(y_pred) #wie viele Überlebende in batch?
    print(f'Batch processed: {len(batch)}, Survived detected: {n_survived}')
    for e, survived in zip(batch, y_pred): #für jedes event im batch ein neues topic event senden
        if survived:
            producer.send(OUTPUT_TOPIC, e)
    batch_size = len(batch)
    batch = []
    
    TRANSACTIONS_PROCESSED.inc(batch_size) # prometheus metrics updaten
    SURVIVED_DETECTED.inc(int(n_survived))
    if TRANSACTIONS_PROCESSED._value.get() > 0:
        SURVIVAL_RATE.set(float(SURVIVED_DETECTED._value.get()) / TRANSACTIONS_PROCESSED._value.get() * 100)
    else:
        SURVIVAL_RATE.set(0)
    PROCESS_LATENCY.observe(time.time() - start) # misst die Latenz der Batch Verarbeitung, nicht pro Event!
