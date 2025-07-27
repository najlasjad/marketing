from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .forms import DocumentForm
from .models import Document

from django.core.serializers.json import DjangoJSONEncoder
import json


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
@login_required
def dataset_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff

    datasets = Document.objects.all().order_by('-uploaded_at')

    dataset_data = []
    for d in datasets:
        dataset_data.append({
            "id": d.id,
            "name": d.name,
            "type": d.file_type or 'unknown',
            "size": d.file_size,
            "records": d.total_rows,
            "created": d.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            "status": "active",  # optional: you can make this dynamic later
        })

    dataset_json = json.dumps(dataset_data, cls=DjangoJSONEncoder)

    return render(request, 'dataset.html', {
        'datasets': dataset_json,
        'is_admin': is_admin
    })


@login_required
def upload_file(request):
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            # define a success page or render success message
            return render(request, 'dataset.html', {'form': form})
    else:
        form = DocumentForm()
    return render(request, 'upload_data.html', {'form': form})


# @login_required
# def dataset_list(request):
#     datasets = Document.object.all()
#     return render(request, 'dataset.html', {'datasets': datasets})
