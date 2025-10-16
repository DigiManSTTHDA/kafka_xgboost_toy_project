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
    bootstrap_servers=KAFKA_BROKER, # wo ist der kafka broker?
    value_serializer=lambda v: json.dumps(v).encode('utf-8') #wird automatisch bei jedem send() aufgerufen. 
    #Kafka akzeptiert nur bytes. value_serializer wandelt dict in json string und dann in bytes um (utf-8 encoding)
)

def event_from_row(row): #macht aus einer DataFrame Zeile ein python dict
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
        row = df.sample(1).iloc[0] #zufällige Zeile aus DataFrame auswählen
        if pd.isna(row[['Age', 'Fare']]).any(): continue  # wenn Age oder Fare NaN ist, überspringen
        event = event_from_row(row) # event aus Zeile erstellen: Python dict (wird bei send() via value_serializer zu JSON → Bytes)
        producer.send(TOPIC, event) #event an kafka topic senden (siehe value_serializer oben!)
    time.sleep(1)
