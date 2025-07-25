from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages
import pandas as pd

from .forms import UploadCSVForm
from .models import RegistrationData


def start_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'start.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if user.is_superuser or user.is_staff:
                return redirect(reverse('admin:auth_user_changelist'))
            else:
                return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Incorrect username or password'})

    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    return render(request, 'dashboard.html', {'is_admin': is_admin})


@login_required
def prediction_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    return render(request, 'prediction.html', {'is_admin': is_admin})


@login_required
def visualization_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    return render(request, 'visualization.html', {'is_admin': is_admin})


@login_required
def dataset_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    return render(request, 'dataset.html', {'is_admin': is_admin})


@login_required
def upload_data_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff

    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = form.cleaned_data['file']
            try:
                # Baca CSV dan skip baris error
                df = pd.read_csv(csv_file, on_bad_lines='skip',
                                 delimiter=';', encoding='utf-8')

                # Cek apakah semua kolom penting ada
                required_columns = [
                    'idregistrantdata', 'groupreg', 'regtype',
                    'iddataregkhusustype', 'idschooltypedata', 'idschooljurusandata',
                    'email', 'idmajordata', 'idcountrydata', 'iddataprovinces',
                    'iddataregencies', 'ispaid', 'paymentamount'
                ]
                missing = [
                    col for col in required_columns if col not in df.columns]
                if missing:
                    raise ValueError(
                        f"Missing columns in CSV: {', '.join(missing)}")

                # Simpan ke database
                for _, row in df.iterrows():
                    RegistrationData.objects.create(
                        idregistrantdata=row['idregistrantdata'],
                        groupreg=row['groupreg'],
                        regtype=row['regtype'],
                        iddataregkhusustype=row['iddataregkhusustype'],
                        idschooltypedata=row['idschooltypedata'],
                        idschooljurusandata=row['idschooljurusandata'],
                        email=row['email'],
                        idmajordata=row['idmajordata'],
                        idcountrydata=row['idcountrydata'],
                        iddataprovinces=row['iddataprovinces'],
                        iddataregencies=row['iddataregencies'],
                        ispaid=row['ispaid'],
                        paymentamount=row['paymentamount']
                    )

                messages.success(
                    request, "File uploaded and data saved successfully.")
                return redirect('dataset')

            except Exception as e:
                messages.error(request, f"Error processing file: {str(e)}")
    else:
        form = UploadCSVForm()

    return render(request, 'upload_data.html', {'form': form, 'is_admin': is_admin})
