from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse


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
            return render(request, 'login.html', {'error': 'Username atau password salah'})

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
