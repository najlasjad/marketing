from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .forms import DocumentForm
from .models import Document
from django.core.serializers.json import DjangoJSONEncoder
import json
from django.shortcuts import get_object_or_404
from django.http import FileResponse

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.io as pio


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


@login_required
def view_dataset(request, id):
    document = get_object_or_404(Document, pk=id)

    # Buka file dan kembalikan sebagai FileResponse untuk download
    if document.file:
        response = FileResponse(document.file.open('rb'), as_attachment=True)
        response[
            'Content-Disposition'] = f'attachment; filename="{document.file.name.split("/")[-1]}"'
        return response
    else:
        from django.http import HttpResponseNotFound
        return HttpResponseNotFound("File not found.")


@login_required
def edit_dataset(request, id):
    dataset = get_object_or_404(Document, id=id)
    if request.method == 'POST':
        form = DocumentForm(request.POST, request.FILES, instance=dataset)
        if form.is_valid():
            form.save()
            return redirect('dataset')
    else:
        form = DocumentForm(instance=dataset)
    return render(request, 'upload_data.html', {'form': form, 'edit': True})


@login_required
def delete_dataset(request, id):
    dataset = get_object_or_404(Document, id=id)
    if request.method == 'POST':
        dataset.delete()
        return redirect('dataset')
    return render(request, 'confirm_delete.html', {'dataset': dataset})


@login_required
def prediction_view(request):
    is_admin = request.user.is_superuser or request.user.is_staff
    return render(request, 'prediction.html', {'is_admin': is_admin})


@login_required
def visualization_view(request):
    documents = Document.objects.all().order_by('-uploaded_at')
    selected_id = request.GET.get('doc')
    regtype_html = None

    regtype_mapping = {
        0: "Unknown",
        1: "Test Event (City)",
        2: "Jalur 1 - Test",
        3: "Jalur 2 - Rapor",
        4: "Jalur 3 - Prestasi",
        5: "S1 Malam",
        6: "S1 Weekend",
        7: "S2 Graduate",
        8: "International - ASEAN",
        9: "International - China",
        10: "Social Culture",
        11: "Short Term",
        12: "Research",
        13: "Internship",
        14: "Special Assignment",
        15: "Jalur 4 - Online",
        16: "Jalur 5 - UTBK",
        17: "Jalur 6 - Blended",
        18: "Fast Track",
        19: "Jalur 7 - UNBK",
        20: "Jalur 8 - Khusus"
    }

    if selected_id:
        doc = get_object_or_404(Document, pk=selected_id)

        try:
            df = pd.read_csv(doc.file.path, delimiter=';',
                             encoding='utf-8', low_memory=False)
        except Exception:
            df = pd.read_csv(doc.file.path)

        expected_cols = [
            'idregistrantdata', 'groupreg', 'regtype',
            'iddataregkhusustype', 'idschooltypedata',
            'idschooljurusandata', 'email', 'idmajordata',
            'idcountrydata', 'iddataprovinces',
            'iddataregencies', 'ispaid', 'paymentamount'
        ]

        available_cols = [col for col in expected_cols if col in df.columns]
        df = df[available_cols]

        if 'email' in df.columns and 'ispaid' in df.columns:
            df = df.sort_values(by='ispaid', ascending=False)
            df = df.drop_duplicates(subset='email', keep='first')

            if 'regtype' in df.columns:
                df['regtype'] = pd.to_numeric(df['regtype'], errors='coerce')
                df = df.dropna(subset=['regtype'])
                df['regtype'] = df['regtype'].astype(int)
                df = df[df['regtype'].isin(regtype_mapping.keys())]
                df['regtype_name'] = df['regtype'].map(regtype_mapping)

                if not df['regtype_name'].isna().all():
                    # 🎯 Plotly Bar Chart
                    count_df = df['regtype_name'].value_counts().reset_index()
                    count_df.columns = ['Registration Type', 'Total Students']

                    fig = px.bar(
                        count_df,
                        x='Registration Type',
                        y='Total Students',
                        color='Registration Type',
                        title='Registration Type Distribution',
                        template='plotly_white'
                    )
                    fig.update_layout(
                        xaxis_tickangle=-45,
                        title_font_size=20,
                        xaxis_title='',
                        yaxis_title='Total Students',
                        showlegend=False,
                        margin=dict(t=50, b=100)
                    )

                    fig.update_traces(
                        hovertemplate='<b>%{x}</b><br>Total Students=%{y:,.0f}<extra></extra>'
                    )

                    # Convert to HTML
                    regtype_html = pio.to_html(fig, full_html=False)

    return render(request, 'visualization.html', {
        'documents': documents,
        'selected_id': selected_id,
        'regtype_html': regtype_html,
        'regtype_mapping': regtype_mapping,
    })
