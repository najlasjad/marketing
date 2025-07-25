from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import pandas as pd
from django.shortcuts import render
from .forms import UploadCSVForm
from .models import RegistrationData


def start_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'start.html')  # Tampilkan halaman start.html


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

    # sebelumnya 'login1.html', pastikan pakai 'login.html'
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
def upload_dataset(request):
    context = {}
    if request.method == 'POST':
        form = UploadCSVForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['file']
            try:
                df = pd.read_csv(csv_file)
                df.dropna(inplace=True)

                records = [
                    RegistrationData(
                        idregistrantdata=row['idregistrantdata'],
                        groupreg=row['groupreg'],
                        regtype=row['regtype'],
                        iddataregkhusustype=row['iddataregkhusustype'],
                        idschooltypedata=row['idschooltypedata'],
                        idschooljurusandata=row['idschooljurusandata'],
                        email=row['email'],
                        idmajordata=row['idmajordata'],
                        idcountrydata=row['idcountrydata'],
                        iddataprovences=row['iddataprovences'],
                        iddataregencies=row['iddataregencies'],
                        ispaid=row['ispaid'],
                        paymentamount=row['paymentamount'],
                        ump=row['ump'],
                    )
                    for _, row in df.iterrows()
                ]

                RegistrationData.objects.bulk_create(records)

                context = {
                    'form': form,
                    'success': True,
                    'rows': len(records)
                }
            except Exception as e:
                context = {
                    'form': form,
                    'error': str(e)
                }
        else:
            context = {'form': form}
    else:
        context = {'form': UploadCSVForm()}

    return render(request, 'dataset.html', context)
