from flask import Blueprint, render_template, jsonify, request, current_app
from flask_login import login_required, current_user
import pandas as pd
import os
import numpy as np

dashboard = Blueprint("dashboard", __name__)


# ================= LOAD DATA SAFELY =================
def load_data():
    try:
        file_path = os.path.join(current_app.root_path, "data", "crop_production.csv")
        
        # fallback if not found
        if not os.path.exists(file_path):
            file_path = os.path.join(current_app.root_path, "..", "data", "crop_production.csv")

        file_path = os.path.abspath(file_path)
        df = pd.read_csv(file_path)
        return df

    except Exception as e:
        print("CSV Load Error:", e)
        return pd.DataFrame()


# ================= MAIN DASHBOARD =================
@dashboard.route("/dashboard")   # ✅ FIXED ROUTE
@login_required
def show_dashboard():

    df = load_data()

    if df.empty:
        return render_template(
            "dashboard.html",
            total_states=0,
            total_production=0,
            states=[],
            production_values=[],
            crops=[],
            crop_values=[],
            trend_labels=[],
            trend_values=[],
            growth_percent=0,
            risk_overview="NO DATA",
            forecast_next=0
        )

    # ================= KPIs =================
    total_states = df["State_Name"].nunique()
    total_production = int(df["Production"].sum())

    # ================= TOP STATES =================
    state_data = (
        df.groupby("State_Name")["Production"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    # ================= TOP CROPS =================
    crop_data = (
        df.groupby("Crop")["Production"]
        .sum()
        .sort_values(ascending=False)
        .head(5)
    )

    # ================= TREND =================
    year_column = "Crop_Year" if "Crop_Year" in df.columns else "Year"

    trend = df.groupby(year_column)["Production"].sum().sort_index()

    trend_labels = trend.index.tolist()
    trend_values = trend.values.tolist()

    # ================= GROWTH =================
    if len(trend_values) >= 2 and trend_values[-2] != 0:
        growth_percent = round(
            ((trend_values[-1] - trend_values[-2]) / trend_values[-2]) * 100, 2
        )
    else:
        growth_percent = 0

    # ================= RISK =================
    avg_production = np.mean(trend_values)

    if avg_production > 500000:
        risk_overview = "LOW"
    elif avg_production > 200000:
        risk_overview = "MEDIUM"
    else:
        risk_overview = "HIGH"

    # ================= FORECAST =================
    last_value = trend_values[-1] if trend_values else 0
    forecast_next = int(last_value * 1.03)

    return render_template(
        "dashboard.html",
        total_states=total_states,
        total_production=total_production,
        states=state_data.index.tolist(),
        production_values=state_data.values.tolist(),
        crops=crop_data.index.tolist(),
        crop_values=crop_data.values.tolist(),
        trend_labels=trend_labels,
        trend_values=trend_values,
        growth_percent=growth_percent,
        risk_overview=risk_overview,
        forecast_next=forecast_next
    )


# ================= CHATBOT =================
@dashboard.route("/chatbot", methods=["POST"])
@login_required
def chatbot():

    data = request.get_json()
    message = data.get("message", "").lower()
    mode = data.get("mode", "admin")

    df = load_data()

    if df.empty:
        return jsonify({"reply": "Data not available."})

    response = "Please ask about rice, rain, or storage."

    if "rice" in message:
        total = int(
            df[df["Crop"].str.contains("Rice", case=False, na=False)]["Production"].sum()
        )

        if mode == "farmer":
            response = f"Rice production is {total:,} tonnes. Keep storage dry and safe."
        else:
            response = f"Total Rice Production: {total:,} metric tonnes."

    elif "rain" in message:
        response = "Rainfall positively correlates with crop production."

    elif "storage" in message:
        response = "Maintain safety stock using EOQ model."

    return jsonify({"reply": response})
