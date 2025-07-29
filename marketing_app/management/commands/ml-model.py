import pandas as pd
import pickle
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from xgboost import XGBClassifier

# 1. Load the dataset
df = pd.read_csv("2022_encoded_data.csv")

# 2. Separate features (X) and target (y)
X = df.drop(columns=['idregistrantdata', 'email', 'ispaid', 'paymentamount'])
y = df['ispaid']

# 3. Split dataset into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 4. Handle class imbalance using scale_pos_weight
scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

# 5. Build the XGBoost model
xgb = XGBClassifier(
    scale_pos_weight=scale_pos_weight,
    use_label_encoder=False,
    eval_metric='logloss',
    random_state=42
)

# 6. Train the model
xgb.fit(X_train, y_train)

# 7. Evaluate the model
y_pred = xgb.predict(X_test)
y_prob = xgb.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred) * 100
roc_auc = roc_auc_score(y_test, y_prob)

print("=== XGBoost Model Evaluation ===")
print(f"Accuracy: {accuracy:.2f}%")
print(f"ROC-AUC Score: {roc_auc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred, target_names=['Will Not Pay', 'Will Pay']))
print("Confusion Matrix:")
print(confusion_matrix(y_test, y_pred))

# 8. Estimate total number of students likely to pay from the entire dataset
y_prob_all = xgb.predict_proba(X)[:, 1]
predicted_payers = y_prob_all.sum()
total_students = len(X)
actual_payers = y.sum()

print("\n=== Estimated Total Payers ===")
print(f"Total registered students: {total_students}")
print(f"Estimated number who will pay: {predicted_payers:.0f}")
print(f"Actual number who paid: {actual_payers}")

# 9. Save the trained model as a .pkl file
with open("xgb_model.pkl", "wb") as f:
    pickle.dump(xgb, f)

print("\n✅ Model has been saved as 'xgb_model.pkl'")
