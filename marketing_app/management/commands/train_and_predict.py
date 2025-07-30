import os
import pandas as pd
import pickle
from django.core.management.base import BaseCommand
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score, roc_auc_score
from xgboost import XGBClassifier


class Command(BaseCommand):
    help = 'Train model from one CSV and predict on another'

    def add_arguments(self, parser):
        parser.add_argument('--train_file', type=str, required=True,
                            help='Nama file training (di folder documents)')
        parser.add_argument('--predict_file', type=str, required=True,
                            help='Nama file untuk prediksi (di folder documents)')

    def handle(self, *args, **options):
        # Path ke folder documents/
        base_path = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), '../../../', 'documents')
        base_path = os.path.abspath(base_path)

        train_file = options['train_file']
        predict_file = options['predict_file']

        train_path = os.path.join(base_path, train_file)
        predict_path = os.path.join(base_path, predict_file)

        # 1. Load data training
        self.stdout.write(f"📥 Loading training data from: {train_path}")
        df_train = pd.read_csv(train_path)
        X_train = df_train.drop(
            columns=['idregistrantdata', 'email', 'ispaid', 'paymentamount'])
        y_train = df_train['ispaid']

        # 2. Train model
        scale_pos_weight = (len(y_train) - sum(y_train)) / sum(y_train)
        xgb = XGBClassifier(
            scale_pos_weight=scale_pos_weight,
            use_label_encoder=False,
            eval_metric='logloss',
            random_state=42
        )
        xgb.fit(X_train, y_train)
        self.stdout.write("✅ Model trained successfully")

        # 3. Load data prediksi
        self.stdout.write(f"🔎 Predicting using data from: {predict_path}")
        df_predict = pd.read_csv(predict_path)
        X_predict = df_predict.drop(
            columns=['idregistrantdata', 'email', 'ispaid', 'paymentamount'])

        y_prob = xgb.predict_proba(X_predict)[:, 1]
        predicted_payers = y_prob.sum()
        total_students = len(X_predict)

        self.stdout.write("\n=== Estimasi Pembayar ===")
        self.stdout.write(f"Total siswa di data prediksi: {total_students}")
        self.stdout.write(
            f"Perkiraan jumlah yang akan bayar: {predicted_payers:.0f}")

        # 4. Simpan hasil prediksi
        df_predict['predicted_proba_paid'] = y_prob
        output_file = os.path.join(base_path, "prediksi_output.csv")
        df_predict.to_csv(output_file, index=False)
        self.stdout.write(f"📄 Hasil prediksi disimpan ke: {output_file}")

        # 5. Simpan model
        model_path = os.path.join(base_path, "xgb_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump(xgb, f)
        self.stdout.write(f"✅ Model disimpan sebagai: {model_path}")
