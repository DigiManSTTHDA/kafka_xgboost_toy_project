import json
import time
import numpy as np
from kafka import KafkaConsumer, KafkaProducer
import joblib
from prometheus_client import start_http_server, Counter, Gauge, Histogram

# Prometheus Metrics
start_http_server(8000)
TRANSACTIONS_PROCESSED = Counter('transactions_processed_total', 'Anzahl verarbeiteter Transaktionen')
SURVIVED_DETECTED = Counter('survived_detected_total', 'Anzahl Überlebende')
PROCESS_LATENCY = Histogram('processing_latency_seconds', 'Verarbeitungsdauer pro Batch', buckets=(.01, .025, .05, .075, .1, .15, .2, .5, 1, 5))
SURVIVAL_RATE = Gauge('survival_rate', 'Anteil Überlebende / Gesamt (%)')

KAFKA_BROKER = 'localhost:9092'
INPUT_TOPIC = 'titanic-events'
OUTPUT_TOPIC = 'titanic-alerts'

consumer = KafkaConsumer(
    INPUT_TOPIC,
    bootstrap_servers=KAFKA_BROKER,
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    value_deserializer=lambda v: json.loads(v.decode('utf-8'))
)
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
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
    msg = next(consumer)
    event = msg.value
    batch.append(event)
    if len(batch) < BATCH_SIZE:
        continue
    X_batch = np.array([features_from_event(e) for e in batch])
    X_batch[:, [2, 5]] = scaler.transform(X_batch[:, [2, 5]])
    y_pred = model.predict(X_batch)
    n_survived = np.sum(y_pred)
    print(f'Batch processed: {len(batch)}, Survived detected: {n_survived}')
    for e, survived in zip(batch, y_pred):
        if survived:
            producer.send(OUTPUT_TOPIC, e)
    batch = []
    start = time.time()
    TRANSACTIONS_PROCESSED.inc(len(batch))
    SURVIVED_DETECTED.inc(int(n_survived))
    if TRANSACTIONS_PROCESSED._value.get() > 0:
        SURVIVAL_RATE.set(float(SURVIVED_DETECTED._value.get()) / TRANSACTIONS_PROCESSED._value.get() * 100)
    else:
        SURVIVAL_RATE.set(0)
    PROCESS_LATENCY.observe(time.time()-start)
