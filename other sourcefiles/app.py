from __future__ import annotations
import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import webbrowser
import traceback

from core.config import ROOT, load_config, save_local_config
from core.media import find_ytdlp_command, is_url
from core.pipeline import run_job
from core.batch import discover_media, run_batch
from core.library import reindex, search_jobs
from core.watch import watch_folder
from core.text import OllamaTextProvider, model_advice
from core.query import TranscriptQuery

def set_windows_app_identity():
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("SS.TranscribeTranslate.Local")
    except Exception:
        pass

set_windows_app_identity()

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SS Transcribe-Translate — Free Local")
        self.geometry("1200x1020")
        self.minsize(1040, 900)
        self.source = tk.StringVar(value=os.environ.get("SS_TRANSCRIBE_SOURCE", ""))
        initial=load_config(ROOT / "config.json")
        self.ytdlp_path = tk.StringVar(value=initial.ytdlp_path)
        self.language = tk.StringVar(value=initial.language)
        self.model = tk.StringVar(value=initial.local_model)
        self.ollama_model = tk.StringVar()
        self.target = tk.StringVar(value="English")
        self.analysis_language = tk.StringVar(value="source")
        self.hotwords = tk.StringVar()
        self.search_query = tk.StringVar()
        self.top_terms = tk.IntVar(value=30)
        self.qa_question = tk.StringVar()
        self.qa_language = tk.StringVar(value="English")
        self.word_timestamps = tk.BooleanVar(value=initial.word_timestamps)
        self.translate_transcript = tk.BooleanVar(value=False)
        self.keep_media = tk.BooleanVar(value=initial.keep_media)
        self.range_mode = tk.StringVar(value=initial.range_mode)
        self.range_value = tk.DoubleVar(value=initial.range_value)
        self.analysis = tk.BooleanVar(value=initial.analysis)
        self.diarization = tk.BooleanVar(value=initial.diarization)
        self.diarization_segmentation_model = tk.StringVar(value=initial.diarization_segmentation_model)
        self.diarization_embedding_model = tk.StringVar(value=initial.diarization_embedding_model)
        self.diarization_num_speakers = tk.IntVar(value=initial.diarization_num_speakers)
        self.diarization_threshold = tk.DoubleVar(value=initial.diarization_threshold)
        self.output = tk.StringVar(value=str((ROOT / initial.output_dir).resolve() if not Path(initial.output_dir).is_absolute() else initial.output_dir))
        self.status = tk.StringVar(value="Ready — source transcript + source summary are primary; no paid API")
        self.advice = tk.StringVar(value="")
        self.performance = tk.StringVar(value="Quick")
        self.watch_stop = None
        self._build()
        self.apply_performance_profile()
        self.refresh_ollama()
        self.detect_ytdlp()
        self.detect_diarization_models()

    def _build(self):
        root = ttk.Frame(self, padding=16); root.pack(fill="both", expand=True)
        ttk.Label(root,text="SS Transcribe-Translate",font=("Segoe UI",18,"bold")).pack(anchor="w")
        ttk.Label(root,text="Local-first: source transcript + source-language summary are primary. Translation, analysis, Q&A and diarization are optional.").pack(anchor="w",pady=(0,14))

        box=ttk.LabelFrame(root,text="Input",padding=10); box.pack(fill="x")
        ttk.Label(box,text="Local audio/video file or supported media URL").grid(row=0,column=0,sticky="w")
        ttk.Entry(box,textvariable=self.source).grid(row=1,column=0,sticky="ew",padx=(0,8))
        ttk.Button(box,text="Browse…",command=self.browse).grid(row=1,column=1)
        ttk.Label(box,text="Existing yt-dlp executable (web URLs only; never modified)").grid(row=2,column=0,sticky="w",pady=(8,0))
        ttk.Entry(box,textvariable=self.ytdlp_path).grid(row=3,column=0,sticky="ew",padx=(0,8))
        ttk.Button(box,text="Browse yt-dlp…",command=self.browse_ytdlp).grid(row=3,column=1)
        box.columnconfigure(0,weight=1)

        opts=ttk.LabelFrame(root,text="Processing",padding=10); opts.pack(fill="x",pady=10)
        ttk.Label(opts,text="Performance profile").grid(row=0,column=0,sticky="w")
        ttk.Combobox(opts,textvariable=self.performance,values=["Quick","Balanced","Accuracy"],state="readonly",width=16).grid(row=0,column=1,sticky="w")
        ttk.Button(opts,text="Apply profile",command=self.apply_performance_profile).grid(row=0,column=2,sticky="w",padx=8)
        ttk.Label(opts,text="Quick: base INT8 + batched ASR, no word timing/analysis. Balanced: small INT8. Accuracy: small + timing + analysis.").grid(row=0,column=3,columnspan=2,sticky="w")
        ttk.Label(opts,text="Source language").grid(row=1,column=0,sticky="w",pady=3)
        ttk.Entry(opts,textvariable=self.language,width=16).grid(row=1,column=1,sticky="w")
        ttk.Label(opts,text="auto or Whisper ISO code").grid(row=1,column=2,sticky="w",padx=8)
        ttk.Label(opts,text="Whisper model").grid(row=2,column=0,sticky="w")
        ttk.Combobox(opts,textvariable=self.model,values=["tiny","base","small","medium","large-v3"],state="readonly",width=16).grid(row=2,column=1,sticky="w")
        ttk.Label(opts,text="Ollama model").grid(row=1,column=3,sticky="w",padx=(20,8))
        self.ollama_combo=ttk.Combobox(opts,textvariable=self.ollama_model,state="readonly",width=28)
        self.ollama_combo.grid(row=1,column=4,sticky="w")
        self.ollama_combo.bind("<<ComboboxSelected>>",lambda _e:self.update_advice())
        ttk.Button(opts,text="Refresh",command=self.refresh_ollama).grid(row=2,column=3,sticky="w",padx=(20,0))
        ttk.Label(opts,textvariable=self.advice,wraplength=360).grid(row=2,column=4,sticky="w")

        ttk.Label(opts,text="Vocabulary / names").grid(row=3,column=0,sticky="w",pady=(8,3))
        ttk.Entry(opts,textvariable=self.hotwords,width=48).grid(row=3,column=1,sticky="w",pady=(8,3))
        ttk.Label(opts,text="Names, organisations or specialist terms").grid(row=3,column=2,columnspan=3,sticky="w",padx=8,pady=(8,3))
        ttk.Checkbutton(opts,text="Keep word-level timestamps (slower)",variable=self.word_timestamps).grid(row=4,column=0,columnspan=2,sticky="w")
        ttk.Checkbutton(opts,text="Run source-grounded meeting/evidence analysis (slower)",variable=self.analysis).grid(row=5,column=0,columnspan=2,sticky="w")
        ttk.Label(opts,text="Analysis language").grid(row=5,column=2,sticky="w",padx=8)
        ttk.Entry(opts,textvariable=self.analysis_language,width=24).grid(row=5,column=3,sticky="w")

        ttk.Label(opts,text="Search transcript").grid(row=6,column=0,sticky="w")
        ttk.Entry(opts,textvariable=self.search_query,width=48).grid(row=6,column=1,sticky="w")
        ttk.Label(opts,text="Top terms").grid(row=7,column=0,sticky="w")
        ttk.Spinbox(opts,from_=5,to=200,textvariable=self.top_terms,width=8).grid(row=7,column=1,sticky="w")
        ttk.Label(opts,text="Transcript-grounded Q&A").grid(row=8,column=0,sticky="w")
        ttk.Entry(opts,textvariable=self.qa_question,width=48).grid(row=8,column=1,sticky="w")
        ttk.Label(opts,text="Q&A language").grid(row=9,column=0,sticky="w")
        ttk.Entry(opts,textvariable=self.qa_language,width=24).grid(row=9,column=1,sticky="w")
        ttk.Checkbutton(opts,text="Also translate the FULL source transcript",variable=self.translate_transcript).grid(row=10,column=0,columnspan=2,sticky="w")
        ttk.Label(opts,text="Target language").grid(row=10,column=2,sticky="w",padx=8)
        ttk.Entry(opts,textvariable=self.target,width=24).grid(row=10,column=3,sticky="w")

        diar=ttk.LabelFrame(root,text="Optional local speaker diarization — no cloud / no Torch / no WhisperX",padding=10); diar.pack(fill="x",pady=(0,10))
        ttk.Checkbutton(diar,text="Enable speaker diarization",variable=self.diarization).grid(row=0,column=0,sticky="w")
        ttk.Label(diar,text="Segmentation ONNX model").grid(row=1,column=0,sticky="w")
        ttk.Entry(diar,textvariable=self.diarization_segmentation_model,width=80).grid(row=1,column=1,columnspan=3,sticky="ew")
        ttk.Label(diar,text="Speaker embedding ONNX model").grid(row=2,column=0,sticky="w")
        ttk.Entry(diar,textvariable=self.diarization_embedding_model,width=80).grid(row=2,column=1,columnspan=3,sticky="ew")
        ttk.Label(diar,text="Known speakers (0 = automatic)").grid(row=3,column=0,sticky="w")
        ttk.Spinbox(diar,from_=0,to=50,textvariable=self.diarization_num_speakers,width=8).grid(row=3,column=1,sticky="w")
        ttk.Label(diar,text="Auto cluster threshold").grid(row=3,column=2,sticky="w")
        ttk.Spinbox(diar,from_=0.1,to=1.0,increment=0.05,textvariable=self.diarization_threshold,width=8).grid(row=3,column=3,sticky="w")
        diar.columnconfigure(1,weight=1)

        ttk.Checkbutton(opts,text="Keep source/downloaded media and extracted audio (default OFF)",variable=self.keep_media).grid(row=11,column=0,columnspan=2,sticky="w",pady=(8,0))
        ttk.Label(opts,text="Default keeps only transcript/text outputs").grid(row=11,column=2,columnspan=3,sticky="w",pady=(8,0))
        rangebox=ttk.LabelFrame(opts,text="Transcription range (from start)",padding=6); rangebox.grid(row=12,column=0,columnspan=5,sticky="ew",pady=(8,0))
        ttk.Label(rangebox,text="Take").grid(row=0,column=0,sticky="w")
        ttk.Combobox(rangebox,textvariable=self.range_mode,values=["full","minutes","percent"],state="readonly",width=12).grid(row=0,column=1,sticky="w",padx=6)
        ttk.Label(rangebox,text="Value").grid(row=0,column=2,sticky="w")
        ttk.Spinbox(rangebox,from_=0,to=100000,increment=1,textvariable=self.range_value,width=12).grid(row=0,column=3,sticky="w",padx=6)
        ttk.Label(rangebox,text="full = entire source; minutes = first N minutes; percent = first N% (e.g. 50 = first half)").grid(row=0,column=4,sticky="w")
        ttk.Label(opts,text="Output").grid(row=13,column=0,sticky="w",pady=(8,0))
        ttk.Entry(opts,textvariable=self.output).grid(row=13,column=1,columnspan=4,sticky="ew",pady=(8,0))
        opts.columnconfigure(4,weight=1)

        actions=ttk.Frame(root); actions.pack(fill="x",pady=8)
        ttk.Button(actions,text="START",command=self.start).pack(side="left")
        ttk.Button(actions,text="Batch folder…",command=self.batch_folder).pack(side="left",padx=8)
        ttk.Button(actions,text="Library…",command=self.library).pack(side="left")
        ttk.Button(actions,text="Watch folder…",command=self.start_watch).pack(side="left",padx=8)
        ttk.Button(actions,text="Stop watch",command=self.stop_watch).pack(side="left")
        ttk.Button(actions,text="Open output folder",command=self.open_output).pack(side="left",padx=8)
        ttk.Label(actions,textvariable=self.status).pack(side="right")
        logbox=ttk.LabelFrame(root,text="Progress / errors",padding=8); logbox.pack(fill="both",expand=True)
        toolbar=ttk.Frame(logbox); toolbar.pack(fill="x",pady=(0,6))
        ttk.Button(toolbar,text="Copy log",command=self.copy_log).pack(side="left")
        ttk.Button(toolbar,text="Save log…",command=self.save_log).pack(side="left",padx=6)
        ttk.Button(toolbar,text="Clear",command=self.clear_log).pack(side="left")
        self.log=tk.Text(logbox,wrap="word",font=("Consolas",10),undo=False)
        self.log.pack(fill="both",expand=True)
        self.log.bind("<Control-a>",lambda _e:self.select_all_log())
        self.log.bind("<Button-3>",self.show_log_menu)
        self.log_menu=tk.Menu(self.log,tearoff=0)
        self.log_menu.add_command(label="Copy",command=self.copy_log)
        self.log_menu.add_command(label="Select all",command=self.select_all_log)
        self.log_menu.add_separator()
        self.log_menu.add_command(label="Save log…",command=self.save_log)

    def select_all_log(self):
        self.log.tag_add("sel","1.0","end-1c")
        self.log.mark_set("insert","1.0")
        self.log.see("1.0")
        return "break"

    def copy_log(self):
        try:
            text=self.log.get("sel.first","sel.last")
        except tk.TclError:
            text=self.log.get("1.0","end-1c")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.status.set(f"Copied {len(text)} characters")

    def clear_log(self):
        self.log.delete("1.0","end")

    def save_log(self):
        path=filedialog.asksaveasfilename(title="Save processing log",defaultextension=".txt",
            filetypes=[("Text files","*.txt"),("All files","*.*")])
        if path:
            Path(path).write_text(self.log.get("1.0","end-1c"),encoding="utf-8")
            self.status.set("Log saved: "+path)

    def show_log_menu(self,event):
        self.log_menu.tk_popup(event.x_root,event.y_root)

    def combo(self,parent,label,var,values,row,column):
        ttk.Label(parent,text=label).grid(row=row,column=column,sticky="w",pady=3)
        ttk.Combobox(parent,textvariable=var,values=values,state="readonly",width=24).grid(row=row,column=column+1,sticky="w",pady=3)

    def apply_performance_profile(self):
        profile=self.performance.get()
        if profile=="Quick":
            self.model.set("base")
            self.word_timestamps.set(False)
            self.analysis.set(False)
            self.diarization.set(False)
        elif profile=="Balanced":
            self.model.set("small")
            self.word_timestamps.set(False)
            self.analysis.set(False)
            self.diarization.set(False)
        else:
            self.model.set("small")
            self.word_timestamps.set(True)
            self.analysis.set(True)
        self.status.set(f"Profile: {profile} — model={self.model.get()}, word timestamps={'ON' if self.word_timestamps.get() else 'OFF'}, analysis={'ON' if self.analysis.get() else 'OFF'}")

    def refresh_ollama(self):
        def worker():
            try:
                models=OllamaTextProvider(load_config().ollama_url,"",self.logmsg).list_models()
                self.after(0,lambda:self.set_models(models))
            except Exception as exc: self.logmsg("Ollama model discovery failed: "+str(exc))
        threading.Thread(target=worker,daemon=True).start()

    def set_models(self,models):
        self.ollama_combo["values"]=models
        configured=load_config().ollama_model
        preferred=["qwen3:1.7b","gemma3:1b","llama3.2:1b","phi4-mini:3.8b"]
        if configured in models: self.ollama_model.set(configured)
        else:
            choice=next((m for m in preferred if m in models), None)
            self.ollama_model.set(choice or (models[0] if models else ""))
        self.update_advice(); self.logmsg(f"Ollama models available: {', '.join(models) if models else 'none'}")

    def update_advice(self):
        tier,note=model_advice(self.ollama_model.get()); self.advice.set(f"{tier.upper()}: {note}")

    def browse(self):
        path=filedialog.askopenfilename(title="Choose media",filetypes=[("Media","*.mp4 *.mkv *.mov *.avi *.webm *.m4v *.mp3 *.m4a *.wav *.flac *.ogg"),("All files","*.*")])
        if path: self.source.set(path)

    def browse_ytdlp(self):
        path=filedialog.askopenfilename(
            title="Select your existing standalone yt-dlp.exe",
            filetypes=[("yt-dlp executable","yt-dlp.exe"),("Executable","*.exe"),("All files","*.*")]
        )
        if path:
            self.ytdlp_path.set(path)
            self.logmsg("Using existing yt-dlp: " + path)

    def detect_ytdlp(self):
        try:
            command=find_ytdlp_command(self.ytdlp_path.get().strip(), self.logmsg)
            if len(command) == 1:
                self.ytdlp_path.set(command[0])
                self.logmsg("yt-dlp found: " + command[0])
            else:
                self.ytdlp_path.set("Python package (existing local yt-dlp)")
            return command
        except FileNotFoundError:
            self.logmsg("No yt-dlp executable/package was found automatically.")
            return []

    def detect_diarization_models(self):
        seg=ROOT/"models"/"diarization"/"sherpa-onnx-pyannote-segmentation-3-0"/"model.onnx"
        emb=ROOT/"models"/"diarization"/"3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
        if seg.is_file(): self.diarization_segmentation_model.set(str(seg))
        if emb.is_file(): self.diarization_embedding_model.set(str(emb))
        if seg.is_file() and emb.is_file(): self.logmsg("Local diarization models detected.")

    def start_watch(self):
        folder=filedialog.askdirectory(title="Choose watch folder")
        if not folder: return
        import threading as _threading
        model=self.ollama_model.get().strip()
        if not model: messagebox.showerror("Ollama required","No Ollama model is available."); return
        cfg=load_config(ROOT/"config.json")
        cfg.language=self.language.get().strip() or "auto"; cfg.local_model=self.model.get(); cfg.ollama_model=model
        cfg.hotwords=self.hotwords.get().strip(); cfg.word_timestamps=self.word_timestamps.get()
        cfg.analysis=self.analysis.get(); cfg.analysis_language=self.analysis_language.get().strip() or "source"
        cfg.search_query=self.search_query.get().strip(); cfg.top_terms=max(5,int(self.top_terms.get()))
        cfg.qa_question=self.qa_question.get().strip(); cfg.qa_language=self.qa_language.get().strip() or "English"
        cfg.target_language=self.target.get().strip() or "English"; cfg.translate_transcript=self.translate_transcript.get()
        cfg.diarization=self.diarization.get(); cfg.diarization_segmentation_model=self.diarization_segmentation_model.get().strip()
        cfg.diarization_embedding_model=self.diarization_embedding_model.get().strip(); cfg.diarization_num_speakers=max(0,int(self.diarization_num_speakers.get())); cfg.diarization_threshold=float(self.diarization_threshold.get())
        cfg.range_mode=self.range_mode.get().strip() or "full"; cfg.range_value=max(0.0,float(self.range_value.get()))
        self.stop_watch(); self.watch_stop=_threading.Event()
        threading.Thread(target=watch_folder,args=(Path(folder),cfg,Path(self.output.get()),self.watch_stop,self.logmsg),daemon=True).start()
        self.logmsg("Watch started: "+folder)
    def stop_watch(self):
        if self.watch_stop: self.watch_stop.set(); self.watch_stop=None; self.logmsg("Watch stopped.")
    
    def batch_folder(self):
        folder=filedialog.askdirectory(title="Choose folder containing media to transcribe")
        if not folder: return
        model=self.ollama_model.get().strip()
        if not model:
            messagebox.showerror("Ollama required","No Ollama model is available."); return
        sources=discover_media(Path(folder))
        if not sources:
            messagebox.showinfo("No media","No supported audio/video files were found."); return
        cfg=load_config(ROOT/"config.json")
        cfg.language=self.language.get().strip() or "auto"; cfg.local_model=self.model.get(); cfg.ollama_model=model
        cfg.hotwords=self.hotwords.get().strip(); cfg.word_timestamps=self.word_timestamps.get()
        cfg.analysis=self.analysis.get(); cfg.analysis_language=self.analysis_language.get().strip() or "source"
        cfg.search_query=self.search_query.get().strip(); cfg.top_terms=max(5,int(self.top_terms.get()))
        cfg.qa_question=self.qa_question.get().strip(); cfg.qa_language=self.qa_language.get().strip() or "English"
        cfg.target_language=self.target.get().strip() or "English"; cfg.translate_transcript=self.translate_transcript.get()
        cfg.diarization=self.diarization.get(); cfg.diarization_segmentation_model=self.diarization_segmentation_model.get().strip()
        cfg.diarization_embedding_model=self.diarization_embedding_model.get().strip(); cfg.diarization_num_speakers=max(0,int(self.diarization_num_speakers.get())); cfg.diarization_threshold=float(self.diarization_threshold.get())
        cfg.range_mode=self.range_mode.get().strip() or "full"; cfg.range_value=max(0.0,float(self.range_value.get()))
        self.status.set(f"Batch: {len(sources)} files")
        threading.Thread(target=lambda: self.batch_worker(sources,cfg),daemon=True).start()

    def batch_worker(self,sources,cfg):
        results=run_batch(sources,cfg,Path(self.output.get()),self.logmsg)
        self.logmsg(f"BATCH COMPLETE: {len(results)}/{len(sources)} succeeded")
        self.after(0,lambda:messagebox.showinfo("Batch complete",f"{len(results)} of {len(sources)} jobs completed."))

    def library(self):
        root=Path(self.output.get()); root.mkdir(parents=True,exist_ok=True); reindex(root)
        win=tk.Toplevel(self); win.title("SS Transcribe-Translate — Local Library"); win.geometry("1000x600")
        top=ttk.Frame(win,padding=10); top.pack(fill="x")
        q=tk.StringVar(); ttk.Entry(top,textvariable=q,width=70).pack(side="left",fill="x",expand=True)
        tree=ttk.Treeview(win,columns=("created","source","language","duration","speakers"),show="headings")
        for col,w in (("created",150),("source",500),("language",100),("duration",90),("speakers",80)):
            tree.heading(col,text=col.title()); tree.column(col,width=w)
        tree.pack(fill="both",expand=True,padx=10,pady=10)
        def refresh():
            for item in tree.get_children(): tree.delete(item)
            for row in search_jobs(root,q.get()):
                tree.insert("", "end", iid=row["job_dir"], values=(row["created"],row["source"],row["language"],f'{row["duration"]:.1f}s',row["speakers"]))
        ttk.Button(top,text="Search",command=refresh).pack(side="left",padx=8)
        def open_selected():
            sel=tree.selection()
            if not sel: return
            player=Path(sel[0])/"player.html"
            if player.exists(): webbrowser.open(player.as_uri())
            else: messagebox.showerror("Player missing","This job has no player.html.")
        ttk.Button(top,text="Open transcript workspace",command=lambda:self.open_workspace(Path(tree.selection()[0])) if tree.selection() else None).pack(side="left",padx=8)
        ttk.Button(top,text="Open synchronized player",command=open_selected).pack(side="left")
        refresh()

    def open_workspace(self, job_dir: Path):
        if not job_dir.exists():
            messagebox.showerror("Job missing", str(job_dir)); return
        def read(name):
            p=job_dir/name
            return p.read_text(encoding="utf-8") if p.exists() else "(not generated)"
        transcript=read("transcript.md"); summary=read("source_summary.md"); analysis=read("analysis.md")
        win=tk.Toplevel(self); win.title("SS Transcript Workspace — "+job_dir.name); win.geometry("1180x800")
        top=ttk.Frame(win,padding=10); top.pack(fill="both",expand=True)
        bar=ttk.Frame(top); bar.pack(fill="x")
        provider=tk.StringVar(value="Ollama"); openai_model=tk.StringVar(value=os.environ.get("OPENAI_MODEL","gpt-5.6-luna"))
        question=tk.StringVar(); answer_lang=tk.StringVar(value="English")
        ttk.Label(bar,text="Query provider").pack(side="left")
        ttk.Combobox(bar,textvariable=provider,values=["Ollama","OpenAI"],state="readonly",width=12).pack(side="left",padx=6)
        ttk.Label(bar,text="OpenAI model").pack(side="left",padx=(16,4)); ttk.Entry(bar,textvariable=openai_model,width=22).pack(side="left")
        ttk.Label(bar,text="Answer language").pack(side="left",padx=(16,4)); ttk.Entry(bar,textvariable=answer_lang,width=16).pack(side="left")
        ttk.Label(bar,text="Question").pack(side="left",padx=(16,4)); ttk.Entry(bar,textvariable=question,width=38).pack(side="left",fill="x",expand=True)
        tabs=ttk.Notebook(top); tabs.pack(fill="both",expand=True,pady=8)
        texts={}
        for title,data in [("Transcript",transcript),("Source summary",summary),("Analysis",analysis),("Query answer","")]:
            frame=ttk.Frame(tabs); tabs.add(frame,text=title)
            txt=tk.Text(frame,wrap="word",font=("Segoe UI",10)); txt.pack(fill="both",expand=True)
            txt.insert("1.0",data); txt.config(state="disabled"); texts[title]=txt
        def do_query():
            q=question.get().strip()
            if not q: messagebox.showerror("Question required","Enter a question about this recording."); return
            context=read("transcript.md")
            def worker():
                try:
                    engine=TranscriptQuery(load_config().ollama_url,self.ollama_model.get().strip(),self.logmsg)
                    if provider.get()=="OpenAI":
                        ans=engine.ask_openai(context,q,answer_lang.get().strip() or "English",openai_model.get().strip() or "gpt-5.6-luna")
                    else:
                        ans=engine.ask_ollama(context,q,answer_lang.get().strip() or "English")
                    def show():
                        t=texts["Query answer"]; t.config(state="normal"); t.delete("1.0","end"); t.insert("1.0",ans); t.config(state="disabled"); tabs.select(3)
                    win.after(0,show)
                except Exception as exc:
                    self.logmsg("QUERY ERROR: "+str(exc)); win.after(0,lambda:messagebox.showerror("Query failed",str(exc)))
            threading.Thread(target=worker,daemon=True).start()
        ttk.Button(bar,text="Ask",command=do_query).pack(side="left",padx=8)
        ttk.Button(bar,text="Open job folder",command=lambda:os.startfile(job_dir)).pack(side="left")
        ttk.Label(top,text="All generated files remain in the job folder. Querying is transcript-grounded; OpenAI is optional and never used automatically.",wraplength=1100).pack(anchor="w")

    def logmsg(self,msg):
        self.after(0,lambda:(self.log.insert("end",msg+"\n"),self.log.see("end"),self.status.set(msg[:150])))

    def start(self):
        source=self.source.get().strip(); model=self.ollama_model.get().strip()
        if not source: messagebox.showerror("Input required","Choose a local audio/video file or paste a supported media URL."); return
        if not model: messagebox.showerror("Ollama required","No Ollama model is available. Start Ollama and click Refresh models."); return
        cfg=load_config(ROOT/"config.json")
        cfg.language=self.language.get().strip() or "auto"; cfg.local_model=self.model.get(); cfg.ollama_model=model
        cfg.ytdlp_path=self.ytdlp_path.get().strip()
        cfg.keep_media=self.keep_media.get()
        if is_url(source):
            command = self.detect_ytdlp()
            if not command:
                path=filedialog.askopenfilename(
                    title="Select your existing standalone yt-dlp.exe",
                    filetypes=[("yt-dlp executable","yt-dlp.exe"),("Executable","*.exe"),("All files","*.*")]
                )
                if not path:
                    messagebox.showerror("yt-dlp required","No existing yt-dlp executable or Python package was found. Select your existing standalone yt-dlp.exe; the app will not install or modify it.")
                    return
                self.ytdlp_path.set(path)
            cfg.ytdlp_path=self.ytdlp_path.get().strip()
        cfg.hotwords=self.hotwords.get().strip(); cfg.word_timestamps=self.word_timestamps.get()
        cfg.analysis_language=self.analysis_language.get().strip() or "source"
        cfg.search_query=self.search_query.get().strip(); cfg.top_terms=max(5,int(self.top_terms.get()))
        cfg.qa_question=self.qa_question.get().strip(); cfg.qa_language=self.qa_language.get().strip() or "English"
        cfg.target_language=self.target.get().strip() or "English"; cfg.translate_transcript=self.translate_transcript.get(); cfg.analysis=self.analysis.get()
        cfg.diarization=self.diarization.get(); cfg.diarization_segmentation_model=self.diarization_segmentation_model.get().strip()
        cfg.diarization_embedding_model=self.diarization_embedding_model.get().strip(); cfg.diarization_num_speakers=max(0,int(self.diarization_num_speakers.get()))
        cfg.diarization_threshold=float(self.diarization_threshold.get())
        cfg.range_mode=self.range_mode.get().strip() or "full"; cfg.range_value=max(0.0,float(self.range_value.get()))
        cfg.output_dir=self.output.get().strip() or str(ROOT / "output")
        save_local_config(cfg)
        if cfg.diarization and (not cfg.diarization_segmentation_model or not cfg.diarization_embedding_model):
            messagebox.showerror("Diarization models required","Provide both local ONNX model paths before enabling diarization."); return
        self.status.set("Running locally…"); threading.Thread(target=self.worker,args=(source,cfg),daemon=True).start()

    def worker(self,source,cfg):
        try:
            output=run_job(source,cfg,Path(self.output.get()),self.logmsg)
            self.after(0,lambda:messagebox.showinfo("Complete",f"Job finished:\n{output}"))
        except Exception as exc:
            self.logmsg("ERROR: "+str(exc)); self.after(0,lambda:messagebox.showerror("Processing failed",str(exc))); self.after(0,lambda:self.status.set("Failed"))

    def open_output(self):
        import os
        path=Path(self.output.get()); path.mkdir(parents=True,exist_ok=True); os.startfile(path)

if __name__=="__main__":
    try:
        App().mainloop()
    except Exception:
        logdir=ROOT/"logs"; logdir.mkdir(parents=True,exist_ok=True)
        (logdir/"app-crash.log").write_text(traceback.format_exc(),encoding="utf-8")
        try:
            messagebox.showerror("SS Transcribe-Translate failed",
                "The application failed during startup.\n\n"
                "Full traceback saved to:\n"+str(logdir/"app-crash.log"))
        except Exception:
            pass
        raise
