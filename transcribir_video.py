import os
import sys
import requests
from faster_whisper import WhisperModel
import yt_dlp

# --- CONFIGURACIÓN ---
INPUT = "https://www.youtube.com/watch?v=tKvJf3GRIxw"  # URL o ruta local
MODELO_WHISPER = "base"        # "tiny" | "base" | "small" | "medium" | "large-v3"
CARPETA_SALIDA = os.path.join(os.path.expanduser("~"), "Downloads")
# ---------------------

# Preferencia de modelos para resumen/traducción (de mejor a peor)
PREFERENCIA_MODELOS = [
    "phi4-mini",
    "qwen3",
    "llama3.2",
    "gemma3",
    "phi3",
    "llama3",
    "mistral",
]

def es_url(t):
    return t.startswith("http://") or t.startswith("https://")

def elegir_mejor_modelo():
    """Consulta Ollama, lista modelos y elige el mejor disponible."""
    print("Consultando modelos en Ollama...")
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=10)
        r.raise_for_status()
        modelos = [m["name"] for m in r.json().get("models", [])]
    except requests.exceptions.ConnectionError:
        print("❌ Ollama no responde en localhost:11434.")
        print("   Abre la aplicación Ollama (icono en la bandeja del sistema).")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error al consultar Ollama: {e}")
        sys.exit(1)

    if not modelos:
        print("❌ No hay modelos instalados en Ollama.")
        print("   Ejecuta: ollama pull phi4-mini")
        sys.exit(1)

    print(f"   Modelos disponibles: {modelos}")

    # Buscar el primer modelo de la lista de preferencia que esté instalado
    for preferido in PREFERENCIA_MODELOS:
        for instalado in modelos:
            # Coincidencia exacta o con tag (ej: "phi4-mini:3.8b")
            if instalado == preferido or instalado.startswith(preferido + ":"):
                print(f"   ✅ Modelo seleccionado: {instalado}")
                return instalado

    # Si ninguno de la lista está, usar el primero disponible
    print(f"   ⚠️  Ninguno de los preferidos está. Usando: {modelos[0]}")
    return modelos[0]

def descargar_audio(url, carpeta):
    archivo = os.path.join(carpeta, "audio_temp.mp3")
    opciones = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192'}],
        'outtmpl': archivo.replace('.mp3', ''),
        'quiet': False,
        'js_runtimes': {'deno': {}},
    }
    with yt_dlp.YoutubeDL(opciones) as ydl:
        ydl.download([url])
    return archivo

def main():
    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    # PASO 0: Elegir modelo de Ollama automáticamente
    modelo_ollama = elegir_mejor_modelo()

    # PASO 1: Obtener audio
    if es_url(INPUT):
        print(f"\nPaso 1/3: Descargando audio en '{CARPETA_SALIDA}'...")
        try:
            archivo_audio = descargar_audio(INPUT, CARPETA_SALIDA)
            descargado = True
        except Exception as e:
            print(f"   ❌ Error al descargar: {e}"); sys.exit(1)
    else:
        if not os.path.isfile(INPUT):
            print(f"❌ No existe el archivo: {INPUT}"); sys.exit(1)
        archivo_audio = INPUT
        descargado = False
        print(f"Paso 1/3: Usando archivo local.")

    # PASO 2: Transcribir
    print(f"\nPaso 2/3: Transcribiendo con Whisper '{MODELO_WHISPER}'...")
    print("   ⏳ Esto puede tardar. No cierres la ventana.")
    try:
        model = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
        segments, info = model.transcribe(archivo_audio, beam_size=5)
        transcripcion = " ".join([seg.text for seg in segments])
        idioma = info.language
        print(f"   ✅ Transcripción completa. Idioma: {idioma}")
    except Exception as e:
        print(f"   ❌ Error en transcripción: {e}"); sys.exit(1)

    # PASO 3: Resumen + traducción
    print(f"\nPaso 3/3: Resumen y traducción con '{modelo_ollama}'...")
    prompt = f"""The following is a transcript in language '{idioma}'.

TASK 1: Write a concise summary in the SAME language as the transcript.
TASK 2: Translate that summary into English.

Format:
SUMMARY ({idioma}):
<...>

ENGLISH TRANSLATION:
<...>

Transcript:
---
{transcripcion}
---
"""
    try:
        r = requests.post("http://localhost:11434/api/generate",
                          json={"model": modelo_ollama,
                                "prompt": prompt,
                                "stream": False},
                          timeout=1800)
        r.raise_for_status()
        resultado = r.json()["response"]
    except requests.exceptions.HTTPError as e:
        print(f"   ❌ Error HTTP: {e}")
        # Guardar transcripción como respaldo
        out = os.path.join(CARPETA_SALIDA, "transcripcion_solo.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(transcripcion)
        print(f"   Transcripción guardada en: {out}")
        sys.exit(1)
    except Exception as e:
        print(f"   ❌ Error con Ollama: {e}")
        out = os.path.join(CARPETA_SALIDA, "transcripcion_solo.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(transcripcion)
        print(f"   Transcripción guardada en: {out}")
        sys.exit(1)

    # Guardar todo
    out = os.path.join(CARPETA_SALIDA, "resultado_transcripcion.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write("=== TRANSCRIPCIÓN ===\n\n" + transcripcion)
        f.write("\n\n\n=== RESUMEN Y TRADUCCIÓN ===\n\n" + resultado)

    if descargado and os.path.exists(archivo_audio):
        os.remove(archivo_audio)

    print(f"\n✅ COMPLETADO: {out}")
    print("\n--- VISTA PREVIA ---\n" + resultado)

if __name__ == "__main__":
    main()