import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from xgboost import XGBClassifier
import joblib

# Daten einlesen
df = pd.read_csv('titanic.csv')

# Features wählen: Pclass, Sex, Age, SibSp, Parch, Fare
df['Sex_enc'] = LabelEncoder().fit_transform(df['Sex'])

features = ['Pclass', 'Sex_enc', 'Age', 'SibSp', 'Parch', 'Fare']
df = df.dropna(subset=features)  # Optional: Zeilen mit fehlenden Werten entfernen

X = df[features]
y = df['Survived']

# Split
X_train, X_test, y_train, y_test = train_test_split(X, y, stratify=y, random_state=42)

# Skaliere numerische Werte
scaler = StandardScaler()
X_train[['Age', 'Fare']] = scaler.fit_transform(X_train[['Age', 'Fare']])
X_test[['Age', 'Fare']] = scaler.transform(X_test[['Age', 'Fare']])

# Trainiere XGBoost
model = XGBClassifier(eval_metric='logloss', n_jobs=2)
model.fit(X_train, y_train)

# Speichere Modell und Scaler
joblib.dump({'model': model, 'scaler': scaler}, 'titanic_model.pkl')
print("Model training finished. Saved as titanic_model.pkl")
