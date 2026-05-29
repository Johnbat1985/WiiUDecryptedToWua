import os
import sys
import json
import queue
import shutil
import threading
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from collections import defaultdict

SETTINGS_FILE = Path(__file__).with_name('wua_generator_settings.json')

class UltimateWuaHybridEngine:
    def __init__(self, root):
        self.root = root
        self.root.title("Official ZArchive + Zstd Hybrid .wua Builder")
        self.root.geometry("900x620")
        self.root.minsize(800, 500)

        self.library_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.zarchive_path = tk.StringVar(value="./zarchive.exe")
        self.catalog = {}
        self._item_ids = {}
        self.ui_queue = queue.Queue()

        self.load_settings()
        self.setup_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def load_settings(self):
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            if data.get('library_dir'):   self.library_dir.set(data['library_dir'])
            if data.get('output_dir'):    self.output_dir.set(data['output_dir'])
            if data.get('zarchive_path'): self.zarchive_path.set(data['zarchive_path'])
        except Exception:
            pass

    def save_settings(self):
        try:
            SETTINGS_FILE.write_text(json.dumps({
                'library_dir':   self.library_dir.get(),
                'output_dir':    self.output_dir.get(),
                'zarchive_path': self.zarchive_path.get(),
            }, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _on_close(self):
        self.save_settings()
        self.root.destroy()

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main_frame, text="Source Library (Unpacked Folders):", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=2)
        f1 = ttk.Frame(main_frame)
        f1.pack(fill=tk.X, pady=(0,10))
        lib_entry = ttk.Entry(f1, textvariable=self.library_dir)
        lib_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        lib_entry.bind('<Return>', lambda e: self.start_scan_thread())
        lib_entry.bind('<FocusOut>', lambda e: self.start_scan_thread())
        ttk.Button(f1, text="Browse...", command=self.browse_input).pack(side=tk.RIGHT)

        ttk.Label(main_frame, text="Destination Directory (Output .wua):", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=2)
        f2 = ttk.Frame(main_frame)
        f2.pack(fill=tk.X, pady=(0,10))
        out_entry = ttk.Entry(f2, textvariable=self.output_dir)
        out_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        out_entry.bind('<Return>', lambda e: self.start_scan_thread())
        out_entry.bind('<FocusOut>', lambda e: self.start_scan_thread())
        ttk.Button(f2, text="Browse...", command=self.browse_output).pack(side=tk.RIGHT)

        ttk.Label(main_frame, text="Path to compiled zarchive.exe:", font=("Helvetica", 10, "bold")).pack(anchor="w", pady=2)
        f_exe = ttk.Frame(main_frame)
        f_exe.pack(fill=tk.X, pady=(0,15))
        ttk.Entry(f_exe, textvariable=self.zarchive_path).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0,5))
        ttk.Button(f_exe, text="Locate...", command=self.browse_zarchive).pack(side=tk.RIGHT)

        f3 = ttk.Frame(main_frame)
        f3.pack(fill=tk.X, pady=(0,10))
        self.scan_btn = ttk.Button(f3, text="🔍 Deep Audit Folders", command=self.start_scan_thread)
        self.scan_btn.pack(side=tk.LEFT, padx=(0,10))
        self.start_btn = ttk.Button(f3, text="⚡ Compile Playable .WUA Archives", command=self.start_process_thread, state=tk.DISABLED)
        self.start_btn.pack(side=tk.LEFT)

        columns = ('name', 'path', 'wua_status')
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0,10))
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.heading('name', text='Game Identifier')
        self.tree.heading('path', text='Folder Location')
        self.tree.heading('wua_status', text='Compiler Validation')
        self.tree.column('name', width=200)
        self.tree.column('path', width=450)
        self.tree.column('wua_status', width=150, anchor=tk.CENTER)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.tag_configure('ready', background='#e2f0d9')
        self.tree.tag_configure('completed', background='#c6e0b4')

        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.pack(fill=tk.X, pady=(0,5))

        self.status_label = ttk.Label(main_frame, text="Ready.", font=("Helvetica", 9, "italic"))
        self.status_label.pack(anchor="w")

        self.root.after(50, self.process_ui_queue)

    def parse_meta_xml(self, meta_path):
        try:
            if not meta_path.exists(): return None, None
            root = ET.parse(meta_path).getroot()
            t_id = root.find('title_id')
            v_num = root.find('title_version')
            return (t_id.text.strip().lower() if t_id is not None else None,
                    v_num.text.strip() if v_num is not None else "0")
        except:
            return None, None

    def browse_input(self):
        f = filedialog.askdirectory()
        if f: self.library_dir.set(os.path.normpath(f)); self.save_settings(); self.start_scan_thread()

    def browse_output(self):
        f = filedialog.askdirectory()
        if f: self.output_dir.set(os.path.normpath(f)); self.save_settings(); self.start_scan_thread()

    def browse_zarchive(self):
        f = filedialog.askopenfilename(filetypes=[("Executable Files", "*.exe")])
        if f: self.zarchive_path.set(os.path.normpath(f)); self.save_settings()

    def start_scan_thread(self):
        if not self.library_dir.get():
            self.status_label.config(text="Select a source library folder first.")
            return
        self.scan_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        for i in self.tree.get_children(): self.tree.delete(i)
        self.catalog = {}
        self._item_ids = {}
        self.status_label.config(text="Scanning...")
        self.progress.configure(mode='indeterminate')
        self.progress.start(10)
        threading.Thread(target=self.scan_worker, daemon=True).start()

    def scan_worker(self):
        base = self.library_dir.get()
        out = Path(self.output_dir.get()) if self.output_dir.get() else None
        found = set()
        TYPE_MAP = {"00050000": "Base", "0005000e": "Update", "0005000c": "DLC"}

        for r, dirs, files in os.walk(base, topdown=True):
            rp = Path(r)
            if rp.name in ["code", "content", "meta"]:
                dirs[:] = []  # don't descend into game content
                g_root = rp.parent
            elif "meta.xml" in files:
                dirs[:] = []
                g_root = rp
            else:
                continue

            grs = str(g_root.resolve())
            if grs in found:
                continue
            found.add(grs)

            t_id, ver = self.parse_meta_xml(g_root / "meta" / "meta.xml")
            prefix    = t_id[:8] if t_id else ""
            unique_id = t_id[8:] if t_id else ""
            info = {
                "base": grs, "name": g_root.name,
                "title_id": t_id, "version": ver,
                "title_type": TYPE_MAP.get(prefix, "Other"),
                "unique_id": unique_id,
                "wua_exists": False,
            }
            self.catalog[grs] = info
            self.ui_queue.put(("ROW", info))
            self.ui_queue.put(("SCAN_STATUS", "Scanning... found " + str(len(found)) + " folder(s)"))

        # Deferred pass: group by unique_id, check wua_exists per group
        groups = defaultdict(list)
        for info in self.catalog.values():
            if info["title_id"]:
                groups[info["unique_id"]].append(info)

        wua_updates = []
        for members in groups.values():
            base_entry = next((m for m in members if m["title_type"] == "Base"), members[0])
            cn = "".join(c for c in base_entry["name"] if c.isalnum() or c in " _-").rstrip()
            wua_exists = bool(out and out.exists() and (out / (cn + ".wua")).exists())
            for m in members:
                m["wua_exists"] = wua_exists
                if wua_exists:
                    wua_updates.append(m["base"])

        if wua_updates:
            self.ui_queue.put(("UPDATE_WUA", wua_updates))
        self.ui_queue.put(("SCAN_DONE", None))

    def process_ui_queue(self):
        try:
            while True:
                m_type, data = self.ui_queue.get_nowait()
                if m_type == "ROW":
                    txt = ("⏳ " + data.get("title_type", "") + " - Ready") if data["title_id"] else "❌ Bad Metadata"
                    iid = self.tree.insert('', tk.END, values=(data["name"], data["base"], txt), tags=('ready',))
                    self._item_ids[data["base"]] = iid
                elif m_type == "UPDATE_WUA":
                    for grs in data:
                        iid = self._item_ids.get(grs)
                        if iid:
                            self.tree.item(iid,
                                values=(self.catalog[grs]["name"], grs, "✓ Active (.WUA)"),
                                tags=('completed',))
                elif m_type == "SCAN_STATUS":
                    self.status_label.config(text=data)
                elif m_type == "SCAN_DONE":
                    self.progress.stop()
                    self.progress.configure(mode='determinate', value=0)
                    self.scan_btn.config(state=tk.NORMAL)
                    if any(not v["wua_exists"] and v["title_id"] for v in self.catalog.values()) and self.output_dir.get():
                        self.start_btn.config(state=tk.NORMAL)
                    self.status_label.config(text="Scan finalized. Library tracking contains " + str(len(self.catalog)) + " folders.")
                self.ui_queue.task_done()
        except queue.Empty:
            pass
        finally:
            self.root.after(50, self.process_ui_queue)

    def start_process_thread(self):
        exe_p = Path(self.zarchive_path.get())
        if not exe_p.exists():
            messagebox.showerror("Missing Compiler",
                "Could not find 'zarchive.exe' at:\n" + str(exe_p.resolve()) +
                "\n\nPlease make sure it is compiled or located correctly.")
            return
        self.start_btn.config(state=tk.DISABLED)
        self.scan_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.batch_process_worker, daemon=True).start()

    def batch_process_worker(self):
        out_path = Path(self.output_dir.get())

        # Group pending titles by unique game ID (lower 8 hex chars of title_id)
        groups = defaultdict(list)
        for v in self.catalog.values():
            if not v["wua_exists"] and v["title_id"]:
                groups[v["unique_id"]].append(v)
        group_list = list(groups.values())

        self.root.after(0, lambda: self.progress.configure(mode='determinate', maximum=len(group_list), value=0))

        for idx, members in enumerate(group_list):
            base_entry = next((m for m in members if m["title_type"] == "Base"), members[0])
            cn = "".join(c for c in base_entry["name"] if c.isalnum() or c in " _-").rstrip()
            target_file = out_path / (cn + ".wua")
            extras = [m["title_type"] for m in members if m is not base_entry]
            label = cn + ((" + " + " + ".join(extras)) if extras else "")

            self.root.after(0, lambda n=label, i=idx, total=len(group_list):
                self.status_label.config(text="Processing [" + str(i+1) + "/" + str(total) + "]: " + n + "..."))

            try:
                self.compile_hybrid_archive(members, target_file)
            except Exception as e:
                self.root.after(0, lambda ex=str(e): messagebox.showerror(
                    "Processing Error", "Failed compilation pipeline:\n" + ex))

            self.root.after(0, lambda v=idx+1: self.progress.configure(value=v))

        self.root.after(0, self.start_scan_thread)
        self.root.after(0, lambda: messagebox.showinfo("Success", "All eligible archives compiled successfully!"))

    def compile_hybrid_archive(self, infos, target_wua):
        temp_sandbox = Path("./wua_sandbox_temp")
        temp_zar_output = Path("./temp_archive.zar")

        try:
            if temp_sandbox.exists(): shutil.rmtree(temp_sandbox)
            if temp_zar_output.exists(): os.remove(temp_zar_output)

            # Stage each title under its own <titleId>_v<version>/ subdirectory
            for info in infos:
                subdir = temp_sandbox / (info["title_id"] + "_v" + info["version"])
                subdir.mkdir(parents=True, exist_ok=True)
                for folder in ["code", "content", "meta"]:
                    src_folder = Path(info["base"]) / folder
                    if src_folder.exists():
                        shutil.copytree(src_folder, subdir / folder)

            exe_cmd = [str(Path(self.zarchive_path.get()).resolve()),
                       str(temp_sandbox.resolve()), str(temp_zar_output.resolve())]
            c_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

            result = subprocess.run(exe_cmd, capture_output=True, text=True, creationflags=c_flags)
            if result.returncode != 0:
                raise RuntimeError("zarchive.exe failed (code %d): %s" % (result.returncode, result.stderr.strip()))
            if not temp_zar_output.exists() or temp_zar_output.stat().st_size == 0:
                raise RuntimeError("zarchive.exe produced no output.")

            # WUA is a plain ZArchive file - zarchive.exe already uses ZSTD internally.
            shutil.copy2(temp_zar_output, target_wua)

        finally:
            if temp_sandbox.exists(): shutil.rmtree(temp_sandbox)
            if temp_zar_output.exists(): os.remove(temp_zar_output)

if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateWuaHybridEngine(root)
    root.mainloop()
