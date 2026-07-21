#!/usr/bin/env python3

import math
import os
import subprocess
import tempfile
import wave
import threading
from dataclasses import dataclass
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import tkinter as tk


@dataclass
class Segmento:
    inicio: float
    fin: float
    texto: str


class TranscripcionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Transcripción de Video a Texto")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        self.video_path = StringVar()
        self.idioma_var = StringVar(value="")
        self.salida_dir = StringVar()
        
        self.procesando = False
        self.progreso_actual = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(W, E, N, S))
        
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        titulo = ttk.Label(main_frame, text="Transcripción de Video a Texto", 
                          font=('Helvetica', 16, 'bold'))
        titulo.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        ttk.Label(main_frame, text="Archivo de Video:").grid(row=1, column=0, sticky=W, pady=5)
        
        video_frame = ttk.Frame(main_frame)
        video_frame.grid(row=1, column=1, columnspan=2, sticky=(W, E), pady=5)
        video_frame.columnconfigure(0, weight=1)
        
        self.video_entry = ttk.Entry(video_frame, textvariable=self.video_path)
        self.video_entry.grid(row=0, column=0, sticky=(W, E), padx=(0, 5))
        
        btn_seleccionar = ttk.Button(video_frame, text="Seleccionar", 
                                    command=self.seleccionar_video)
        btn_seleccionar.grid(row=0, column=1)
        
        config_frame = ttk.LabelFrame(main_frame, text="Configuración", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(W, E), pady=10)
        config_frame.columnconfigure(1, weight=1)
        
        ttk.Label(config_frame, text="Idioma:").grid(row=0, column=0, sticky=W, pady=2)
        idiomas = ["", "Español", "Inglés", "Francés", "Alemán", "Italiano", 
                  "Portugués", "Ruso", "Japonés", "Chino", "Árabe", "Coreano", 
                  "Holandés", "Polaco", "Turco", "Sueco", "Noruego", "Finlandés",
                  "Danés", "Griego", "Checo", "Húngaro", "Rumano", "Búlgaro",
                  "Ucraniano", "Vietnamita", "Tailandés", "Indonesio", "Malayo"]
        idioma_combo = ttk.Combobox(config_frame, textvariable=self.idioma_var, 
                                   values=idiomas, state="readonly", width=20)
        idioma_combo.grid(row=0, column=1, sticky=W, pady=2)
        ttk.Label(config_frame, text="(dejar vacío = detección automática)").grid(row=0, column=2, sticky=W, padx=10)
        
        ttk.Label(config_frame, text="Carpeta salida:").grid(row=1, column=0, sticky=W, pady=5)
        salida_frame = ttk.Frame(config_frame)
        salida_frame.grid(row=1, column=1, columnspan=2, sticky=(W, E), pady=5)
        salida_frame.columnconfigure(0, weight=1)
        
        self.salida_entry = ttk.Entry(salida_frame, textvariable=self.salida_dir)
        self.salida_entry.grid(row=0, column=0, sticky=(W, E), padx=(0, 5))
        
        btn_salida = ttk.Button(salida_frame, text="Seleccionar", 
                               command=self.seleccionar_carpeta)
        btn_salida.grid(row=0, column=1)
        
        info_frame = ttk.Frame(config_frame)
        info_frame.grid(row=2, column=0, columnspan=3, pady=5)
        
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        self.btn_transcribir = ttk.Button(btn_frame, text="▶ Transcribir", 
                                         command=self.iniciar_transcripcion, width=25)
        self.btn_transcribir.grid(row=0, column=0, padx=5)
        
        self.btn_cancelar = ttk.Button(btn_frame, text="✖ Cancelar", 
                                      command=self.cancelar_transcripcion, 
                                      state="disabled", width=20)
        self.btn_cancelar.grid(row=0, column=1, padx=5)
        
        self.progress = ttk.Progressbar(main_frame, mode='determinate', length=400)
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(W, E), pady=10)
        
        progreso_info_frame = ttk.Frame(main_frame)
        progreso_info_frame.grid(row=5, column=0, columnspan=3, sticky=(W, E), pady=5)
        progreso_info_frame.columnconfigure(0, weight=1)
        progreso_info_frame.columnconfigure(1, weight=1)
        
        self.progreso_estado = ttk.Label(progreso_info_frame, text="Estado: Esperando...", font=('Helvetica', 9))
        self.progreso_estado.grid(row=0, column=0, sticky=W)
        
        self.progreso_fragmento = ttk.Label(progreso_info_frame, text="Fragmento: 0/0", font=('Helvetica', 9))
        self.progreso_fragmento.grid(row=1, column=0, sticky=W)
        
        self.progreso_porcentaje = ttk.Label(progreso_info_frame, text="Progreso: 0%", font=('Helvetica', 9))
        self.progreso_porcentaje.grid(row=1, column=1, sticky=E)
        
        log_frame = ttk.LabelFrame(main_frame, text="Log de Transcripción", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(W, E, N, S), pady=10)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_area = ScrolledText(log_frame, height=15, wrap=WORD, 
                                    font=('Courier', 9), state='disabled')
        self.log_area.grid(row=0, column=0, sticky=(W, E, N, S))
        
        self.log_area.tag_config('info', foreground='blue')
        self.log_area.tag_config('warning', foreground='orange')
        self.log_area.tag_config('error', foreground='red')
        self.log_area.tag_config('success', foreground='green')
        
        self.status_bar = ttk.Label(main_frame, text="Listo", relief=SUNKEN, anchor=W)
        self.status_bar.grid(row=7, column=0, columnspan=3, sticky=(W, E), pady=(5, 0))
        
    def seleccionar_video(self):
        archivos = filedialog.askopenfilename(
            title="Seleccionar archivo de video",
            filetypes=[("Archivos de video", "*.mp4 *.mkv *.avi *.mov *.flv *.wmv *.m4v *.webm"), 
                      ("Todos los archivos", "*.*")]
        )
        if archivos:
            self.video_path.set(archivos)
            if not self.salida_dir.get():
                self.salida_dir.set(os.path.dirname(archivos))
    
    def seleccionar_carpeta(self):
        carpeta = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if carpeta:
            self.salida_dir.set(carpeta)
    
    def log_message(self, mensaje, tag=None):
        self.log_area.configure(state='normal')
        if tag:
            self.log_area.insert(END, mensaje + "\n", tag)
        else:
            self.log_area.insert(END, mensaje + "\n")
        self.log_area.see(END)
        self.log_area.configure(state='disabled')
        self.root.update_idletasks()
    
    def actualizar_progreso(self, valor, mensaje="", fragmento_actual=0, total_fragmentos=0):
        self.progress['value'] = valor
        if mensaje:
            self.status_bar.config(text=mensaje)
        
        self.progreso_porcentaje.config(text=f"Progreso: {int(valor)}%")
        
        if fragmento_actual > 0 and total_fragmentos > 0:
            self.progreso_fragmento.config(text=f"Fragmento: {fragmento_actual}/{total_fragmentos}")
        
        self.root.update_idletasks()
    
    def actualizar_estado(self, estado):
        self.progreso_estado.config(text=f"Estado: {estado}")
        self.root.update_idletasks()
    
    def iniciar_transcripcion(self):
        if self.procesando:
            return
            
        if not self.video_path.get():
            messagebox.showerror("Error", "Por favor selecciona un archivo de video")
            return
            
        if not os.path.isfile(self.video_path.get()):
            messagebox.showerror("Error", "El archivo de video no existe")
            return
        
        self.log_area.configure(state='normal')
        self.log_area.delete(1.0, END)
        self.log_area.configure(state='disabled')
        
        self.procesando = True
        self.btn_transcribir.config(state="disabled")
        self.btn_cancelar.config(state="normal")
        self.actualizar_progreso(0, "Iniciando transcripción...")
        self.actualizar_estado("Iniciando")
        
        self.hilo = threading.Thread(target=self.ejecutar_transcripcion)
        self.hilo.daemon = True
        self.hilo.start()
    
    def cancelar_transcripcion(self):
        if self.procesando:
            self.procesando = False
            self.log_message("Cancelando proceso...", "warning")
            self.status_bar.config(text="Cancelado")
            self.actualizar_progreso(0)
            self.btn_transcribir.config(state="normal")
            self.btn_cancelar.config(state="disabled")
    
    def ejecutar_transcripcion(self):
        try:
            def log_callback(mensaje, tag=None):
                if not self.procesando:
                    return
                self.root.after(0, lambda: self.log_message(mensaje, tag))
            
            def progreso_callback(valor, mensaje, fragmento_actual=0, total_fragmentos=0):
                if not self.procesando:
                    return
                self.root.after(0, lambda: self.actualizar_progreso(valor, mensaje, 
                                                                   fragmento_actual, 
                                                                   total_fragmentos))
            
            def estado_callback(estado):
                if not self.procesando:
                    return
                self.root.after(0, lambda: self.actualizar_estado(estado))
            
            idioma_codigo = {
                "Español": "es", "Inglés": "en", "Francés": "fr", "Alemán": "de",
                "Italiano": "it", "Portugués": "pt", "Ruso": "ru", "Japonés": "ja",
                "Chino": "zh", "Árabe": "ar", "Coreano": "ko", "Holandés": "nl",
                "Polaco": "pl", "Turco": "tr", "Sueco": "sv", "Noruego": "no",
                "Finlandés": "fi", "Danés": "da", "Griego": "el", "Checo": "cs",
                "Húngaro": "hu", "Rumano": "ro", "Búlgaro": "bg", "Ucraniano": "uk",
                "Vietnamita": "vi", "Tailandés": "th", "Indonesio": "id", "Malayo": "ms"
            }
            
            idioma = idioma_codigo.get(self.idioma_var.get(), None)
            
            transcribir_video_con_callback(
                video_path=self.video_path.get(),
                idioma=idioma,
                salida_dir=self.salida_dir.get() or None,
                log_callback=log_callback,
                progreso_callback=progreso_callback,
                estado_callback=estado_callback,
                cancelar_check=lambda: not self.procesando
            )
            
            if self.procesando:
                self.root.after(0, lambda: self.log_message("✅ Transcripción completada exitosamente!", "success"))
                self.root.after(0, lambda: self.status_bar.config(text="Completado"))
                self.root.after(0, lambda: self.actualizar_progreso(100, "Completado!"))
                self.root.after(0, lambda: messagebox.showinfo("Completado", 
                    "La transcripción se ha completado exitosamente.\n"
                    "Los archivos se han guardado en la carpeta de salida."))
        
        except Exception as e:
            if self.procesando:
                self.root.after(0, lambda: self.log_message(f"❌ Error: {str(e)}", "error"))
                self.root.after(0, lambda: self.status_bar.config(text="Error"))
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante la transcripción:\n{str(e)}"))
        finally:
            self.procesando = False
            self.root.after(0, lambda: self.btn_transcribir.config(state="normal"))
            self.root.after(0, lambda: self.btn_cancelar.config(state="disabled"))


def transcribir_video_con_callback(
    video_path: str,
    idioma: str | None = None,
    salida_dir: str | None = None,
    log_callback=None,
    progreso_callback=None,
    estado_callback=None,
    cancelar_check=None,
) -> str:
    
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"No se encontró el archivo: {video_path}")

    from faster_whisper import WhisperModel
    import imageio_ffmpeg

    nombre_base = os.path.splitext(os.path.basename(video_path))[0]
    salida_dir = salida_dir or os.path.dirname(os.path.abspath(video_path))
    os.makedirs(salida_dir, exist_ok=True)

    if log_callback:
        log_callback("🧠 Modelo: large-v3", "success")
        log_callback("💻 Dispositivo: CPU", "info")
        log_callback("⏱️ Nota: Este proceso puede tomar varias horas para videos largos", "warning")
        log_callback("Preparando ffmpeg embebido...", "info")
    
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        raise RuntimeError(f"Error al obtener ffmpeg: {e}")

    if log_callback:
        log_callback("Cargando modelo Whisper 'large-v3' en CPU... (puede tardar varios minutos)", "info")
    
    if estado_callback:
        estado_callback("Cargando modelo")
    
    if cancelar_check and cancelar_check():
        raise InterruptedError("Proceso cancelado por el usuario")
    
    modelo = WhisperModel("large-v3", device="cpu", compute_type="int8")

    with tempfile.TemporaryDirectory() as tmp:
        audio_completo = os.path.join(tmp, "audio.wav")
        if log_callback:
            log_callback("Extrayendo audio del video...", "info")
        
        if estado_callback:
            estado_callback("Extrayendo audio")
        
        if progreso_callback:
            progreso_callback(5, "Extrayendo audio...")
        
        cmd = [
            ffmpeg_exe, "-y", "-i", video_path,
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-acodec", "pcm_s16le",
            audio_completo,
        ]
        subprocess.run(cmd, capture_output=True, check=True)

        if cancelar_check and cancelar_check():
            raise InterruptedError("Proceso cancelado por el usuario")

        with wave.open(audio_completo, "rb") as w:
            duracion_total = w.getnframes() / w.getframerate()
        
        chunk_seg = 10 * 60
        n_chunks = max(1, math.ceil(duracion_total / chunk_seg))
        
        if log_callback:
            log_callback(f"Duración total: {duracion_total/60:.1f} min -> {n_chunks} fragmento(s) de 10 min", "info")

        todos_los_segmentos: list[Segmento] = []

        for i in range(n_chunks):
            if cancelar_check and cancelar_check():
                raise InterruptedError("Proceso cancelado por el usuario")
            
            inicio = i * chunk_seg
            dur = min(chunk_seg, duracion_total - inicio)
            fragmento_wav = os.path.join(tmp, f"chunk_{i:04d}.wav")

            progreso_base = 10 + (i / n_chunks) * 80
            
            if log_callback:
                log_callback(f"📦 Fragmento {i+1}/{n_chunks}: cortando audio ({inicio/60:.1f} - {(inicio+dur)/60:.1f} min)...", "info")
            
            if estado_callback:
                estado_callback(f"Cortando fragmento {i+1}/{n_chunks}")
            
            if progreso_callback:
                progreso_callback(progreso_base, f"Procesando fragmento {i+1}/{n_chunks}...", i+1, n_chunks)
            
            with wave.open(audio_completo, "rb") as origen:
                framerate = origen.getframerate()
                sampwidth = origen.getsampwidth()
                nchannels = origen.getnchannels()

                frame_inicio = int(inicio * framerate)
                n_frames = int(dur * framerate)

                origen.setpos(frame_inicio)
                datos = origen.readframes(n_frames)

            with wave.open(fragmento_wav, "wb") as destino:
                destino.setnchannels(nchannels)
                destino.setsampwidth(sampwidth)
                destino.setframerate(framerate)
                destino.writeframes(datos)

            if log_callback:
                log_callback(f"🎯 Fragmento {i+1}/{n_chunks}: transcribiendo...", "info")
            
            if estado_callback:
                estado_callback(f"Transcribiendo fragmento {i+1}/{n_chunks}")
            
            segments, info = modelo.transcribe(
                fragmento_wav,
                language=idioma,
                vad_filter=True,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
                condition_on_previous_text=True,
            )

            for seg in segments:
                todos_los_segmentos.append(
                    Segmento(
                        inicio=seg.start + inicio,
                        fin=seg.end + inicio,
                        texto=seg.text,
                    )
                )

            os.remove(fragmento_wav)
            
            if log_callback:
                log_callback(f"✅ Fragmento {i+1}/{n_chunks} completado", "success")
            
            if progreso_callback:
                progreso_callback(progreso_base + 5, f"Fragmento {i+1}/{n_chunks} completado", i+1, n_chunks)

        if log_callback:
            log_callback(f"Transcripción completa: {len(todos_los_segmentos)} segmentos.", "success")
        
        if estado_callback:
            estado_callback("Guardando archivos")
        
        if progreso_callback:
            progreso_callback(95, "Guardando archivos...")

        ruta_txt = os.path.join(salida_dir, f"{nombre_base}.txt")
        ruta_txt_tiempos = os.path.join(salida_dir, f"{nombre_base}_con_tiempos.txt")
        ruta_srt = os.path.join(salida_dir, f"{nombre_base}.srt")

        def formatear_srt_timestamp(segundos: float) -> str:
            horas = int(segundos // 3600)
            minutos = int((segundos % 3600) // 60)
            seg = int(segundos % 60)
            ms = int((segundos - int(segundos)) * 1000)
            return f"{horas:02d}:{minutos:02d}:{seg:02d},{ms:03d}"

        with open(ruta_txt, "w", encoding="utf-8") as f:
            for seg in todos_los_segmentos:
                f.write(seg.texto.strip() + " ")
            f.write("\n")

        with open(ruta_txt_tiempos, "w", encoding="utf-8") as f:
            for seg in todos_los_segmentos:
                ini = formatear_srt_timestamp(seg.inicio).replace(",", ".")
                f.write(f"[{ini}] {seg.texto.strip()}\n")

        with open(ruta_srt, "w", encoding="utf-8") as f:
            for i, seg in enumerate(todos_los_segmentos, start=1):
                f.write(f"{i}\n")
                f.write(f"{formatear_srt_timestamp(seg.inicio)} --> {formatear_srt_timestamp(seg.fin)}\n")
                f.write(seg.texto.strip() + "\n\n")

        if log_callback:
            log_callback(f"✓ Guardado: {ruta_txt}", "success")
            log_callback(f"✓ Guardado: {ruta_txt_tiempos}", "success")
            log_callback(f"✓ Guardado: {ruta_srt}", "success")
        
        if progreso_callback:
            progreso_callback(100, "Completado!")
        
        if estado_callback:
            estado_callback("Completado")

        return ruta_txt


def main():
    root = tk.Tk()
    app = TranscripcionApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()