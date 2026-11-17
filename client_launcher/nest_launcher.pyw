"""The Nest Vanilla Edition — Standalone GitHub Auto-Updating Client Launcher."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import ctypes
import hashlib
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import urllib.parse
import urllib.request
import uuid
import zipfile

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("TheNest.VanillaEdition.ClientLauncher")
except Exception:
    pass

RESOURCE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(RESOURCE_DIR, "launcher_config.json")

DEFAULT_INSTALL_ROOT = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "TheNestVanilla")
STATE_DIR = DEFAULT_INSTALL_ROOT
STATE_PATH = os.path.join(STATE_DIR, "launcher_state.json")

CF_INSTALL_DIR = r"C:\Users\katen\curseforge\minecraft\Install"
CF_JAVA_25 = os.path.join(CF_INSTALL_DIR, "java", "java-runtime-epsilon", "bin", "javaw.exe")

MOJANG_PROFILE_URL = "https://api.mojang.com/users/profiles/minecraft/{name}"
HEAD_AVATAR_URL = "https://mc-heads.net/avatar/{ident}/36"
MC_VERSION_MANIFEST = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
NEOFORGE_INSTALLER_URL = (
    "https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/neoforge-{ver}-installer.jar"
)
ADOPTIUM_JRE25_API = (
    "https://api.adoptium.net/v3/binary/latest/25/ga/windows/x64/jre/hotspot/normal/eclipse"
)

RE_VALID_NICK = re.compile(r"^[A-Za-z0-9_]{3,16}$")

# Warm Espresso-Brown & Nest Gold Theme
BG = "#16110d"
SURFACE = "#211913"
SURFACE_ALT = "#2c2219"
INPUT_BG = "#100c09"
BORDER = "#3b2d21"
TEXT = "#f5ece0"
MUTED = "#a89682"
ACCENT = "#e09f3e"
GOLD_BTN = "#c88628"
GOLD_HOVER = "#df9a36"
GOLD_FG = "#16110d"
OK_GREEN = "#6bc482"
ERR_RED = "#e06c60"


def apply_dark_titlebar(window: tk.Misc) -> None:
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        val = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
    except Exception:
        pass


def load_json(path: str, default: dict) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return dict(default)


def save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def http_get_bytes(url: str, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "TheNestLauncher/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download_file(url: str, dest: str, expected_sha256: str | None = None) -> None:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    req = urllib.request.Request(url, headers={"User-Agent": "TheNestLauncher/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp, open(tmp, "wb") as out:
        shutil.copyfileobj(resp, out, 1024 * 128)
    if expected_sha256 and sha256_file(tmp) != expected_sha256:
        os.remove(tmp)
        raise ValueError(f"Checksum mismatch for {os.path.basename(dest)}")
    os.replace(tmp, dest)


def offline_uuid_for_nick(nick: str) -> str:
    raw = bytearray(hashlib.md5(f"OfflinePlayer:{nick}".encode("utf-8")).digest())
    raw[6] = (raw[6] & 0x0F) | 0x30
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw)).hex


def fetch_mojang_profile(nick: str) -> tuple[str, str, bool]:
    """Fetch official Mojang UUID for skin/account matching; fallback to offline UUID."""
    clean = nick.strip()
    if not clean:
        return "", "", False
    try:
        url = MOJANG_PROFILE_URL.format(name=urllib.parse.quote(clean))
        data = json.loads(http_get_bytes(url, timeout=8).decode("utf-8"))
        return data.get("name", clean), data["id"], True
    except Exception:
        return clean, offline_uuid_for_nick(clean), False


def make_button(parent: tk.Misc, text: str, bg: str, hover: str, fg: str, cmd, padx: int = 12, pady: int = 6, size: int = 9) -> tk.Button:
    btn = tk.Button(
        parent,
        text=text,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=fg,
        font=("Segoe UI", size, "bold"),
        bd=0,
        relief="flat",
        padx=padx,
        pady=pady,
        cursor="hand2",
        command=cmd,
    )
    btn.bind("<Enter>", lambda _e: btn.configure(bg=hover))
    btn.bind("<Leave>", lambda _e: btn.configure(bg=bg))
    return btn


class NestLauncher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.cfg = load_json(
            CONFIG_PATH,
            {
                "pack_name": "The Nest Vanilla Edition",
                "pack_version": "1.0.0",
                "mc_version": "26.3",
                "neoforge_version": "26.3.0.103",
                "asset_index": "34",
                "manifest_url": "",
                "files_base_url": "",
                "default_ram_gb": 8,
            },
        )
        self.state = load_json(
            STATE_PATH,
            {
                "nick": "",
                "uuid": "",
                "ram_gb": self.cfg.get("default_ram_gb", 8),
                "install_root": DEFAULT_INSTALL_ROOT,
            },
        )
        if not self.state.get("install_root"):
            self.state["install_root"] = DEFAULT_INSTALL_ROOT

        self.busy = False
        self.ui_queue: queue.Queue = queue.Queue()
        self._icons: list[tk.PhotoImage] = []
        self._avatar_img: tk.PhotoImage | None = None
        self._debounce_id: str | None = None
        self._lookup_seq = 0
        self._last_looked_up = ""

        self.root.title(self.cfg.get("pack_name", "The Nest Vanilla Edition"))
        dpi_scale = max(1.0, self.root.winfo_fpixels("1i") / 96.0)
        self.root.geometry(f"{int(520 * dpi_scale)}x{int(430 * dpi_scale)}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self._setup_styles()
        self._load_icons()
        self._build_ui()
        apply_dark_titlebar(self.root)
        self._poll_ui_queue()

        initial_nick = (self.state.get("nick") or "").strip()
        if RE_VALID_NICK.match(initial_nick):
            self._trigger_lookup(initial_nick)

    @property
    def install_root(self) -> str:
        return self.state["install_root"]

    @property
    def game_dir(self) -> str:
        return os.path.join(self.install_root, "instance")

    @property
    def runtime_dir(self) -> str:
        return os.path.join(self.install_root, "mc_install")

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Nest.Horizontal.TProgressbar",
            troughcolor=INPUT_BG,
            background=ACCENT,
            bordercolor=BORDER,
            lightcolor=ACCENT,
            darkcolor=GOLD_BTN,
            thickness=6,
        )
        style.configure(
            "Nest.TCombobox",
            fieldbackground=INPUT_BG,
            background=SURFACE_ALT,
            foreground=TEXT,
            bordercolor=BORDER,
            arrowcolor=ACCENT,
            padding=4,
        )
        style.map(
            "Nest.TCombobox",
            fieldbackground=[("readonly", INPUT_BG)],
            selectbackground=[("readonly", SURFACE_ALT)],
            selectforeground=[("readonly", TEXT)],
        )
        self.root.option_add("*TCombobox*Listbox.background", SURFACE)
        self.root.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#4a3623")
        self.root.option_add("*TCombobox*Listbox.selectForeground", TEXT)

    def _load_icons(self) -> None:
        ico_path = os.path.join(RESOURCE_DIR, "panel_icon.ico")
        if os.path.exists(ico_path):
            try:
                self.root.iconbitmap(ico_path)
            except Exception:
                pass
        tb_path = os.path.join(RESOURCE_DIR, "taskbar_icon.png")
        if os.path.exists(tb_path):
            try:
                tb_full = tk.PhotoImage(file=tb_path)
                tb_64 = tb_full.subsample(4, 4)
                self._tb_icons = [tb_full, tb_64]
                self.root.iconphoto(True, tb_64, tb_full)
            except Exception:
                pass
        hdr_path = os.path.join(RESOURCE_DIR, "header_icon.png")
        if os.path.exists(hdr_path):
            try:
                small = tk.PhotoImage(file=hdr_path)
                self._icons = [small, small]
                return
            except Exception:
                pass
        png_path = os.path.join(RESOURCE_DIR, "nest_logo.png")
        if os.path.exists(png_path):
            try:
                full = tk.PhotoImage(file=png_path)
                small = full.subsample(2, 2)
                self._icons = [full, small]
            except Exception:
                pass

    def _build_ui(self) -> None:
        # 1. Clean Minimal Header
        hdr = tk.Frame(self.root, bg=BG, padx=24, pady=16)
        hdr.pack(fill="x")
        if len(self._icons) >= 2:
            tk.Label(hdr, image=self._icons[1], bg=BG).pack(side="left", padx=(0, 12))

        tcol = tk.Frame(hdr, bg=BG)
        tcol.pack(side="left")
        tk.Label(
            tcol,
            text=self.cfg.get("pack_name", "The Nest Vanilla Edition"),
            font=("Segoe UI Variable Display", 14, "bold"),
            bg=BG,
            fg=TEXT,
        ).pack(anchor="w")
        self.ver_lbl = tk.Label(
            tcol,
            text=f"Minecraft {self.cfg.get('mc_version')} · NeoForge {self.cfg.get('neoforge_version')}",
            font=("Segoe UI", 8),
            bg=BG,
            fg=ACCENT,
        )
        self.ver_lbl.pack(anchor="w", pady=(1, 0))

        # 2. Player Nickname + Auto Skin Card
        acct = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
        acct.pack(fill="x", padx=24, pady=(0, 10))

        self.avatar_lbl = tk.Label(
            acct,
            text="?",
            width=4,
            height=2,
            bg=INPUT_BG,
            fg=MUTED,
            font=("Segoe UI", 10, "bold"),
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        self.avatar_lbl.pack(side="left", padx=(0, 14))

        nick_col = tk.Frame(acct, bg=SURFACE)
        nick_col.pack(side="left", fill="x", expand=True)

        tk.Label(nick_col, text="PLAYER NICKNAME", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg=MUTED).pack(anchor="w")

        entry_shell = tk.Frame(nick_col, bg=INPUT_BG, highlightbackground=BORDER, highlightthickness=1)
        entry_shell.pack(fill="x", pady=(4, 4))

        self.nick_var = tk.StringVar(value=self.state.get("nick", ""))
        self.nick_var.trace_add("write", self._on_nick_changed)

        nick_entry = tk.Entry(
            entry_shell,
            textvariable=self.nick_var,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=ACCENT,
            font=("Segoe UI", 10, "bold"),
            bd=0,
            relief="flat",
        )
        nick_entry.pack(fill="x", padx=9, pady=5)

        self.acct_status = tk.Label(
            nick_col,
            text="Type a valid nick (3–16 chars) to load skin",
            font=("Segoe UI", 8),
            bg=SURFACE,
            fg=MUTED,
            anchor="w",
        )
        self.acct_status.pack(fill="x")

        # 3. Install Folder Card (HDD/SSD selectable)
        loc = tk.Frame(self.root, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=9)
        loc.pack(fill="x", padx=24, pady=(0, 10))

        loc_top = tk.Frame(loc, bg=SURFACE)
        loc_top.pack(fill="x")
        tk.Label(loc_top, text="MODPACK INSTALL FOLDER", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg=MUTED).pack(side="left")
        make_button(loc_top, "Open", SURFACE_ALT, "#3a2d21", TEXT, self._open_game_dir, 8, 2, 8).pack(side="right")
        make_button(loc_top, "Change...", SURFACE_ALT, "#3a2d21", ACCENT, self._choose_folder, 8, 2, 8).pack(side="right", padx=(0, 6))

        self.path_lbl = tk.Label(
            loc,
            text=self.install_root,
            font=("Cascadia Mono", 8),
            bg=SURFACE,
            fg=TEXT,
            anchor="w",
        )
        self.path_lbl.pack(fill="x", pady=(4, 0))

        # 4. Compact Settings Strip
        opts = tk.Frame(self.root, bg=BG, padx=24, pady=2)
        opts.pack(fill="x")

        tk.Label(opts, text="Memory", font=("Segoe UI", 8, "bold"), bg=BG, fg=MUTED).pack(side="left")
        self.ram_var = tk.StringVar(value=f"{self.state.get('ram_gb', 8)} GB")
        ttk.Combobox(
            opts,
            textvariable=self.ram_var,
            values=["6 GB", "8 GB", "10 GB", "12 GB"],
            width=6,
            state="readonly",
            font=("Segoe UI", 9),
            style="Nest.TCombobox",
        ).pack(side="left", padx=(8, 0))

        make_button(opts, "Check Updates", SURFACE, SURFACE_ALT, ACCENT, self._check_only, 10, 4, 8).pack(side="right")

        # 5. Bottom Play Button + Progress
        bottom = tk.Frame(self.root, bg=BG, padx=24)
        bottom.pack(side="bottom", fill="x", pady=(0, 18))

        self.status_lbl = tk.Label(bottom, text="Ready.", font=("Segoe UI", 8), bg=BG, fg=MUTED, anchor="w")
        self.status_lbl.pack(fill="x", pady=(0, 5))

        self.progress = ttk.Progressbar(bottom, style="Nest.Horizontal.TProgressbar", mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 12))

        self.play_btn = make_button(bottom, "PLAY", GOLD_BTN, GOLD_HOVER, GOLD_FG, self._on_play, 16, 10, 11)
        self.play_btn.pack(fill="x")

    def _poll_ui_queue(self) -> None:
        while True:
            try:
                fn = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except tk.TclError:
                pass
        self.root.after(50, self._poll_ui_queue)

    def _safe_ui(self, fn) -> None:
        self.ui_queue.put(fn)

    def _set_status(self, text: str, color: str = MUTED, pct: float | None = None) -> None:
        def _apply() -> None:
            self.status_lbl.configure(text=text, fg=color)
            if pct is not None:
                self.progress["value"] = max(0, min(100, pct))
        self._safe_ui(_apply)

    def _choose_folder(self) -> None:
        if self.busy:
            return
        picked = filedialog.askdirectory(initialdir=self.install_root, title="Choose Modpack Install Folder (e.g. D:\\Games\\TheNest)")
        if not picked:
            return
        chosen = os.path.normpath(picked)
        if os.path.basename(chosen).lower() != "thenestvanilla":
            chosen = os.path.join(chosen, "TheNestVanilla")
        self.state["install_root"] = chosen
        save_json(STATE_PATH, self.state)
        self.path_lbl.configure(text=chosen)
        self._set_status(f"Install path set to {chosen}", ACCENT, 0)

    def _on_nick_changed(self, *_args) -> None:
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
            self._debounce_id = None

        raw = self.nick_var.get().strip()
        if not raw:
            self.acct_status.configure(text="Type a valid nick (3–16 chars) to load skin", fg=MUTED)
            self._reset_avatar()
            return
        if not RE_VALID_NICK.match(raw):
            self.acct_status.configure(text="Invalid nick (use 3–16 letters, numbers or _)", fg=ACCENT)
            self._reset_avatar()
            return

        if raw.lower() == self._last_looked_up.lower():
            return
        self.acct_status.configure(text="Checking Minecraft account...", fg=MUTED)
        self._debounce_id = self.root.after(550, lambda n=raw: self._trigger_lookup(n))

    def _reset_avatar(self) -> None:
        self._avatar_img = None
        self.avatar_lbl.configure(image="", text="?", width=4, height=2)

    def _trigger_lookup(self, nick: str) -> None:
        self._debounce_id = None
        self._lookup_seq += 1
        seq = self._lookup_seq
        threading.Thread(target=self._lookup_nick_worker, args=(nick, seq), daemon=True).start()

    def _lookup_nick_worker(self, nick: str, seq: int) -> None:
        resolved_name, uid, is_official = fetch_mojang_profile(nick)
        if seq != self._lookup_seq:
            return
        self._last_looked_up = resolved_name
        self.state["nick"] = resolved_name
        self.state["uuid"] = uid
        save_json(STATE_PATH, self.state)

        avatar_bytes = None
        if is_official:
            try:
                avatar_bytes = http_get_bytes(HEAD_AVATAR_URL.format(ident=uid), timeout=8)
            except Exception:
                avatar_bytes = None

        def _update_ui() -> None:
            if seq != self._lookup_seq:
                return
            if is_official:
                self.acct_status.configure(text=f"Account matched ({resolved_name}) · skin loaded", fg=OK_GREEN)
            else:
                self.acct_status.configure(text=f"Offline profile ({uid[:8]}...) · default skin", fg=ACCENT)
            if avatar_bytes:
                try:
                    img = tk.PhotoImage(data=avatar_bytes)
                    self._avatar_img = img
                    self.avatar_lbl.configure(image=img, text="", width=36, height=36)
                except Exception:
                    self._reset_avatar()
            else:
                self._reset_avatar()
        self._safe_ui(_update_ui)

    def _open_game_dir(self) -> None:
        os.makedirs(self.game_dir, exist_ok=True)
        os.startfile(self.game_dir)

    def _check_only(self) -> None:
        if self.busy:
            return
        self.busy = True
        threading.Thread(target=self._sync_worker, args=(False,), daemon=True).start()

    def _on_play(self) -> None:
        if self.busy:
            return
        nick = self.nick_var.get().strip()
        if not RE_VALID_NICK.match(nick):
            messagebox.showwarning("Valid Nickname Required", "Enter a valid Minecraft nickname (3–16 characters: letters, numbers, or _).")
            return
        self.state["nick"] = nick
        self.state["ram_gb"] = int(self.ram_var.get().split()[0])
        save_json(STATE_PATH, self.state)

        self.busy = True
        self.play_btn.configure(state="disabled", text="SYNCING...")
        threading.Thread(target=self._sync_worker, args=(True,), daemon=True).start()

    def _sync_worker(self, launch_after: bool) -> None:
        try:
            resolved_name, uid, _ = fetch_mojang_profile(self.state["nick"])
            self.state["nick"], self.state["uuid"] = resolved_name, uid
            save_json(STATE_PATH, self.state)

            self._sync_from_github()
            if launch_after:
                java_exe, install_dir = self._ensure_runtime()
                self._launch_game(java_exe, install_dir)
            else:
                self._set_status("Modpack is up to date.", OK_GREEN, 100)
        except Exception as exc:
            self.busy = False
            self._set_status(f"Error: {exc}", ERR_RED)
            self._safe_ui(lambda: self.play_btn.configure(state="normal", text="PLAY"))
            self._safe_ui(lambda msg=str(exc): messagebox.showerror("Launcher Error", msg))
            return
        self.busy = False
        self._safe_ui(lambda: self.play_btn.configure(state="normal", text="PLAY"))

    def _sync_from_github(self) -> None:
        manifest_url = self.cfg.get("manifest_url", "").strip()
        files_base = self.cfg.get("files_base_url", "").strip().rstrip("/")
        game_dir = self.game_dir
        os.makedirs(game_dir, exist_ok=True)

        if not manifest_url or "CHANGE_ME_" in manifest_url:
            self._set_status("Set your GitHub repo in launcher_config.json to enable auto-updates.", ACCENT, 35)
            return

        self._set_status("Checking GitHub for updates...", MUTED, 10)
        try:
            manifest = json.loads(http_get_bytes(manifest_url, timeout=12).decode("utf-8"))
        except Exception as exc:
            self._set_status(f"Offline/GitHub unreachable ({exc}); using local files.", ACCENT, 40)
            return

        ver = manifest.get("pack_version", self.cfg.get("pack_version", "1.0.0"))
        self._safe_ui(lambda: self.ver_lbl.configure(
            text=f"v{ver} · MC {manifest.get('mc_version', '26.3')} · NeoForge {manifest.get('neoforge_version', '26.3.0.103')}"
        ))

        expected: dict[str, dict] = manifest.get("files", {})
        managed_dirs = manifest.get("managed_dirs", ["mods", "config", "resourcepacks", "defaultconfigs"])

        for mdir in managed_dirs:
            root_path = os.path.join(game_dir, mdir)
            if not os.path.exists(root_path):
                continue
            for r, _d, fnames in os.walk(root_path):
                for fn in fnames:
                    full = os.path.join(r, fn)
                    rel = os.path.relpath(full, game_dir).replace("\\", "/")
                    if rel not in expected and mdir in ("mods", "resourcepacks"):
                        os.remove(full)

        to_download: list[tuple[str, str, str]] = []
        for rel, meta in expected.items():
            dest = os.path.join(game_dir, rel.replace("/", os.sep))
            want_hash = meta.get("sha256")
            if not os.path.exists(dest) or (want_hash and sha256_file(dest) != want_hash):
                url = meta.get("url") or f"{files_base}/{urllib.parse.quote(rel)}"
                to_download.append((url, dest, want_hash))

        if not to_download:
            self._set_status(f"Up to date (v{ver}, {len(expected)} files verified).", OK_GREEN, 65)
            return

        total = len(to_download)
        done = 0
        self._set_status(f"Downloading {total} updated file(s)...", TEXT, 15)
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(download_file, u, d, h) for u, d, h in to_download]
            for fut in as_completed(futs):
                fut.result()
                done += 1
                self._set_status(f"Synced {done}/{total} files...", TEXT, 15 + (done / total) * 55)

    def _ensure_runtime(self) -> tuple[str, str]:
        java_exe = self._ensure_java25()
        mc_ver = self.cfg.get("mc_version", "26.3")
        nf_ver = self.cfg.get("neoforge_version", "26.3.0.103")

        if (
            os.path.exists(os.path.join(CF_INSTALL_DIR, "versions", mc_ver, f"{mc_ver}.json"))
            and os.path.exists(os.path.join(CF_INSTALL_DIR, "versions", f"neoforge-{nf_ver}", f"neoforge-{nf_ver}.json"))
        ):
            self._set_status("Runtime ready.", OK_GREEN, 88)
            return java_exe, CF_INSTALL_DIR

        install_dir = self.runtime_dir
        os.makedirs(os.path.join(install_dir, "versions"), exist_ok=True)
        lp_path = os.path.join(install_dir, "launcher_profiles.json")
        if not os.path.exists(lp_path):
            save_json(lp_path, {"profiles": {}, "settings": {}})

        if not os.path.exists(os.path.join(install_dir, "versions", mc_ver, f"{mc_ver}.jar")):
            self._bootstrap_vanilla(install_dir, mc_ver)

        nf_json_path = os.path.join(install_dir, "versions", f"neoforge-{nf_ver}", f"neoforge-{nf_ver}.json")
        if not os.path.exists(nf_json_path):
            self._set_status(f"Installing NeoForge {nf_ver}...", TEXT, 75)
            inst_jar = os.path.join(install_dir, f"neoforge-{nf_ver}-installer.jar")
            download_file(NEOFORGE_INSTALLER_URL.format(ver=nf_ver), inst_jar)
            res = subprocess.run([java_exe, "-jar", inst_jar, "--installClient", install_dir], capture_output=True, text=True)
            if os.path.exists(inst_jar):
                os.remove(inst_jar)
            if res.returncode != 0:
                raise RuntimeError(f"NeoForge install failed:\n{res.stderr or res.stdout}")

        self._set_status("Runtime ready!", OK_GREEN, 92)
        return java_exe, install_dir

    def _ensure_java25(self) -> str:
        if os.path.exists(CF_JAVA_25):
            return CF_JAVA_25
        local_javaw = os.path.join(self.install_root, "java25", "bin", "javaw.exe")
        if os.path.exists(local_javaw):
            return local_javaw

        self._set_status("Downloading Java 25 runtime (first setup)...", TEXT, 68)
        os.makedirs(self.install_root, exist_ok=True)
        zip_path = os.path.join(self.install_root, "java25.zip")
        download_file(ADOPTIUM_JRE25_API, zip_path)
        extract_tmp = os.path.join(self.install_root, "java25_tmp")
        if os.path.exists(extract_tmp):
            shutil.rmtree(extract_tmp)
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(extract_tmp)
        os.remove(zip_path)
        top_dirs = [d for d in os.listdir(extract_tmp) if os.path.isdir(os.path.join(extract_tmp, d))]
        target = os.path.join(self.install_root, "java25")
        if os.path.exists(target):
            shutil.rmtree(target)
        shutil.move(os.path.join(extract_tmp, top_dirs[0]), target)
        shutil.rmtree(extract_tmp, ignore_errors=True)
        return local_javaw

    def _bootstrap_vanilla(self, install_dir: str, mc_ver: str) -> None:
        self._set_status(f"Downloading Minecraft {mc_ver} assets...", TEXT, 70)
        manifest = json.loads(http_get_bytes(MC_VERSION_MANIFEST).decode("utf-8"))
        v_entry = next((v for v in manifest["versions"] if v["id"] == mc_ver), None)
        if not v_entry:
            raise RuntimeError(f"Minecraft version {mc_ver} not found in Mojang manifest.")

        v_data = json.loads(http_get_bytes(v_entry["url"]).decode("utf-8"))
        v_dir = os.path.join(install_dir, "versions", mc_ver)
        os.makedirs(v_dir, exist_ok=True)
        save_json(os.path.join(v_dir, f"{mc_ver}.json"), v_data)

        download_file(v_data["downloads"]["client"]["url"], os.path.join(v_dir, f"{mc_ver}.jar"))

        ai = v_data["assetIndex"]
        idx_path = os.path.join(install_dir, "assets", "indexes", f"{ai['id']}.json")
        if not os.path.exists(idx_path):
            download_file(ai["url"], idx_path)
        idx_data = load_json(idx_path, {})
        obj_tasks = []
        for obj in idx_data.get("objects", {}).values():
            h = obj["hash"]
            dst = os.path.join(install_dir, "assets", "objects", h[:2], h)
            if not os.path.exists(dst):
                obj_tasks.append((f"https://resources.download.minecraft.net/{h[:2]}/{h}", dst))
        if obj_tasks:
            with ThreadPoolExecutor(max_workers=10) as pool:
                for fut in as_completed([pool.submit(download_file, u, d) for u, d in obj_tasks]):
                    fut.result()

        lib_tasks = []
        for lib in v_data.get("libraries", []):
            art = lib.get("downloads", {}).get("artifact")
            if art and "path" in art:
                dst = os.path.join(install_dir, "libraries", art["path"].replace("/", os.sep))
                if not os.path.exists(dst):
                    lib_tasks.append((art["url"], dst))
        if lib_tasks:
            with ThreadPoolExecutor(max_workers=8) as pool:
                for fut in as_completed([pool.submit(download_file, u, d) for u, d in lib_tasks]):
                    fut.result()

    def _launch_game(self, java_exe: str, install_dir: str) -> None:
        mc_ver = self.cfg.get("mc_version", "26.3")
        nf_ver = self.cfg.get("neoforge_version", "26.3.0.103")
        game_dir = self.game_dir
        ram_gb = int(self.state.get("ram_gb", 8))

        with open(os.path.join(install_dir, "versions", mc_ver, f"{mc_ver}.json"), "r", encoding="utf-8") as f:
            mc_json = json.load(f)
        with open(os.path.join(install_dir, "versions", f"neoforge-{nf_ver}", f"neoforge-{nf_ver}.json"), "r", encoding="utf-8") as f:
            nf_json = json.load(f)

        lib_dir = os.path.join(install_dir, "libraries")
        cp_entries, seen = [], set()
        for src in (nf_json.get("libraries", []), mc_json.get("libraries", [])):
            for lib in src:
                rules = lib.get("rules")
                if rules:
                    allow = False
                    for r in rules:
                        os_r = r.get("os", {})
                        if not os_r or os_r.get("name") == "windows":
                            allow = r["action"] == "allow"
                    if not allow:
                        continue
                path = lib.get("downloads", {}).get("artifact", {}).get("path")
                if not path and "name" in lib:
                    parts = lib["name"].split(":")
                    g, a, v = parts[0], parts[1], parts[2]
                    c = parts[3] if len(parts) > 3 else None
                    ext = "jar"
                    if "@" in v:
                        v, ext = v.split("@", 1)
                    if c and "@" in c:
                        c, ext = c.split("@", 1)
                    fn = f"{a}-{v}" + (f"-{c}" if c else "") + f".{ext}"
                    path = "/".join(g.split(".") + [a, v, fn])
                if path:
                    full = os.path.join(lib_dir, path.replace("/", os.sep))
                    if full not in seen and os.path.exists(full):
                        seen.add(full)
                        cp_entries.append(full)

        client_jar = os.path.join(install_dir, "versions", mc_ver, f"{mc_ver}.jar")
        if os.path.exists(client_jar):
            cp_entries.append(client_jar)

        natives_dir = os.path.join(install_dir, "natives", f"neoforge-{nf_ver}")
        os.makedirs(natives_dir, exist_ok=True)
        cp_str = os.pathsep.join(cp_entries)

        jvm_args = [
            f"-Xmx{ram_gb * 1024}m",
            "-Xms512m",
            "-XX:+UseZGC",
            f"-Dminecraft.applet.TargetDirectory={game_dir}",
            f"-Djava.library.path={natives_dir}",
            f"-DlibraryDirectory={lib_dir}",
            "-Dfml.ignorePatchDiscrepancies=true",
            "-Dfml.ignoreInvalidMinecraftCertificates=true",
        ]
        for arg in mc_json.get("arguments", {}).get("jvm", []) + nf_json.get("arguments", {}).get("jvm", []):
            if isinstance(arg, str):
                a = (
                    arg.replace("${natives_directory}", natives_dir)
                    .replace("${launcher_name}", "TheNestLauncher")
                    .replace("${launcher_version}", "1.0")
                    .replace("${classpath}", cp_str)
                    .replace("${library_directory}", lib_dir)
                    .replace("${classpath_separator}", os.pathsep)
                    .replace("${version_name}", f"neoforge-{nf_ver}")
                )
                jvm_args.append(a)

        asset_idx = mc_json.get("assetIndex", {}).get("id", self.cfg.get("asset_index", "34"))
        game_args = [
            "--username", self.state["nick"],
            "--version", f"neoforge-{nf_ver}",
            "--gameDir", game_dir,
            "--assetsDir", os.path.join(install_dir, "assets"),
            "--assetIndex", asset_idx,
            "--uuid", self.state["uuid"] or offline_uuid_for_nick(self.state["nick"]),
            "--accessToken", "0",
            "--userType", "msa",
            "--versionType", "release",
        ] + [str(x) for x in nf_json.get("arguments", {}).get("game", []) if isinstance(x, str)]

        self._set_status(f"Launching as {self.state['nick']}...", OK_GREEN, 100)
        subprocess.Popen([java_exe] + jvm_args + [nf_json["mainClass"]] + game_args, cwd=game_dir)
        self._safe_ui(lambda: self.root.after(1200, self.root.destroy))


if __name__ == "__main__":
    app_root = tk.Tk()
    NestLauncher(app_root)
    app_root.mainloop()
