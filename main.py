import io
import sys
import traceback
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar cliente de Gemini tomando explícitamente la variable de entorno
api_key = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

class EjercicioRequest(BaseModel):
    codigo: str

@app.post("/ejecutar")
def ejecutar_codigo(req: EjercicioRequest):
    codigo_usuario = req.codigo

    # 1. Sanitización de caracteres
    codigo_usuario = codigo_usuario.replace("\xa0", " ").expandtabs(4)

    # 2. Aislar código del alumno
    marca = "# Escribe tu código aquí abajo:"
    if marca in codigo_usuario:
        partes = codigo_usuario.split(marca)
        codigo_a_evaluar = partes[1]
    else:
        codigo_a_evaluar = codigo_usuario

    # 3. Validar si está vacío
    if not codigo_a_evaluar.strip():
        return {
            "exito": False,
            "salida": "",
            "mensaje_alerta": "ingrese el codigo solicitado"
        }

    # 4. Capturar consola
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    exito = True
    error_detalle = ""

    try:
        exec(codigo_usuario, {})
    except Exception:
        exito = False
        error_detalle = traceback.format_exc()

    sys.stdout = old_stdout
    salida_consola = new_stdout.getvalue()

    # 5. Tutor IA con análisis detallado del error
    explicacion_ia = ""
    if not exito:
        prompt_tutor = (
            "Eres un profesor paciente de programación para principiantes absolutos. "
            "El alumno escribió un código en Python que generó el siguiente error:\n"
            f"{error_detalle}\n"
            "Explica de forma muy sencilla, amable y en español exacto: "
            "1. Qué causó el error. "
            "2. En qué línea ocurrió (si aplica). "
            "3. Cómo solucionarlo de forma directa. "
            "Sé breve (máximo 4 líneas)."
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_tutor
            )
            explicacion_ia = response.text
        except Exception as e:
            explicacion_ia = f"Error al conectar con el tutor IA: {str(e)}"

    mensaje_exito = ""
    if exito and salida_consola.strip():
        mensaje_exito = "¡Excelente! Has completado la secuencia algorítmica correctamente."

    return {
        "exito": exito,
        "salida": salida_consola,
        "explicacion_ia": explicacion_ia,
        "mensaje": mensaje_exito
    }

@app.get("/", response_class=HTMLResponse)
def servir_home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()