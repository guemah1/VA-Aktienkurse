import os
import pandas as pd
from zipfile import ZipFile
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import dash_daq as daq

# Pfade zu den ZIP-Ordnern
covid_zip_folder_path = r'C:\Users\mguen\OneDrive\Desktop\VA Projekt Kurse\Data_Covid.zip'
stocks_zip_folder_path = r'C:\Users\mguen\OneDrive\Desktop\VA Projekt Kurse\Data_stocks.zip'

covid_data = None
stocks_data = {}

# Lade der Daten aus den ZIP-Ordnern Anpassung der Spalten
with ZipFile(covid_zip_folder_path, 'r') as covid_zip_file:
    covid_zip_file_names = covid_zip_file.namelist()
    for file_name in covid_zip_file_names:
        if file_name.endswith(".csv"):
            with covid_zip_file.open(file_name) as csv_file:
                covid_data = pd.read_csv(csv_file)
                covid_data = covid_data.rename(columns={'date': 'Date', 'total_cases': 'total_cases'})

with ZipFile(stocks_zip_folder_path, 'r') as stocks_zip_file:
    stocks_zip_file_names = stocks_zip_file.namelist()
    for file_name in stocks_zip_file_names:
        if file_name.endswith(".csv"):
            with stocks_zip_file.open(file_name) as csv_file:
                stock_data = pd.read_csv(csv_file)
                stock_data = stock_data.rename(columns={'Date': 'Date', 'Close': 'Close', 'Volume': 'Volume'})
                stocks_data[file_name] = stock_data

# Erstellung der Dash-App
app = dash.Dash(__name__)

# Dropdown-Menü zur Auswahl der zu vergleichenden Aktien
stocks_options = [{'label': file_name, 'value': file_name} for file_name in stocks_zip_file_names]

# Finde den Gesamtzeitraum der Daten
start_date = min(covid_data['Date'])
end_date = max(covid_data['Date'])

# Layout der App
app.layout = html.Div([
    html.H1("Visual Analytics Dashboard"),
    dcc.Dropdown(
        id='stocks-dropdown',
        options=stocks_options,
        multi=True,
        value=[]
    ),
    dcc.Graph(id='covid-time-series-plot'),
    dcc.Graph(id='stocks-time-series-plot'),
    dcc.DatePickerRange(
        id='date-range',
        start_date=start_date,
        end_date=end_date,
        display_format='YYYY-MM-DD',
    ),
    dcc.Graph(id='small-multiples'),
    dcc.Graph(id='bar-chart'),
    dcc.Graph(id='pie-chart'),
    dcc.Graph(id='scatter-plot'),  # Scatterplot für Linked Views
    dcc.Graph(id='parallel-coordinates-plot')  # Parallele-Koordinaten-Diagramm
])

# Funktion zum Erstellen von Small Multiples
def create_small_multiples(selected_files, start_date, end_date):
    if not selected_files:
        return go.Figure()

    # Erstellen einer Subplot-Matrix für die Sparkline-Diagramme
    rows = len(selected_files)
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.02)

    for i, file_name in enumerate(selected_files):
        stock_data = stocks_data[file_name]
        stock_data_filtered = stock_data[(stock_data['Date'] >= start_date) & (stock_data['Date'] <= end_date)]
        fig.add_trace(go.Scatter(x=stock_data_filtered['Date'], y=stock_data_filtered['Close'], mode='lines',
                                 name=f'Stock {file_name} Close'), row=i + 1, col=1)

    fig.update_layout(title="Small Multiples - Kursentwicklung", height=300 * rows)
    return fig

# Funktion zum Erstellen eines Balkendiagramms
def create_bar_chart(selected_files):
    if not selected_files:
        return go.Figure()

    data = []
    for file_name in selected_files:
        stock_data = stocks_data[file_name]
        data.append(go.Bar(x=stock_data['Date'], y=stock_data['Close'], name=f'Stock {file_name} Close'))

    layout = go.Layout(barmode='stack', title="Balkendiagramm - Aktienkurse")
    return go.Figure(data=data, layout=layout)

# Funktion zum Erstellen eines Kuchendiagramms
def create_pie_chart(selected_file):
    if not selected_file:
        return go.Figure()

    stock_data = stocks_data[selected_file]
    pie_data = stock_data['Close']
    labels = stock_data['Date']

    data = [go.Pie(labels=labels, values=pie_data, title=f'Kuchendiagramm - {selected_file}')]
    return go.Figure(data=data)

# Funktion zum Erstellen einer Scatterplot-Matrix
def create_scatter_matrix(selected_files):
    if not selected_files:
        return go.Figure()

    data = []

    for file_name in selected_files:
        stock_data = stocks_data[file_name]
        scatter_matrix = pd.plotting.scatter_matrix(stock_data, diagonal='hist', markersize=5)
        scatter_matrix[0][0].update(showgrid=False, title=f'{file_name} Close')
        scatter_matrix[1][1].update(showgrid=False, title=f'{file_name} Volume')
        data.append(go.Scatter(x=[], y=[]))  # Leerer Scatterplot für Abstand

    layout = go.Layout(title="Scatterplot Matrix")
    return go.Figure(data=data, layout=layout)

# Callbacks für interaktive Elemente
@app.callback(
    Output('covid-time-series-plot', 'figure'),
    Output('stocks-time-series-plot', 'figure'),
    Output('small-multiples', 'figure'),
    Output('bar-chart', 'figure'),
    Output('pie-chart', 'figure'),
    Output('scatter-plot', 'figure'),
    Output('parallel-coordinates-plot', 'figure'),
    Input('stocks-dropdown', 'value'),
    Input('date-range', 'start_date'),
    Input('date-range', 'end_date'),
    State('stocks-dropdown', 'value')
)
def update_plots(selected_files, start_date, end_date, selected_files_state):
    if not selected_files:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="Wähle Dateien aus")
        return (
            empty_fig, empty_fig, create_small_multiples([], start_date, end_date),
            create_bar_chart([]), create_pie_chart([]), create_scatter_matrix([]), go.Figure()
        )

    selected_stocks_data = [stocks_data[file_name] for file_name in selected_files]
    covid_data_filtered = covid_data[(covid_data['Date'] >= start_date) & (covid_data['Date'] <= end_date)]
    selected_stocks_data_filtered = [stock_data[(stock_data['Date'] >= start_date) & (stock_data['Date'] <= end_date)]
                                     for stock_data in selected_stocks_data]
    covid_time_series_fig = go.Figure(
        data=[go.Scatter(x=covid_data_filtered['Date'], y=covid_data_filtered['total_cases'], name='Total COVID Cases')
    ])
    stocks_time_series_fig = go.Figure()

    for stock_data, file_name in zip(selected_stocks_data_filtered, selected_files):
        stocks_time_series_fig.add_trace(
            go.Scatter(x=stock_data['Date'], y=stock_data['Close'], name=f'Stock {file_name} Close'))

    small_multiples_fig = create_small_multiples(selected_files, start_date, end_date)
    bar_chart_fig = create_bar_chart(selected_files[0])  # Nur das erste ausgewählte Diagramm für das Balkendiagramm
    pie_chart_fig = create_pie_chart(selected_files[0])  # Nur das erste ausgewählte Diagramm für das Kuchendiagramm

    covid_time_series_fig.update_layout(title="Zeitreihe der COVID-Fälle")
    stocks_time_series_fig.update_layout(title="Zeitreihe der Aktienkurse")

    # Scatterplot für Linked Views aktualisieren
    scatter_fig = create_scatter_matrix(selected_files)

    # Parallele-Koordinaten-Diagramm aktualisieren
    parallel_fig = go.Figure()

    if selected_files_state:
        selected_stocks_data_state = [stocks_data[file_name] for file_name in selected_files_state]

        for stock_data_state in selected_stocks_data_state:
            parallel_fig.add_trace(go.Scatter(x=stock_data_state['Date'], y=stock_data_state['Close'],
                                              mode='lines', name=f'Aktienkurs'))

    parallel_fig.update_layout(title="Parallele-Koordinaten-Diagramm")

    return covid_time_series_fig, stocks_time_series_fig, small_multiples_fig, bar_chart_fig, pie_chart_fig, scatter_fig, parallel_fig

if __name__ == '__main__':
    app.run_server(debug=True)
