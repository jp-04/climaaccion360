import os
import sqlite3

from flask import Flask, jsonify, render_template, request

from auth import bp as auth_bp, current_user
from data_loader import DataValidationError, load_emissions_data, prepare_for_visualization, summarize_emissions
from database import init_app as init_database, save_prediction
from modelos_ml.prediccion import predecir
from pipeline.actualizar_datos import update_dataset
from weather_service import WeatherServiceError, get_current_weather


app = Flask(__name__)
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("Configura la variable de entorno SECRET_KEY antes de iniciar la app")
app.config.update(
    SECRET_KEY=secret_key,
    DATABASE=os.environ.get("DATABASE_PATH", os.path.join(app.instance_path, "usuarios.db")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER") == "true",
)
init_database(app)
app.register_blueprint(auth_bp)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ods13")
def ods13():
    return render_template("ods13.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/modelos")
def modelos():
    return render_template("modelos.html")


@app.route("/acciones")
def acciones():
    return render_template("acciones.html")


@app.route("/api/emisiones")
def emisiones_api():
    try:
        frame = load_emissions_data()
    except (DataValidationError, FileNotFoundError) as error:
        return jsonify({"status": "error", "error": str(error), "data": []}), 500

    return jsonify(
        {
            "status": "success" if not frame.empty else "empty",
            "data": prepare_for_visualization(frame),
            "indicator": "EN.GHG.CO2.PC.CE.AR5",
            "country": "Colombia",
            "unit": "Toneladas de CO₂ per cápita",
            "available_years": sorted(frame["Año"].dropna().astype(int).unique().tolist()),
            "statistics": summarize_emissions(frame),
        }
    )


@app.route("/api/actualizar-datos", methods=["GET", "POST"])
def actualizar_datos_api():
    try:
        rows = update_dataset()
    except Exception as error:
        app.logger.exception("Error actualizando datos climáticos")
        return jsonify({"status": "error", "message": "No fue posible actualizar los datos", "error": str(error)}), 502

    return jsonify(
        {
            "status": "success",
            "message": "Datos climáticos actualizados correctamente",
            "rows": rows,
        }
    )


@app.route("/api/prediccion")
def prediccion_api():
    model_name = request.args.get("modelo", "regresion_lineal")
    year_text = request.args.get("año", request.args.get("year"))
    if year_text is None:
        return jsonify({"error": "El parámetro año es obligatorio"}), 400
    try:
        result = predecir(int(year_text), model_name)
    except (TypeError, ValueError, OSError) as error:
        return jsonify({"error": str(error)}), 400
    user = current_user()
    if user is not None:
        try:
            save_prediction(user["id"], result)
        except sqlite3.Error:
            app.logger.exception("No fue posible guardar la predicción del usuario")
    return jsonify(result)


@app.route("/api/clima")
def clima_api():
    try:
        weather = get_current_weather()
    except WeatherServiceError as error:
        return jsonify({"status": "error", "error": str(error)}), 503
    return jsonify({"status": "success", **weather})


if __name__ == "__main__":
    app.run(debug=True)
