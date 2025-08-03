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
import numpy as np
import plotly.express as px
import plotly.io as pio
import plotly.graph_objects as go
import json
import joblib
from django.conf import settings
from sklearn.preprocessing import LabelEncoder
import os
import geopandas as gpd


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
    documents = Document.objects.all().order_by('-uploaded_at')
    selected_id = request.GET.get('doc')
    payment_html = None

    ump_mapping = {
        0: 2725504, 11: 3166460, 12: 2522609, 13: 2512539, 14: 2938564,
        15: 2698940, 16: 3144446, 17: 2238094, 18: 2440486, 19: 3264884,
        21: 3050172, 31: 4641854, 32: 1841487, 33: 1812935, 34: 1840915,
        35: 1891567, 36: 2501203, 51: 2516971, 52: 2207212, 53: 1975000,
        61: 2434328, 62: 2922516, 63: 2906473, 64: 3014497, 65: 3016738,
        71: 3310723, 72: 2390739, 73: 3165876, 74: 2576016, 75: 2800580,
        76: 2678863, 81: 2619312, 82: 2862231, 91: 3200000, 94: 3561932,
    }

    if not selected_id and documents.exists():
        selected_id = str(documents.first().id)

    payment_html = None
    map_html = None
    total_registrants = 0
    student_paid = 0
    student_unpaid = 0
    growth_chart_html = None
    growth_data = []

    # Grafik Payment Pie Chart (per dokumen terpilih)
    if selected_id:
        doc = get_object_or_404(Document, pk=selected_id)

        try:
            df = pd.read_csv(doc.file.path, delimiter=';',
                             encoding='utf-8', low_memory=False)
        except Exception:
            df = pd.read_csv(doc.file.path)

        df['ump'] = df['iddataprovinces'].map(
            lambda x: ump_mapping.get(x, None))

        expected_cols = [
            'idregistrantdata', 'groupreg', 'regtype', 'iddataregkhusustype',
            'idschooltypedata', 'idschooljurusandata', 'email', 'idmajordata',
            'idcountrydata', 'iddataprovinces', 'iddataregencies',
            'ispaid', 'paymentamount', 'ump'
        ]
        available_cols = [col for col in expected_cols if col in df.columns]
        df = df[available_cols]

        if 'email' in df.columns and 'ispaid' in df.columns:
            df = df.sort_values(by='ispaid', ascending=False)
            df = df.drop_duplicates(subset='email', keep='first')

            total_registrants = len(df)
            student_paid = df[df['ispaid'] == 1].shape[0]
            student_unpaid = df[df['ispaid'] == 0].shape[0]

            payment_counts = df['ispaid'].value_counts().sort_index()
            labels = ['Not Yet Paid', 'Payment Completed']
            colors = ['rgb(165, 0, 38)', 'rgb(255, 160, 122)']

            fig1 = go.Figure(
                data=[go.Pie(
                    labels=labels,
                    values=payment_counts,
                    marker=dict(colors=colors),
                    textinfo='percent+label',
                    insidetextorientation='radial',
                    textfont=dict(size=14, color='black')
                )]
            )

            fig1.update_layout(
                title_text='Distribution of Students by Payment Status',
                title_font=dict(size=18, color='black'),
                showlegend=False
            )

            payment_html = pio.to_html(fig1, full_html=False)

            # ----------------------------
            # 🗺️ PETA PROVINSI DENGAN GEOPANDAS
            # ----------------------------
            province_counts = df['iddataprovinces'].value_counts().to_dict()

            geo_path = os.path.join(
                settings.BASE_DIR, 'marketing_app', 'static', 'geo', 'indonesia_provinces.geojson')
            print(f"[DEBUG] GeoJSON path: {geo_path}")
            print(f"[EXISTS?] {os.path.exists(geo_path)}")

            gdf = gpd.read_file(geo_path)

            # GUNAKAN CC_1 SEBAGAI ID PROVINSI
            gdf['prov_id'] = gdf['CC_1'].astype(int)
            gdf['registrants'] = gdf['prov_id'].map(
                province_counts).fillna(0).astype(int)

            fig_map = px.choropleth_mapbox(
                gdf,
                geojson=json.loads(gdf.to_json()),
                locations=gdf.index,
                color="registrants",
                color_continuous_scale="YlOrRd",
                mapbox_style="carto-positron",
                center={"lat": -2.5, "lon": 118},
                zoom=4.2,
                hover_name="NAME_1",
                hover_data={"registrants": True},
                opacity=0.6
            )

            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=600,
                width=1000
            )

            map_html = pio.to_html(fig_map, full_html=False)

    # Statistik pertumbuhan
    yearly_stats = {}
    for doc in documents:
        try:
            df = pd.read_csv(doc.file.path, delimiter=';',
                             encoding='utf-8', low_memory=False)
        except Exception:
            df = pd.read_csv(doc.file.path)

        if 'email' in df.columns:
            df = df.drop_duplicates(subset='email', keep='first')
            registrants = df.shape[0]
            paid = df[df['ispaid'] ==
                      1].shape[0] if 'ispaid' in df.columns else 0

            yearly_stats[doc.name] = {
                "registrants": registrants,
                "paid": paid
            }

    sorted_years = sorted(yearly_stats.keys())

    for i in range(1, len(sorted_years)):
        prev = yearly_stats[sorted_years[i - 1]]
        curr = yearly_stats[sorted_years[i]]

        reg_growth = (
            (curr['registrants'] - prev['registrants']) / prev['registrants']) * 100
        paid_growth = ((curr['paid'] - prev['paid']) / prev['paid']) * 100

        growth_data.append({
            "year": sorted_years[i],
            "registrants_growth": round(reg_growth, 2),
            "paid_growth": round(paid_growth, 2)
        })

    if yearly_stats:
        years = sorted_years
        registrants = [yearly_stats[y]['registrants'] for y in years]
        paid = [yearly_stats[y]['paid'] for y in years]

        fig_growth = go.Figure()
        fig_growth.add_trace(go.Scatter(
            x=years,
            y=registrants,
            mode='lines+markers',
            name='Total Registrants',
            line=dict(color='rgba(100, 149, 237, 0.8)', width=3),
            marker=dict(size=6)
        ))

        fig_growth.add_trace(go.Scatter(
            x=years,
            y=paid,
            mode='lines+markers',
            name='Paid Students',
            line=dict(color='rgba(220, 20, 60, 0.8)', width=3),
            marker=dict(size=6)
        ))

        fig_growth.update_layout(
            title='Yearly Growth: Registrants and Paid Students',
            xaxis_title='Year',
            yaxis_title='Count',
            template='simple_white',
            legend=dict(orientation="h", y=1.1),
            margin=dict(l=40, r=40, t=60, b=40)
        )

        growth_chart_html = pio.to_html(fig_growth, full_html=False)

    return render(request, 'dashboard.html', {
        'documents': documents,
        'selected_id': selected_id,
        'payment_html': payment_html,
        'map_html': map_html,
        'total_registrants': total_registrants,
        'student_paid': student_paid,
        'student_unpaid': student_unpaid,
        'growth_chart_html': growth_chart_html,
        'growth_data': growth_data,
    })


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
    documents = Document.objects.all().order_by('-uploaded_at')
    test_doc = documents.filter(name__icontains='2023').first()

    prediction_results = None
    selected_idregistrantdata = request.POST.get(
        'idregistrantdata') if request.method == 'POST' else None
    selected_student_data = None
    student_options = []
    test_df = None

    selected_columns = [
        'idregistrantdata',
        'groupreg',
        'regtype',
        'iddataregkhusustype',
        'idschooltypedata',
        'idschooljurusandata',
        'email',
        'idmajordata',
        'idcountrydata',
        'iddataprovinces',
        'iddataregencies',
        'paymentamount',
        'ispaid',
    ]

    ump_mapping = {
        0: 2725504, 11: 3166460, 12: 2522609, 13: 2512539, 14: 2938564, 15: 2698940,
        16: 3144446, 17: 2238094, 18: 2440486, 19: 3264884, 21: 3050172, 31: 4641854,
        32: 1841487, 33: 1812935, 34: 1840915, 35: 1891567, 36: 2501203, 51: 2516971,
        52: 2207212, 53: 1975000, 61: 2434328, 62: 2922516, 63: 2906473, 64: 3014497,
        65: 3016738, 71: 3310723, 72: 2390739, 73: 3165876, 74: 2576016, 75: 2800580,
        76: 2678863, 81: 2619312, 82: 2862231, 91: 3200000, 94: 3561932,
    }

    if test_doc:
        try:
            test_df = pd.read_csv(test_doc.file.path,
                                  delimiter=';', encoding='utf-8')
        except Exception:
            test_df = pd.read_csv(test_doc.file.path)

        if 'idregistrantdata' in test_df.columns:
            test_df = test_df.dropna(subset=['idregistrantdata'])
            test_df = test_df.drop_duplicates(
                subset='idregistrantdata', keep='first')
            if 'email' not in test_df.columns:
                test_df['email'] = ''
            test_df = test_df[selected_columns]
            student_options = test_df[[
                'idregistrantdata', 'email']].to_dict('records')

    if selected_idregistrantdata and test_df is not None:
        student_row = test_df[test_df['idregistrantdata'].astype(
            str) == str(selected_idregistrantdata)]

        if not student_row.empty:
            selected_student_data = student_row.iloc[0].to_dict()

            # Mapping UMP
            student_row['ump'] = student_row['iddataprovinces'].map(
                ump_mapping)
            selected_student_data['ump'] = int(student_row['ump'].values[0]) if not pd.isna(
                student_row['ump'].values[0]) else None

            if request.method == 'POST':
                model_path = os.path.join(settings.BASE_DIR, 'xgb_model.pkl')
                feature_path = os.path.join(
                    settings.BASE_DIR, 'xgb_model_features.pkl')

                if os.path.exists(model_path) and os.path.exists(feature_path):
                    model = joblib.load(model_path)
                    model_features = joblib.load(feature_path)

                    feature_cols = [
                        'groupreg', 'regtype', 'iddataregkhusustype',
                        'idschooltypedata', 'idschooljurusandata',
                        'idmajordata', 'idcountrydata', 'iddataprovinces',
                        'iddataregencies', 'paymentamount', 'ump'
                    ]

                    try:
                        df_pred = student_row.copy()
                        df_pred = df_pred[feature_cols]

                        # Encoding
                        categorical_cols = [col for col in df_pred.columns if df_pred[col].nunique(
                        ) < 15 and df_pred[col].dtype in ['int64', 'object']]
                        ordinal_cols = [
                            col for col in categorical_cols if df_pred[col].dtype != 'object']
                        nominal_cols = [
                            col for col in categorical_cols if df_pred[col].dtype == 'object']

                        for col in ordinal_cols:
                            le = LabelEncoder()
                            df_pred[col] = le.fit_transform(df_pred[col])

                        df_pred = pd.get_dummies(df_pred, columns=nominal_cols)

                        # ✅ Align to model's expected columns
                        df_pred = df_pred.reindex(
                            columns=model_features, fill_value=0)

                        prediction = model.predict(df_pred)[0]
                        proba = model.predict_proba(df_pred)[0]

                        prediction_results = {
                            'status': 'Paid' if prediction == 1 else 'Not Paid',
                            'probability_paid': round(proba[1] * 100, 2),
                            'probability_unpaid': round(proba[0] * 100, 2),
                        }
                    except Exception as e:
                        prediction_results = {
                            'error': f'Prediction error: {str(e)}'
                        }
                else:
                    prediction_results = {
                        'error': 'Model or feature structure file not found.'}

    return render(request, 'prediction.html', {
        'is_admin': is_admin,
        'student_options': student_options,
        'prediction_results': prediction_results,
        'selected_student_data': selected_student_data,
        'selected_idregistrantdata': selected_idregistrantdata
    })


@login_required
def visualization_view(request):
    documents = Document.objects.all().order_by('-uploaded_at')
    selected_id = request.GET.get('doc')
    regtype_html = None
    schooltype_html = None
    province_html = None
    payment_html = None
    ump_html = None
    map_html = None

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

    schooltype_mapping = {
        1: "SMA",
        2: "SMK",
        3: "MA",
        9: "Lainnya"
    }

    ump_mapping = {
        0: 2725504,
        11: 3166460,
        12: 2522609,
        13: 2512539,
        14: 2938564,
        15: 2698940,
        16: 3144446,
        17: 2238094,
        18: 2440486,
        19: 3264884,
        21: 3050172,
        31: 4641854,
        32: 1841487,
        33: 1812935,
        34: 1840915,
        35: 1891567,
        36: 2501203,
        51: 2516971,
        52: 2207212,
        53: 1975000,
        61: 2434328,
        62: 2922516,
        63: 2906473,
        64: 3014497,
        65: 3016738,
        71: 3310723,
        72: 2390739,
        73: 3165876,
        74: 2576016,
        75: 2800580,
        76: 2678863,
        81: 2619312,
        82: 2862231,
        91: 3200000,
        94: 3561932,
    }

    if selected_id:
        doc = get_object_or_404(Document, pk=selected_id)

        try:
            df = pd.read_csv(doc.file.path, delimiter=';',
                             encoding='utf-8', low_memory=False)
        except Exception:
            df = pd.read_csv(doc.file.path)

        df['ump'] = df['iddataprovinces'].map(ump_mapping)
        expected_cols = [
            'idregistrantdata', 'groupreg', 'regtype',
            'iddataregkhusustype', 'idschooltypedata',
            'idschooljurusandata', 'email', 'idmajordata',
            'idcountrydata', 'iddataprovinces',
            'iddataregencies', 'ispaid', 'paymentamount', 'ump'
        ]

        available_cols = [col for col in expected_cols if col in df.columns]
        df = df[available_cols]

        if 'email' in df.columns and 'ispaid' in df.columns:
            df = df.sort_values(by='ispaid', ascending=False)
            df = df.drop_duplicates(subset='email', keep='first')

            # 🎯 Chart 1: Registrasi (with custom blue gradient)
            if 'regtype' in df.columns:
                df['regtype'] = pd.to_numeric(df['regtype'], errors='coerce')
                df = df.dropna(subset=['regtype'])
                df['regtype'] = df['regtype'].astype(int)
                df = df[df['regtype'].isin(regtype_mapping.keys())]

                # Mapping regtype
                df['regtype_name'] = df['regtype'].map(regtype_mapping)

                if not df['regtype_name'].isna().all():
                    # Count and sort registration types
                    regtype_counts = df['regtype_name'].value_counts(
                    ).reset_index()
                    regtype_counts.columns = ['regtype_name', 'count']
                    regtype_counts = regtype_counts.sort_values(
                        'count', ascending=False).reset_index(drop=True)

                    # Custom blue gradient colors
                    colors = [
                        'rgb(8,48,107)', 'rgb(23,80,141)', 'rgb(38,112,175)',
                        'rgb(66,146,198)', 'rgb(107,174,214)', 'rgb(158,202,225)',
                        'rgb(198,219,239)', 'rgb(222,235,247)', 'rgb(239,243,255)',
                        'rgb(222,235,247)', 'rgb(198,219,239)', 'rgb(158,202,225)',
                        'rgb(107,174,214)', 'rgb(66,146,198)', 'rgb(38,112,175)'
                    ]
                    colors = colors[:len(regtype_counts)]

                    # Create the bar chart
                    fig = px.bar(
                        regtype_counts,
                        x='regtype_name',
                        y='count',
                        title='Registration Type Distribution',
                        text_auto=True
                    )

                    # Apply manual colors
                    fig.update_traces(marker_color=colors)

                    # Layout styling
                    fig.update_layout(
                        xaxis_title='Registration Type',
                        yaxis_title='Total Students',
                        title_font=dict(size=20, color='darkblue'),
                        xaxis_tickangle=-30,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        showlegend=False,
                        margin=dict(t=50, b=100)
                    )

                    fig.update_traces(
                        hovertemplate='<b>%{x}</b><br>Jumlah Siswa: %{y}<extra></extra>'
                    )

                    # Convert to HTML for rendering
                    regtype_html = pio.to_html(fig, full_html=False)

            # 🏫 Chart 2: Tipe Sekolah
            if 'idschooltypedata' in df.columns:
                df['idschooltypedata'] = pd.to_numeric(
                    df['idschooltypedata'], errors='coerce')
                df = df.dropna(subset=['idschooltypedata'])
                df['idschooltypedata'] = df['idschooltypedata'].astype(int)
                df['schooltype_name'] = df['idschooltypedata'].map(
                    schooltype_mapping)

                if not df['schooltype_name'].isna().all():
                    schooltype_counts = df['schooltype_name'].value_counts(
                    ).reset_index()
                    schooltype_counts.columns = ['schooltype_name', 'count']
                    schooltype_counts = schooltype_counts.sort_values(
                        'count', ascending=False).reset_index(drop=True)

                    # Define custom red gradient colors
                    colors = [
                        "#8B0000", "#B22222", "#CD5C5C",
                        "#F08080", "#FA8072", "#FFA07A",
                    ]
                    colors = colors[:len(schooltype_counts)]

                    # Create Plotly bar chart
                    fig2 = px.bar(
                        schooltype_counts,
                        x='schooltype_name',
                        y='count',
                        text_auto=True
                    )

                    fig2.update_traces(marker_color=colors)

                    # Layout styling
                    fig2.update_layout(
                        title='Distribution of School Types',
                        xaxis_title='School Type',
                        yaxis_title='Total Students',
                        title_font=dict(size=18, color='black'),
                        xaxis_tickangle=0,
                        plot_bgcolor='white',
                        paper_bgcolor='white',
                        showlegend=False
                    )

                    fig2.update_traces(
                        hovertemplate='<b>%{x}</b><br>Jumlah Siswa: %{y}<extra></extra>'
                    )

                    # Convert to HTML
                    schooltype_html = pio.to_html(fig2, full_html=False)

            if 'iddataprovinces' in df.columns:
                df['iddataprovinces'] = pd.to_numeric(
                    df['iddataprovinces'], errors='coerce')
                df = df.dropna(subset=['iddataprovinces'])

                # --- Mapping ID → Nama Provinsi
                province_mapping = {
                    0: "Unknown", 11: "Aceh", 12: "Sumatera Utara", 13: "Sumatera Barat",
                    14: "Riau", 15: "Jambi", 16: "Sumatera Selatan", 17: "Bengkulu", 18: "Lampung",
                    19: "Kepulauan Bangka Belitung", 21: "Kepulauan Riau", 31: "DKI Jakarta",
                    32: "Jawa Barat", 33: "Jawa Tengah", 34: "DI Yogyakarta", 35: "Jawa Timur",
                    36: "Banten", 51: "Bali", 52: "Nusa Tenggara Barat", 53: "Nusa Tenggara Timur",
                    61: "Kalimantan Barat", 62: "Kalimantan Tengah", 63: "Kalimantan Selatan",
                    64: "Kalimantan Timur", 65: "Kalimantan Utara", 71: "Sulawesi Utara",
                    72: "Sulawesi Tengah", 73: "Sulawesi Selatan", 74: "Sulawesi Tenggara",
                    75: "Gorontalo", 76: "Sulawesi Barat", 81: "Maluku", 82: "Maluku Utara",
                    91: "Papua Barat", 94: "Papua"
                }

                # Tambah nama provinsi
                df['province_name'] = df['iddataprovinces'].astype(
                    int).map(province_mapping)

                # Hitung dan urutkan
                province_counts = (
                    df['province_name'].value_counts()
                    .rename_axis('province_name')
                    .reset_index(name='jumlah_pendaftar')
                    .sort_values('jumlah_pendaftar', ascending=False)
                    .reset_index(drop=True)
                )

                # Grup warna
                k = 5
                province_counts['rank'] = np.arange(
                    len(province_counts))  # 0 = paling tinggi
                province_counts['group'] = (
                    province_counts['rank'] * k / len(province_counts)).astype(int)
                province_counts.loc[province_counts['group']
                                    >= k, 'group'] = k-1

                # Warna gradasi biru (5 kelompok)
                palette = px.colors.sequential.Blues[-5:][::-1]
                group_to_color = {i: palette[i] for i in range(k)}
                province_counts['color'] = province_counts['group'].map(
                    group_to_color)

                # Map warna final
                color_map = dict(
                    zip(province_counts['province_name'], province_counts['color']))

                # Plot
                fig3 = px.bar(
                    province_counts,
                    x='province_name',
                    y='jumlah_pendaftar',
                    title='Distribution of Applicants per Province',
                    text='jumlah_pendaftar',
                    color='province_name',
                    color_discrete_map=color_map
                )

                fig3.update_layout(
                    xaxis_title='Provinces',
                    yaxis_title='Total Applicants',
                    xaxis_tickangle=-90,
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )

                province_html = pio.to_html(fig3, full_html=False)

            if 'ispaid' in df.columns:
                payment_counts = df['ispaid'].value_counts().sort_index()
                labels = ['Not Yet Paid', 'Payment Completed']
                colors = ['rgb(165, 0, 38)', 'rgb(255, 160, 122)']

                fig4 = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=payment_counts,
                            marker=dict(colors=colors),
                            textinfo='percent+label',
                            insidetextorientation='radial',
                            textfont=dict(size=14, color='black')
                        )
                    ]
                )

                fig4.update_layout(
                    title_text='Distribution of Students by Payment Status',
                    title_font=dict(size=18, color='black'),
                    showlegend=False
                )

                payment_html = pio.to_html(fig4, full_html=False)

            if 'iddataprovinces' in df.columns and 'ump' in df.columns:
                # Province mapping
                province_mapping = {
                    0: "Unknown", 11: "Aceh", 12: "Sumatera Utara", 13: "Sumatera Barat",
                    14: "Riau", 15: "Jambi", 16: "Sumatera Selatan", 17: "Bengkulu", 18: "Lampung",
                    19: "Kepulauan Bangka Belitung", 21: "Kepulauan Riau", 31: "DKI Jakarta",
                    32: "Jawa Barat", 33: "Jawa Tengah", 34: "DI Yogyakarta", 35: "Jawa Timur",
                    36: "Banten", 51: "Bali", 52: "Nusa Tenggara Barat", 53: "Nusa Tenggara Timur",
                    61: "Kalimantan Barat", 62: "Kalimantan Tengah", 63: "Kalimantan Selatan",
                    64: "Kalimantan Timur", 65: "Kalimantan Utara", 71: "Sulawesi Utara",
                    72: "Sulawesi Tengah", 73: "Sulawesi Selatan", 74: "Sulawesi Tenggara",
                    75: "Gorontalo", 76: "Sulawesi Barat", 81: "Maluku", 82: "Maluku Utara",
                    91: "Papua Barat", 94: "Papua"
                }

                df['province_name'] = df['iddataprovinces'].map(
                    province_mapping)

                df = df[df['ump'] < 100_000_000]

                ump_per_province = (
                    df.groupby('province_name')['ump']
                    .mean()
                    .dropna()
                    .sort_values()
                )

                ump_sorted = ump_per_province.sort_values(ascending=False)

                blue_group_colors = px.colors.sequential.Blues[2:7][::-1]
                n = len(ump_sorted)
                group_size = int(np.ceil(n / 5))

                color_list = []
                for i in range(n):
                    group_idx = min(i // group_size, 4)
                    color_list.append(blue_group_colors[group_idx])

                fig = go.Figure(
                    go.Bar(
                        x=ump_sorted.values[::-1],
                        y=ump_sorted.index[::-1],
                        orientation='h',
                        marker=dict(color=color_list[::-1]),
                        text=[
                            f"Rp {int(x):,}".replace(",", ".")
                            for x in ump_sorted.values[::-1]
                        ],
                        textposition='outside',
                        hovertemplate='%{y}<br>UMP: Rp %{x:,.0f}<extra></extra>'
                    )
                )

                fig.update_layout(
                    title='2022 UMP per Province (Highest to Lowest)',
                    xaxis_title='UMP Nominal (Rp)',
                    yaxis_title='Provinces',
                    title_font=dict(size=18, color='black'),
                    xaxis_tickformat=',.0f',
                    margin=dict(l=80, r=50, t=80, b=50),
                    height=850,
                    showlegend=False
                )

                ump_html = pio.to_html(fig, full_html=False)

            # ----------------------------
            # 🗺️ PETA PROVINSI DENGAN GEOPANDAS
            # ----------------------------
            province_counts = df['iddataprovinces'].value_counts().to_dict()

            geo_path = os.path.join(
                settings.BASE_DIR, 'marketing_app', 'static', 'geo', 'indonesia_provinces.geojson')
            print(f"[DEBUG] GeoJSON path: {geo_path}")
            print(f"[EXISTS?] {os.path.exists(geo_path)}")

            gdf = gpd.read_file(geo_path)

            # GUNAKAN CC_1 SEBAGAI ID PROVINSI
            gdf['prov_id'] = gdf['CC_1'].astype(int)
            gdf['registrants'] = gdf['prov_id'].map(
                province_counts).fillna(0).astype(int)

            fig_map = px.choropleth_mapbox(
                gdf,
                geojson=json.loads(gdf.to_json()),
                locations=gdf.index,
                color="registrants",
                color_continuous_scale="YlOrRd",
                mapbox_style="carto-positron",
                center={"lat": -2.5, "lon": 118},
                zoom=4.2,
                hover_name="NAME_1",
                hover_data={"registrants": True},
                opacity=0.6
            )

            fig_map.update_layout(
                margin={"r": 0, "t": 0, "l": 0, "b": 0},
                height=600,
                width=1000
            )

            map_html = pio.to_html(fig_map, full_html=False)

    return render(request, 'visualization.html', {
        'documents': documents,
        'selected_id': selected_id,
        'regtype_html': regtype_html,
        'regtype_mapping': regtype_mapping,
        'schooltype_html': schooltype_html,
        'province_html': province_html,
        'payment_html': payment_html,
        'ump_html': ump_html,
        'map_html': map_html
    })
