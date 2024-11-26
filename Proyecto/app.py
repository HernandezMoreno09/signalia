from flask import Flask, send_from_directory
import gradio as gr

# Crear la app Flask
app = Flask(__name__)

# Define tu aplicación de Gradio
def translator(audio_file=None, input_text=None):
    # Simula tu lógica de Gradio (ejemplo simple)
    return "Transcripción: Hola Mundo", "Traducción a Inglés: Hello World", "Traducción a Español: Hola Mundo", None, None, []

# Interfaz Gradio
interface = gr.Interface(
    fn=translator,
    inputs=[
        gr.Audio(sources=["microphone"], type="filepath", label="Audio"),
        gr.Textbox(label="Texto transcrito")
    ],
    outputs=[
        gr.Textbox(label="Transcripción original"),
        gr.Textbox(label="Traducción a Inglés"),
        gr.Textbox(label="Traducción a Español"),
        gr.Audio(label="Audio traducido a Inglés"),
        gr.Audio(label="Audio traducido a Español"),
        gr.Gallery(label="Imágenes")
    ],
    title="SignalIA",
    description="Traducción del inglés o español a lengua de señas mexicana."
)

# Ruta principal de Flask
@app.route("/")
def home():
    return send_from_directory("static", "index.html")  # Sirve un archivo estático como página principal

# Ruta para Gradio
@app.route("/gradio", methods=["GET", "POST"])
def gradio_app():
    return interface.launch(
        inline=True,        # Integrar Gradio dentro del servidor Flask
        share=False,        # No usar Gradio Hub
        server_name="0.0.0.0",
        server_port=None    # Flask gestiona el puerto
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)  # Flask escucha en la red local
