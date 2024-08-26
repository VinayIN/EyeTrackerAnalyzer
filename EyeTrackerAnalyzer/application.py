import sys
import os
import re
import asyncio
import multiprocessing
import dash
import datetime
import numpy as np
import pandas as pd
from EyeTrackerAnalyzer import WARN, MESSAGE_QUEUE
try:
    from EyeTrackerAnalyzer.components.window import run_validation_window
    from EyeTrackerAnalyzer.components.tobii import Tobii
except ModuleNotFoundError:
    WARN.generate_warning(
        "Without tobii_research & PyQt6 library, Validation of eye-tracker won't work.",
        category=UserWarning)
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output
import plotly.express as px

def run_async_function(async_func):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_func())
    loop.close()

def run_tobii():
    tobii_process = Tobii(save_data=True, verbose=True)
    tobii_process.start_tracking(duration=10)

app = dash.Dash(
    __package__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True)

app.layout = dbc.Container([
    dbc.Row(dash.html.H1("Eye Tracker Analyzer")),
    dbc.Row([
        dbc.Col(
            dbc.Row([
                dash.dcc.Markdown(
                    '''
                    This interface allows you to validate the eye tracker accuracy along with the following:
                    - View gaze points
                    - View fixation points
                    - View eye tracker accuracy
                        * Comparing the gaze data with validation grid locations.
                    '''
                ),
            ])),
        dbc.Col(
            dash.html.Div([
                dbc.Row([dbc.Button("Validate Eye Tracker", color="primary", outline=True, id="open-grid-window")])
            ])),
        ]),
    dbc.Tabs([
        dbc.Tab(label="Gaze points", tab_id="eye-tracker-gaze"),
        dbc.Tab(label="Fixation", tab_id="eye-tracker-fixation"),
        dbc.Tab(label="Metrics", tab_id="eye-tracker-metrics")  
    ],
    id="tabs",
    active_tab="eye-tracker-gaze"),
    dbc.Spinner(
            [
                dash.dcc.Store(id="store"),
                dash.html.Div(id="tab-content", className="p-4"),
            ],
            delay_show=100,
        ),
])


@app.callback(
    Output('open-grid-window', 'n_clicks'),
    [Input('open-grid-window', 'n_clicks')]
)
def update_window(n_clicks):
    if n_clicks:
        print(f"executing: {run_validation_window.__name__}")
        with multiprocessing.Pool(processes=2) as pool:
            tobii_result = pool.apply_async(run_tobii)
            validation_result = pool.apply_async(run_validation_window)
            tobii_result.get()
            validation_result.get()
        print("validation window closed")
    return n_clicks

@app.callback(
    Output("tab-content", "children"),
    [Input("tabs", "active_tab"), Input("store", "data")],
)
def render_tab_content(active_tab, data):
    if active_tab == "eye-tracker-gaze":
        print("plotting gaze points")
        return render_gaze_tab()
    elif active_tab == "eye-tracker-fixation":
        print("plotting fixation points")
        return render_fixation_tab()
    elif active_tab == "eye-tracker-metrics":
        print("plotting metrics")
        return render_metrics_tab()
    return "No tab selected"

def render_gaze_tab():
    return dbc.Container([
            dbc.Row([dbc.Button("Fetch (Gaze points)", color="primary", outline=True, disabled=True, id="collect-gaze-point")], className='my-2')
        ])

def render_fixation_tab():
    return dbc.Container([
            dbc.Row([dbc.Button("Fetch (Modified Gaze points)", outline=True, color="primary", disabled=True, id="append-gaze-point")], className='my-2')
        ])

def get_file_names(prefix):
    return [f for f in os.listdir('data/') if f.startswith(prefix)]

def render_metrics_tab():
    gaze_files = get_file_names("gaze_data_")
    validation_files = get_file_names("validation_")

    return dbc.Container([
        dbc.Row([
            dbc.Col(dash.dcc.Dropdown(
                id='gaze-data-dropdown',
                options=[{'label': f, 'value': f} for f in gaze_files],
                placeholder="Select Gaze Data File"
            )),
            dbc.Col(dash.dcc.Dropdown(
                id='validation-data-dropdown',
                options=[{'label': f, 'value': f} for f in validation_files],
                placeholder="Select Validation File"
            )),
        ]),
        dbc.Row([
            dash.html.Div(id='dropdown-output'),
            dbc.Button("Analyze", color="success", outline=True, id="analyze-button"),
            dash.html.Div(id='graph-output')
        ])
    ])

@app.callback(
    Output('dropdown-output', 'children'),
    [Input('gaze-data-dropdown', 'value'),
     Input('validation-data-dropdown', 'value')]
)
def update_dropdown(gaze_data, validation_data):
    ts_gaze_data = "-"
    ts_validation_data = "-"
    if gaze_data:
        ts_gaze_data = re.search(r"gaze_data_(.*).json", gaze_data).group(1)
        ts_gaze_data = datetime.datetime.strptime(ts_gaze_data, "%Y%m%d_%H%M%S")
    if validation_data:
        ts_validation_data = re.search(r"validation_(.*).json", validation_data).group(1)
        ts_validation_data = datetime.datetime.strptime(ts_validation_data, "%Y%m%d_%H%M%S")
    return dbc.Row([
        dbc.Col(f"Timestamp: {ts_gaze_data}"),
        dbc.Col(f"Timestamp: {ts_validation_data}")
    ])

def get_confusion_matrix_metric(matrix):

    num_classes = matrix.shape[0]
    accuracy = 0.0
    precision = np.zeros(num_classes)
    recall = np.zeros(num_classes)
    f1_score = np.zeros(num_classes)

    # Calculate metrics for each class
    for i in range(num_classes):
        tp = matrix[i, i]
        fp = np.sum(matrix[:, i]) - tp
        fn = np.sum(matrix[i, :]) - tp
        tn = np.sum(matrix) - tp - fp - fn

        precision[i] = tp / (tp + fp) if tp + fp > 0 else 0
        recall[i] = tp / (tp + fn) if tp + fn > 0 else 0
        f1_score[i] = 2 * precision[i] * recall[i] / (precision[i] + recall[i]) if precision[i] + recall[i] > 0 else 0

    accuracy = np.trace(matrix) / np.sum(matrix)

    return {'accuracy': accuracy, 'precision': precision, 'recall': recall, 'f1_score': f1_score}

@app.callback(
    Output('graph-output', 'children'),
    [Input('analyze-button', 'n_clicks')],
    [Input('gaze-data-dropdown', 'value'),
     Input('validation-data-dropdown', 'value')]
)
def update_graph(n_clicks, gaze_data, validation_data):
    if n_clicks:
        matrix = np.array([
            [10, 2, 3, 1, 0, 1, 2, 1, 0],
            [1, 15, 2, 0, 2, 0, 1, 0, 1],
            [2, 1, 12, 2, 0, 1, 1, 0, 1],
            [0, 0, 1, 18, 0, 2, 0, 0, 1],
            [1, 2, 0, 0, 16, 0, 1, 0, 1],
            [0, 1, 2, 1, 0, 17, 1, 0, 1],
            [2, 0, 1, 0, 1, 1, 15, 0, 1],
            [0, 0, 0, 0, 0, 0, 0, 20, 0],
            [0, 1, 1, 1, 1, 1, 1, 0, 15]
        ])

        normalized_matrix = matrix / np.sum(matrix, axis=1, keepdims=True)
        normalized_matrix = np.round(normalized_matrix, decimals=2)
        metric = get_confusion_matrix_metric(normalized_matrix)
        labels = ["1","2","3","4","5","6","7","8","9"]
        
        # Create a DataFrame for the confusion matrix
        metric_df = pd.DataFrame.from_dict(metric)
        df = pd.DataFrame(normalized_matrix, index=labels, columns=labels)
        df = df.reset_index().melt(id_vars='index')
        df.columns = ['Validation', 'Gaze', 'Value']
        
        fig = px.imshow(
            normalized_matrix,
            x=labels,
            y=labels,
            color_continuous_scale='Blues',
            labels=dict(x="Gaze", y="Validation", color="Value"),
            text_auto=True)
        
        fig.update_layout(
            title='Validation Data Vs Gaze Data',
            xaxis=dict(side='top')
        )

        
        metric_fig = px.bar(
            metric,
            x=labels,
            y=metric_df.columns.drop(["accuracy"], errors="ignore"),
            barmode="group",
            labels={"x": "Class", "y": "Value"},
            title='Precision, Recall, and F1-Score')

        return dbc.Container([
            dash.dcc.Graph(figure=fig, className="metric-grid"),
            dash.dcc.Graph(figure=metric_fig, className="metric-values"),
            dash.dcc.Markdown(
                f'''
                Accuracy: `{metric.get('accuracy')}`
                '''
            ),
        ])
    return dash.html.Div()

if __name__ == '__main__':
    app.run(debug=True)