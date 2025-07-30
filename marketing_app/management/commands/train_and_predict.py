import os
import pandas as pd
import pickle
from django.conf import settings
from django.core.management.base import BaseCommand
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from xgboost import XGBClassifier


class Command(BaseCommand):
    help = "Train XGBoost model to predict payment status"

    def handle(self, *args, **kwargs):
        # Load dataset
        df = pd.read_csv("data/2022_encoded_data.csv",
                         on_bad_lines='skip', delimiter=';')

        # Check target column
        if 'ispaid' not in df.columns:
            self.stderr.write(self.style.ERROR(
                "❌ Column 'ispaid' not found in dataset"))
            self.stderr.write(f"🧪 Available columns: {df.columns.tolist()}")
            return

        y = df['ispaid']
        columns_to_drop = ['idregistrantdata',
                           'email', 'ispaid', 'paymentamount']
        X = df.drop(
            columns=[col for col in columns_to_drop if col in df.columns])

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)

        # Train model
        xgb = XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        xgb.fit(X_train, y_train)

        # Evaluate
        y_pred = xgb.predict(X_test)
        y_prob = xgb.predict_proba(X_test)[:, 1]

        accuracy = accuracy_score(y_test, y_pred) * 100
        roc_auc = roc_auc_score(y_test, y_prob)

        self.stdout.write("\n=== XGBoost Model Evaluation ===")
        self.stdout.write(f"Accuracy: {accuracy:.2f}%")
        self.stdout.write(f"ROC-AUC Score: {roc_auc:.4f}")
        self.stdout.write("Classification Report:")
        self.stdout.write(classification_report(
            y_test, y_pred, target_names=['Will Not Pay', 'Will Pay']))
        self.stdout.write("Confusion Matrix:")
        self.stdout.write(str(confusion_matrix(y_test, y_pred)))

        model_path = os.path.join('xgb_model.pkl')
        with open(model_path, "wb") as f:
            pickle.dump(xgb, f)

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Model saved to {model_path}"))
