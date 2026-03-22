from flask import Blueprint, render_template, request, current_app
from flask_login import login_required
import pandas as pd
import plotly.express as px
import numpy as np
import os
import matplotlib.pyplot as plt

from app.utils import role_required
from app.ml_models import random_forest_model, xgboost_model, lstm_model

forecast = Blueprint("forecast", __name__)


# ================= SAFE DATA PATH =================
def load_data():
    try:
        file_path = os.path.join(current_app.root_path, "..", "data", "crop_production.csv")
        file_path = os.path.abspath(file_path)
        return pd.read_csv(file_path)
    except Exception as e:
        print("Data Load Error:", e)
        return pd.DataFrame()


@forecast.route("/forecast", methods=["GET", "POST"])
@login_required
@role_required(["Admin", "Data Analyst"])
def show_forecast():

    df = load_data()

    if df.empty:
        return "Dataset not found or empty."

    states = df["State_Name"].dropna().unique()
    crops = df["Crop"].dropna().unique()

    plot_html = None
    adjusted = None
    error = None
    model_names = None
    mae_scores = None
    r2_scores = None

    if request.method == "POST":

        try:
            state = request.form.get("state")
            crop = request.form.get("crop")

            rainfall = float(request.form.get("rainfall", 0))
            temperature = float(request.form.get("temperature", 0))
        except ValueError:
            error = "Invalid input values."
            return render_template("forecast.html", states=states, crops=crops, error=error)

        filtered = df[
            (df["State_Name"] == state) &
            (df["Crop"] == crop)
        ]

        if filtered.empty:
            error = "No data available."
            return render_template("forecast.html", states=states, crops=crops, error=error)

        # ================= TREND =================
        year_column = "Crop_Year" if "Crop_Year" in df.columns else "Year"

        trend = (
            filtered.groupby(year_column)["Production"]
            .sum()
            .sort_index()
        )

        if len(trend) < 5:
            error = "Not enough historical data."
            return render_template("forecast.html", states=states, crops=crops, error=error)

        # ================= FORECAST =================
        future_values = list(trend.tail(5).values)
        last_value = future_values[-1]

        for _ in range(20):
            last_value *= 1.03
            future_values.append(last_value)

        forecast_values = future_values[-20:]

        climate_factor = 1 + (rainfall / 100) - (temperature * 0.02)
        adjusted = [float(x * climate_factor) for x in forecast_values]

        # ================= PLOT =================
        fig = px.line(
            x=trend.index,
            y=trend.values,
            labels={"x": "Year", "y": "Production"},
            title="Crop Production Forecast"
        )

        future_years = list(range(int(trend.index.max()) + 1,
                                 int(trend.index.max()) + 21))

        fig.add_scatter(
            x=future_years,
            y=adjusted,
            mode="lines",
            name="Forecast"
        )

        plot_html = fig.to_html(full_html=False)

        # ================= ML MODELS (SAFE) =================
        try:
            years = np.array(trend.index).reshape(-1, 1)
            values = np.array(trend.values)

            rf_pred, rf_mae, rf_r2 = random_forest_model(years, values)
            xgb_pred, xgb_mae, xgb_r2 = xgboost_model(years, values)
            lstm_pred, lstm_mae, lstm_r2 = lstm_model(values)

            model_names = ["Random Forest", "XGBoost", "LSTM"]
            mae_scores = [rf_mae, xgb_mae, lstm_mae]
            r2_scores = [rf_r2, xgb_r2, lstm_r2]

            # ================= SAFE CHART SAVE =================
            chart_path = os.path.join(current_app.root_path, "static", "accuracy_chart.png")

            plt.figure()
            plt.bar(model_names, r2_scores)
            plt.title("Model Accuracy Comparison")
            plt.ylabel("R2 Score")
            plt.tight_layout()
            plt.savefig(chart_path)
            plt.close()

        except Exception as e:
            print("ML Error:", e)

    return render_template(
        "forecast.html",
        states=states,
        crops=crops,
        plot_html=plot_html,
        adjusted=adjusted,
        error=error,
        model_names=model_names,
        mae_scores=mae_scores,
        r2_scores=r2_scores
    )
