import pandas as pd
import json
import time
import random
from kafka import KafkaProducer

df = pd.read_csv('../model_training/titanic.csv')
df['Sex_enc'] = (df['Sex'] == 'male').astype(int)

KAFKA_BROKER = 'localhost:9092'
TOPIC = 'titanic-events'

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def event_from_row(row):
    return {
        'Pclass': int(row.Pclass),
        'Sex_enc': int(row.Sex_enc),
        'Age': float(row.Age),
        'SibSp': int(row.SibSp),
        'Parch': int(row.Parch),
        'Fare': float(row.Fare)
    }

EVENTS_PER_SEC = 20
while True:
    for _ in range(EVENTS_PER_SEC):
        row = df.sample(1).iloc[0]
        if pd.isna(row[['Age', 'Fare']]).any(): continue  # Skip rows with NA
        event = event_from_row(row)
        producer.send(TOPIC, event)
    time.sleep(1)
