import gradio as gr
import whisper
from translate import Translator
from dotenv import dotenv_values
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
from langdetect import detect, LangDetectException
import mysql.connector

# Definir las variables de configuración directamente en el archivo Python
DB_HOST = "127.0.0.1"
DB_USER = "root"  # Usuario cambiado a 'root'
DB_PASSWORD = "251121"  # Contraseña de la base de datos
DB_NAME = "proyecto_senas"
DB_PORT = 3307  # Puerto personalizado (en este caso 3307)
charset = 'utf8mb4'

ELEVENLABS_API_KEY = "sk_8644cbbd1af0db8b897c6272f14dc28332481da625d81104"  # Asegúrate de colocar tu API Key real


# Conectar a la base de datos MariaDB
def connect_db():
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=DB_PORT,
            charset='utf8mb4',
            collation='utf8mb4_general_ci'
        )
        print("Conexión exitosa a la base de datos")
        return connection
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None


# Función para realizar la traducción y otras operaciones
def translator(audio_file=None, input_text=None):
    try:
        # Verificar si el usuario introdujo un texto o subió un archivo de audio
        if audio_file:
            # 1. Transcribir texto usando Whisper (si hay un archivo de audio)
            try:
                model = whisper.load_model("base")
                result = model.transcribe(audio_file, language="es", fp16=False)  # Ajustar lenguaje según necesidad
                transcription = result["text"]
            except Exception as e:
                raise gr.Error(f"Se ha producido un error transcribiendo el texto: {str(e)}")
        elif input_text:
            transcription = input_text.strip()  # Eliminar espacios al principio y al final
        else:
            raise gr.Error("Por favor, ingrese un archivo de audio o un texto transcrito.")

        # Verificar que el texto no esté vacío
        if not transcription:
            raise gr.Error("El texto proporcionado está vacío. Por favor, ingrese un texto válido.")

        print(f"Texto original: {transcription}")

        # Detectar el idioma del texto ingresado (usando langdetect)
        try:
            detected_lang = detect(transcription)
            print(f"Idioma detectado: {detected_lang}")

            if detected_lang == "es":
                # Si el texto está en español, traducimos a inglés
                es_transcription = transcription
                en_transcription = Translator(from_lang="es", to_lang="en").translate(transcription)
            elif detected_lang == "en":
                # Si el texto está en inglés, traducimos a español
                en_transcription = transcription
                es_transcription = Translator(from_lang="en", to_lang="es").translate(transcription)
            else:
                raise gr.Error("El idioma del texto no es ni inglés ni español. Por favor, ingrese un texto en uno de esos idiomas.")
        except LangDetectException:
            raise gr.Error("No se pudo detectar el idioma del texto. Asegúrese de que el texto sea válido y esté en inglés o español.")
        except Exception as e:
            raise gr.Error(f"Se ha producido un error detectando el idioma o traduciendo el texto: {str(e)}")

        print(f"Texto traducido a Inglés: {en_transcription}")
        print(f"Texto traducido a Español: {es_transcription}")

        # Inicializar la variable `urls_imagen` con una lista vacía
        urls_imagen = []

        # Conexión a la base de datos para obtener la URL de las imágenes
        db_connection = connect_db()
        if db_connection:
            try:
                cursor = db_connection.cursor()

                # Separar las palabras de la transcripción en español
                palabras = es_transcription.split()
                
                # Crear un conjunto para almacenar las palabras únicas y evitar duplicados
                palabras_unicas = set(palabras)

                # Construir una consulta para obtener todas las URLs en una sola operación
                # Usamos JOIN para obtener las URLs de la tabla Lenguaje_senas
                placeholders = ', '.join(['%s'] * len(palabras_unicas))
                query = f"""
                    SELECT L.URL 
                    FROM Palabras P
                    JOIN Interpretacion I ON P.ID_palabra = I.ID_palabra
                    JOIN Lenguaje_senas L ON I.ID_sena = L.ID_sena
                    WHERE P.Palabra_espanol IN ({placeholders})
                """
                
                cursor.execute(query, list(palabras_unicas))
                resultados = cursor.fetchall()

                # Agregar las URLs obtenidas a la lista
                urls_imagen = [url[0].replace("drive.google.com", "drive.google.com/uc?export=view") for url in resultados]

                if not urls_imagen:
                    # Si no se encuentran URLs, agregar una URL por defecto o mensaje
                    urls_imagen = ["URL por defecto"]

                print("URLs de imágenes encontradas:", urls_imagen)

                cursor.close()
                db_connection.close()

            except mysql.connector.Error as err:
                print(f"Error al interactuar con la base de datos: {err}")
                urls_imagen = ["URL por defecto"]

        # 3. Generar audio traducido
        try:
            en_save_file_path = text_to_speech(en_transcription, "en")
            es_save_file_path = text_to_speech(es_transcription, "es")
        except Exception as e:
            raise gr.Error(f"Se ha producido un error generando el audio: {str(e)}")

        # Devolver los resultados (archivos de audio, transcripciones, traducciones y URLs de las imágenes)
        return transcription, en_transcription, es_transcription, en_save_file_path, es_save_file_path, urls_imagen

    except Exception as e:
        print(f"Error en la ejecución general: {str(e)}")
        raise gr.Error(f"Error en la ejecución: {str(e)}")

# Función para generar el archivo de audio a partir del texto
def text_to_speech(text: str, language: str) -> str:
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        response = client.text_to_speech.convert(
            voice_id="nPczCjzI2devNBz1zQrb",  # Brian
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=0.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )

        save_file_path = f"{language}.mp3"

        with open(save_file_path, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)

    except Exception as e:
        raise gr.Error(f"Se ha producido un error creando el audio: {str(e)}")

    return save_file_path

# Interfaz Gradio para mostrar transcripciones y traducciones
web = gr.Interface(
    fn=translator,
    inputs=[
        gr.Audio(
            sources=["microphone"],
            type="filepath",
            label="Graba un audio en español o inglés (opcional)"
        ),
        gr.Textbox(
            label="O ingresa un texto transcrito (opcional)",
            placeholder="Introduce el texto transcrito en inglés o español...",
            lines=2
        )
    ],
    outputs=[
        gr.Textbox(label="Transcripción original"),  # Transcripción del audio original
        gr.Textbox(label="Traducción a Inglés"),     # Traducción al inglés
        gr.Textbox(label="Traducción a Español"),    # Traducción al español
        gr.Audio(label="Audio traducido a Inglés"),  # Audio en inglés
        gr.Audio(label="Audio traducido a Español"), # Audio en español
        gr.Gallery(label="Imágenes de Lengua de Señas")  # Mostrar las imágenes en una galería
    ],
    title="SignalIA",
    description="Traducción del inglés o español a lengua de señas mexicana."
)

# Lanza la interfaz
web.launch(share=True)

