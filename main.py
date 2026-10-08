import io
import sys
import traceback
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

# Inicializar cliente de Gemini (asegúrate de tener tu GEMINI_API_KEY en las variables de entorno)
client = genai.Client()

class EjercicioRequest(BaseModel.Model):
    codigo: str

@app.post("/ejecutar")
def ejecutar_codigo(req: EjercicioRequest):
    codigo_usuario = req.codigo

    # 1. Sanitización de caracteres invisibles y tabulaciones
    codigo_usuario = codigo_usuario.replace("\xa0", " ").expandtabs(4)

    # 2. Aislar el código escrito por el alumno después de la marca
    marca = "# Escribe tu código aquí abajo:"
    if marca in codigo_usuario:
        partes = codigo_usuario.split(marca)
        codigo_a_evaluar = partes[1]
    else:
        codigo_a_evaluar = codigo_usuario

    # 3. Validar si el espacio de código está vacío
    if not codigo_a_evaluar.strip():
        return {
            "exito": False,
            "salida": "",
            "mensaje_alerta": "ingrese el codigo solicitado"
        }

    # 4. Capturar la salida estándar (print)
    old_stdout = sys.stdout
    new_stdout = io.StringIO()
    sys.stdout = new_stdout

    exito = True
    error_detalle = ""

    try:
        # Ejecución segura en entorno aislado local
        exec(codigo_usuario, {})
    except Exception:
        exito = False
        error_detalle = traceback.format_exc()

    sys.stdout = old_stdout
    salida_consola = new_stdout.getvalue()

    # 5. Si hay error, consultar al tutor de IA
    explicacion_ia = ""
    if not exito:
        prompt_tutor = (
            "Eres un profesor paciente de programación para principiantes absolutos. "
            "El alumno intentó resolver un ejercicio básico de secuencias y obtuvo este error:\n"
            f"{error_detalle}\n"
            "Explica de forma muy sencilla, amable y en español qué falló y cómo corregirlo en máximo 3 líneas."
        )
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_tutor
            )
            explicacion_ia = response.text
        except Exception:
            explicacion_ia = "Revisa la sintaxis de tu código, parece haber un error tipográfico."

    # Validar si completó correctamente el ejercicio
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