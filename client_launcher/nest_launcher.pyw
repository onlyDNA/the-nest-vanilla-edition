"""The Nest Vanilla Edition — Standalone GitHub Auto-Updating Client Launcher."""

from concurrent.futures import ThreadPoolExecutor, as_completed
import base64
import ctypes
import hashlib
import json
import math
import os
import queue
import re
import shutil
import socket
import struct
import subprocess
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import urllib.parse
import urllib.request
import uuid
import zipfile
import zlib

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


class _SelfUpdateTriggered(Exception):
    """Internal signal raised when the launcher swaps its own EXE and restarts."""

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


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def get_memory_info_gb() -> tuple[float, float, float]:
    """Return (total_phys_gb, avail_phys_gb, avail_commit_gb) on Windows."""
    try:
        st = _MEMORYSTATUSEX()
        st.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
            gb = float(1024 ** 3)
            return (st.ullTotalPhys / gb, st.ullAvailPhys / gb, st.ullAvailPageFile / gb)
    except Exception:
        pass
    return (16.0, 10.0, 12.0)


def resolve_safe_ram_gb(requested_gb: int) -> tuple[int, str]:
    """Clamp requested JVM heap safely so Windows + native GL/Voxy buffers never OOM."""
    total_gb, _avail_phys, avail_commit = get_memory_info_gb()
    # Leave plenty of room for OS, GPU drivers, native/off-heap Voxy allocations, and background apps
    phys_cap = max(4, int(total_gb * 0.55))
    commit_cap = max(4, int(avail_commit - 3))
    safe = min(max(4, requested_gb), phys_cap, commit_cap)
    if safe < requested_gb:
        return safe, f"Clamped RAM {requested_gb}GB -> {safe}GB (safe limit {phys_cap}GB, commit free {avail_commit:.1f}GB)"
    return safe, ""


def _pack_varint(v: int) -> bytes:
    out = bytearray()
    while (v & ~0x7F) != 0:
        out.append((v & 0x7F) | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


def _recv_varint(sock: socket.socket) -> int:
    val = 0
    shift = 0
    while True:
        b = sock.recv(1)
        if not b:
            raise EOFError("EOF reading VarInt")
        byte = b[0]
        val |= (byte & 0x7F) << shift
        if not (byte & 0x80):
            return val
        shift += 7
        if shift > 35:
            raise ValueError("VarInt too long")


def ping_mc_server(host_port: str, timeout: float = 1.4) -> tuple[str, int, int]:
    """Return ('online'|'starting'|'offline', online_players, max_players)."""
    host = host_port.strip()
    port = 25565
    if ":" in host:
        h_part, p_part = host.rsplit(":", 1)
        host = h_part.strip()
        try:
            port = int(p_part.strip())
        except ValueError:
            port = 25565
    if not host:
        return ("offline", 0, 0)
    connected = False
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            connected = True
            sock.settimeout(timeout)
            hb = host.encode("utf-8")
            hs = _pack_varint(0) + _pack_varint(769) + _pack_varint(len(hb)) + hb + struct.pack(">H", port) + _pack_varint(1)
            sock.sendall(_pack_varint(len(hs)) + hs)
            sock.sendall(b"\x01\x00")
            _pkt_len = _recv_varint(sock)
            pid = _recv_varint(sock)
            if pid != 0:
                return ("starting", 0, 0)
            slen = _recv_varint(sock)
            if slen <= 0 or slen > 65536:
                return ("starting", 0, 0)
            buf = bytearray()
            while len(buf) < slen:
                chunk = sock.recv(slen - len(buf))
                if not chunk:
                    return ("starting", 0, 0)
                buf.extend(chunk)
            info = json.loads(buf.decode("utf-8", errors="replace"))
            players = info.get("players", {})
            return ("online", int(players.get("online", 0)), int(players.get("max", 20)))
    except Exception:
        return ("starting", 0, 0) if connected else ("offline", 0, 0)


def check_nest_server_status(targets: list[str]) -> tuple[str, int, int]:
    """Check all configured server targets and detect local server boot if starting."""
    seen: list[str] = []
    for t in targets:
        t = (t or "").strip()
        if t and t not in seen:
            seen.append(t)
    any_starting = False
    for tgt in seen:
        st, onl, mx = ping_mc_server(tgt)
        if st == "online":
            return ("online", onl, mx)
        if st == "starting":
            any_starting = True
    if any_starting:
        return ("starting", 0, 0)
    # Detect host-side dedicated server starting before port 25565 binds
    local_lock = r"C:\Users\katen\Desktop\TheNest VanillaEditon Server\world\session.lock"
    if os.path.exists(local_lock):
        try:
            with open(local_lock, "r+b"):
                pass
        except PermissionError:
            return ("starting", 0, 0)
        except Exception:
            pass
    return ("offline", 0, 0)


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


def fetch_mojang_skin_png(nick: str) -> tuple[str, str, bool, bytes | None, bool]:
    """Fetch official Mojang profile + raw 64x64 skin PNG bytes + slim arm flag."""
    resolved_name, uid, is_official = fetch_mojang_profile(nick)
    if not is_official or not uid:
        return resolved_name, uid, False, None, False
    try:
        sess_url = f"https://sessionserver.mojang.com/session/minecraft/profile/{uid}"
        sess_data = json.loads(http_get_bytes(sess_url, timeout=8).decode("utf-8"))
        for prop in sess_data.get("properties", []):
            if prop.get("name") == "textures" and prop.get("value"):
                tex_json = json.loads(base64.b64decode(prop["value"]).decode("utf-8"))
                skin_info = tex_json.get("textures", {}).get("SKIN", {})
                skin_url = skin_info.get("url")
                is_slim = skin_info.get("metadata", {}).get("model") == "slim"
                if skin_url:
                    png_bytes = http_get_bytes(skin_url, timeout=8)
                    if png_bytes and len(png_bytes) > 64:
                        return resolved_name, uid, True, png_bytes, is_slim
    except Exception:
        pass
    return resolved_name, uid, is_official, None, False


def make_default_steve_grid() -> list[list[tuple[int, int, int, int]]]:
    """Generate a clean procedural 64x64 Steve skin grid for fallback 3D preview."""
    grid = [[(0, 0, 0, 0) for _ in range(64)] for _ in range(64)]

    def fill_rect(x0: int, y0: int, w: int, h: int, rgba: tuple[int, int, int, int]) -> None:
        for yy in range(y0, min(64, y0 + h)):
            for xx in range(x0, min(64, x0 + w)):
                grid[yy][xx] = rgba

    skin = (186, 136, 102, 255)
    skin_dark = (165, 117, 85, 255)
    hair = (72, 46, 28, 255)
    shirt = (0, 158, 168, 255)
    shirt_dark = (0, 134, 143, 255)
    pants = (56, 58, 130, 255)
    shoes = (75, 75, 78, 255)

    # Head (u=0, v=0)
    fill_rect(8, 0, 8, 8, hair)
    fill_rect(16, 0, 8, 8, skin_dark)
    fill_rect(0, 8, 32, 8, skin)
    fill_rect(0, 8, 8, 3, hair)
    fill_rect(8, 8, 8, 2, hair)
    fill_rect(16, 8, 16, 4, hair)
    # Eyes & mouth on front face (8..15, 8..15)
    grid[12][9] = (255, 255, 255, 255)
    grid[12][10] = (73, 59, 122, 255)
    grid[12][13] = (73, 59, 122, 255)
    grid[12][14] = (255, 255, 255, 255)
    fill_rect(11, 13, 2, 1, (145, 95, 70, 255))
    fill_rect(10, 14, 4, 1, (112, 65, 46, 255))

    # Body (u=16, v=16)
    fill_rect(20, 16, 8, 4, shirt)
    fill_rect(28, 16, 8, 4, shirt_dark)
    fill_rect(16, 20, 24, 12, shirt)
    fill_rect(22, 20, 4, 2, skin)

    # Right Arm (u=40, v=16) & Left Arm (u=32, v=48)
    for u0, v0 in ((40, 16), (32, 48)):
        fill_rect(u0 + 4, v0, 8, 4, shirt)
        fill_rect(u0, v0 + 4, 16, 4, shirt)
        fill_rect(u0, v0 + 8, 16, 8, skin)

    # Right Leg (u=0, v=16) & Left Leg (u=16, v=48)
    for u0, v0 in ((0, 16), (16, 48)):
        fill_rect(u0 + 4, v0, 8, 4, pants)
        fill_rect(u0, v0 + 4, 16, 10, pants)
        fill_rect(u0, v0 + 14, 16, 2, shoes)

    return grid


def decode_skin_png(png_bytes: bytes | None) -> list[list[tuple[int, int, int, int]]]:
    """Pure-Python decoder for 64x64 and 64x32 Minecraft skin PNGs."""
    if not png_bytes or len(png_bytes) < 64 or png_bytes[:8] != b"\x89PNG\r\n\x1a\n":
        return make_default_steve_grid()
    try:
        pos = 8
        width = height = bit_depth = color_type = 0
        plte: list[tuple[int, int, int]] = []
        trns = b""
        idat_parts: list[bytes] = []

        while pos + 8 <= len(png_bytes):
            length = struct.unpack(">I", png_bytes[pos : pos + 4])[0]
            ctype = png_bytes[pos + 4 : pos + 8]
            cdata = png_bytes[pos + 8 : pos + 8 + length]
            pos += 12 + length
            if ctype == b"IHDR":
                width, height, bit_depth, color_type, _c, _f, _i = struct.unpack(">IIBBBBB", cdata[:13])
            elif ctype == b"PLTE":
                plte = [(cdata[i], cdata[i + 1], cdata[i + 2]) for i in range(0, len(cdata) - 2, 3)]
            elif ctype == b"tRNS":
                trns = cdata
            elif ctype == b"IDAT":
                idat_parts.append(cdata)
            elif ctype == b"IEND":
                break

        if width != 64 or height not in (32, 64) or bit_depth != 8:
            return make_default_steve_grid()

        bpp_map = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
        bpp = bpp_map.get(color_type, 4)
        stride = width * bpp
        raw = zlib.decompress(b"".join(idat_parts))

        recon = bytearray(height * stride)
        in_idx = 0
        for y in range(height):
            ftype = raw[in_idx]
            in_idx += 1
            row_start = y * stride
            prev_start = (y - 1) * stride
            for x in range(stride):
                val = raw[in_idx]
                in_idx += 1
                a = recon[row_start + x - bpp] if x >= bpp else 0
                b = recon[prev_start + x] if y > 0 else 0
                c = recon[prev_start + x - bpp] if (y > 0 and x >= bpp) else 0
                if ftype == 1:
                    val = (val + a) & 0xFF
                elif ftype == 2:
                    val = (val + b) & 0xFF
                elif ftype == 3:
                    val = (val + ((a + b) >> 1)) & 0xFF
                elif ftype == 4:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                    val = (val + pr) & 0xFF
                recon[row_start + x] = val

        grid = [[(0, 0, 0, 0) for _ in range(64)] for _ in range(64)]
        for y in range(height):
            row_off = y * stride
            for x in range(width):
                px = row_off + x * bpp
                if color_type == 6:
                    r, g, b, al = recon[px], recon[px + 1], recon[px + 2], recon[px + 3]
                elif color_type == 2:
                    r, g, b = recon[px], recon[px + 1], recon[px + 2]
                    al = 255
                elif color_type == 3:
                    idx = recon[px]
                    r, g, b = plte[idx] if idx < len(plte) else (0, 0, 0)
                    al = trns[idx] if idx < len(trns) else 255
                elif color_type == 4:
                    r = g = b = recon[px]
                    al = recon[px + 1]
                else:
                    r = g = b = recon[px]
                    al = 255
                grid[y][x] = (r, g, b, al)

        # Convert legacy 64x32 skin to 64x64 (mirror right leg -> left leg, right arm -> left arm)
        if height == 32:
            for dy in range(16):
                for dx in range(16):
                    grid[48 + dy][16 + dx] = grid[16 + dy][dx]
                    grid[48 + dy][32 + dx] = grid[16 + dy][40 + dx]

        return grid
    except Exception:
        return make_default_steve_grid()


def render_head_avatar_photoimage(grid: list[list[tuple[int, int, int, int]]], size: int = 36) -> tk.PhotoImage:
    """Render the 8x8 front face + 8x8 hat overlay directly into a crisp tk.PhotoImage."""
    img = tk.PhotoImage(width=8, height=8)
    rows = []
    for y in range(8):
        row_cols = []
        for x in range(8):
            br, bg_c, bb, _ba = grid[8 + y][8 + x]
            hr, hg, hb, ha = grid[8 + y][40 + x]
            if ha > 24:
                alpha = ha / 255.0
                r = int(hr * alpha + br * (1.0 - alpha))
                g = int(hg * alpha + bg_c * (1.0 - alpha))
                b = int(hb * alpha + bb * (1.0 - alpha))
            else:
                r, g, b = br, bg_c, bb
            row_cols.append(f"#{r:02x}{g:02x}{b:02x}")
        rows.append("{" + " ".join(row_cols) + "}")
    img.put(" ".join(rows))
    scale = max(1, round(size / 8))
    return img.zoom(scale, scale)


class SkinStudioWindow(tk.Toplevel):
    """Seamless, Borderless 3D Skin Preview, Default/Slim Arm Selector & Skin Preset Manager."""

    def __init__(self, launcher: "NestLauncher") -> None:
        super().__init__(launcher.root)
        self.launcher = launcher
        self.title("The Nest — 3D Skin Studio")
        self.configure(bg=BG, highlightthickness=0, bd=0)
        self.resizable(False, False)

        # Frameless seamless popup window centered over/near launcher
        self.overrideredirect(True)
        self.launcher.root.update_idletasks()
        lx = self.launcher.root.winfo_rootx()
        ly = self.launcher.root.winfo_rooty()
        lw = self.launcher.root.winfo_width()
        lh = self.launcher.root.winfo_height()
        ww, wh = 660, 450
        px = max(20, lx + (lw - ww) // 2)
        py = max(20, ly + (lh - wh) // 2)
        self.geometry(f"{ww}x{wh}+{px}+{py}")
        self.transient(launcher.root)
        self.lift()

        self._win_drag_origin: tuple[int, int] | None = None

        self.presets_dir = os.path.join(STATE_DIR, "skin_presets")
        self.presets_index_path = os.path.join(self.presets_dir, "presets.json")
        os.makedirs(self.presets_dir, exist_ok=True)
        self.presets: list[dict] = self._load_presets_list()

        # Current editor state
        self.current_mode: str = launcher.state.get("skin_mode", "mojang")
        self.current_slim: bool = bool(launcher.state.get("skin_slim", False))
        self.current_preset_name: str = launcher.state.get("skin_preset_name", "")
        b64 = launcher.state.get("skin_png_b64", "")
        self.current_png_bytes: bytes | None = None
        if b64:
            try:
                self.current_png_bytes = base64.b64decode(b64)
            except Exception:
                self.current_png_bytes = None
        if not self.current_png_bytes and launcher._mojang_skin_bytes:
            self.current_png_bytes = launcher._mojang_skin_bytes
            if self.current_mode == "mojang":
                self.current_slim = launcher._mojang_skin_slim

        self.skin_grid = decode_skin_png(self.current_png_bytes)

        # 3D camera state (No continuous auto-rotate timer -> 0% idle CPU & instant UI!)
        self.yaw = -0.52
        self.pitch = 0.22
        self.walk_phase = 0.65
        self._drag_last: tuple[int, int] | None = None
        self._last_render_ts = 0.0
        self.walk_pose = True
        self.outer_layers = True

        self._build_studio_ui()
        self._refresh_arm_buttons()
        self._refresh_presets_listbox()
        self._render_3d()

    def _start_win_drag(self, event) -> None:
        self._win_drag_origin = (event.x_root - self.winfo_x(), event.y_root - self.winfo_y())

    def _on_win_drag(self, event) -> None:
        if self._win_drag_origin is not None:
            nx = event.x_root - self._win_drag_origin[0]
            ny = event.y_root - self._win_drag_origin[1]
            self.geometry(f"+{nx}+{ny}")

    def _load_presets_list(self) -> list[dict]:
        data = load_json(self.presets_index_path, {"presets": []})
        raw_list = data.get("presets", [])
        return [p for p in raw_list if isinstance(p, dict) and p.get("name") and p.get("file")]

    def _save_presets_list(self) -> None:
        save_json(self.presets_index_path, {"presets": self.presets})

    def _build_studio_ui(self) -> None:
        # Seamless Top Bar (No border, draggable, white corner options)
        hdr = tk.Frame(self, bg=BG, highlightthickness=0, bd=0, padx=18, pady=12)
        hdr.pack(fill="x")
        hdr.bind("<ButtonPress-1>", self._start_win_drag)
        hdr.bind("<B1-Motion>", self._on_win_drag)

        title_lbl = tk.Label(
            hdr,
            text="SKIN STUDIO",
            font=("Segoe UI Variable Display", 12, "bold"),
            bg=BG,
            fg="#ffffff",
        )
        title_lbl.pack(side="left")
        title_lbl.bind("<ButtonPress-1>", self._start_win_drag)
        title_lbl.bind("<B1-Motion>", self._on_win_drag)

        # Top-right corner white options (Apply & Close + X)
        close_lbl = tk.Label(
            hdr,
            text="✕",
            font=("Segoe UI", 11, "bold"),
            bg=BG,
            fg="#ffffff",
            padx=8,
            pady=2,
            cursor="hand2",
        )
        close_lbl.pack(side="right")
        close_lbl.bind("<Button-1>", lambda _e: self.destroy())
        close_lbl.bind("<Enter>", lambda _e: close_lbl.configure(fg=ERR_RED))
        close_lbl.bind("<Leave>", lambda _e: close_lbl.configure(fg="#ffffff"))

        self.mode_badge = tk.Label(
            hdr,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg=BG,
            fg="#ffffff",
            padx=10,
        )
        self.mode_badge.pack(side="right")
        self.mode_badge.bind("<ButtonPress-1>", self._start_win_drag)
        self.mode_badge.bind("<B1-Motion>", self._on_win_drag)

        body = tk.Frame(self, bg=BG, highlightthickness=0, bd=0, padx=18, pady=4)
        body.pack(fill="both", expand=True)

        # LEFT PANE: Seamless 3D Preview Canvas (No border, options in white in the corner)
        left = tk.Frame(body, bg=BG, highlightthickness=0, bd=0)
        left.pack(side="left", fill="y", padx=(0, 16))

        self.canvas = tk.Canvas(
            left,
            width=265,
            height=375,
            bg=BG,
            highlightthickness=0,
            bd=0,
            cursor="fleur",
        )
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._on_canvas_down)
        self.canvas.bind("<B1-Motion>", self._on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_canvas_up)

        # RIGHT PANE: Seamless Controls & Presets (No borders)
        right = tk.Frame(body, bg=BG, highlightthickness=0, bd=0)
        right.pack(side="left", fill="both", expand=True)

        # 1. Skin Source Section
        src_card = tk.Frame(right, bg=SURFACE, highlightthickness=0, bd=0, padx=14, pady=10)
        src_card.pack(fill="x", pady=(0, 8))

        tk.Label(src_card, text="LOAD OR IMPORT SKIN", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg="#ffffff").pack(anchor="w")

        btn_row = tk.Frame(src_card, bg=SURFACE, pady=6)
        btn_row.pack(fill="x")
        make_button(btn_row, "Import .PNG File", GOLD_BTN, GOLD_HOVER, GOLD_FG, self._import_png_file, 10, 5, 8).pack(side="left", padx=(0, 6))
        make_button(btn_row, "Use My Nickname", SURFACE_ALT, "#3a2d21", "#ffffff", self._use_my_nickname_skin, 10, 5, 8).pack(side="left")

        fetch_row = tk.Frame(src_card, bg=SURFACE)
        fetch_row.pack(fill="x", pady=(2, 0))
        tk.Label(fetch_row, text="Nick:", font=("Segoe UI", 8, "bold"), bg=SURFACE, fg="#ffffff").pack(side="left")
        self.fetch_nick_var = tk.StringVar(value=self.launcher.nick_var.get().strip())
        fetch_entry = tk.Entry(
            fetch_row,
            textvariable=self.fetch_nick_var,
            bg=INPUT_BG,
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Segoe UI", 9, "bold"),
            bd=0,
            highlightthickness=0,
            relief="flat",
            width=16,
        )
        fetch_entry.pack(side="left", padx=6, ipady=4)
        make_button(fetch_row, "Fetch Skin", SURFACE_ALT, "#3a2d21", "#ffffff", self._fetch_from_nick, 10, 4, 8).pack(side="left")

        # 2. Arm Model Section (Default vs Slim)
        arm_card = tk.Frame(right, bg=SURFACE, highlightthickness=0, bd=0, padx=14, pady=10)
        arm_card.pack(fill="x", pady=(0, 8))

        tk.Label(arm_card, text="ARM MODEL", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg="#ffffff").pack(anchor="w", pady=(0, 6))

        arm_btns = tk.Frame(arm_card, bg=SURFACE)
        arm_btns.pack(fill="x")
        self.btn_arm_default = make_button(
            arm_btns,
            "Default (4px Wide)",
            SURFACE_ALT,
            GOLD_HOVER,
            "#ffffff",
            lambda: self._set_arm_model(False),
            10,
            5,
            8,
        )
        self.btn_arm_default.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.btn_arm_slim = make_button(
            arm_btns,
            "Slim (3px Alex)",
            SURFACE_ALT,
            GOLD_HOVER,
            "#ffffff",
            lambda: self._set_arm_model(True),
            10,
            5,
            8,
        )
        self.btn_arm_slim.pack(side="left", fill="x", expand=True)

        # 3. Skin Presets Manager Section
        pre_card = tk.Frame(right, bg=SURFACE, highlightthickness=0, bd=0, padx=14, pady=10)
        pre_card.pack(fill="both", expand=True, pady=(0, 8))

        tk.Label(pre_card, text="SAVED SKIN PRESETS", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg="#ffffff").pack(anchor="w")

        save_row = tk.Frame(pre_card, bg=SURFACE, pady=6)
        save_row.pack(fill="x")
        self.preset_name_var = tk.StringVar(value=self.current_preset_name or "My Skin")
        pre_entry = tk.Entry(
            save_row,
            textvariable=self.preset_name_var,
            bg=INPUT_BG,
            fg="#ffffff",
            insertbackground="#ffffff",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        pre_entry.pack(side="left", fill="x", expand=True, padx=(0, 6), ipady=4)
        make_button(save_row, "Save", SURFACE_ALT, "#3a2d21", "#ffffff", self._save_current_preset, 10, 4, 8).pack(side="left", padx=(0, 4))
        make_button(save_row, "Delete", SURFACE_ALT, "#3a2d21", "#ffffff", self._delete_selected_preset, 10, 4, 8).pack(side="left")

        list_shell = tk.Frame(pre_card, bg=INPUT_BG, highlightthickness=0, bd=0)
        list_shell.pack(fill="both", expand=True)

        self.preset_listbox = tk.Listbox(
            list_shell,
            bg=INPUT_BG,
            fg="#ffffff",
            selectbackground= SURFACE_ALT,
            selectforeground="#ffffff",
            font=("Segoe UI", 9),
            bd=0,
            highlightthickness=0,
            activestyle="none",
            height=4,
        )
        self.preset_listbox.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        self.preset_listbox.bind("<<ListboxSelect>>", self._on_preset_selected)

        # 4. Bottom Apply & Equip Button
        bot = tk.Frame(right, bg=BG, highlightthickness=0, bd=0)
        bot.pack(fill="x")
        self.studio_status = tk.Label(bot, text="Drag 3D model to rotate.", font=("Segoe UI", 8), bg=BG, fg="#ffffff", anchor="w")
        self.studio_status.pack(fill="x", pady=(0, 4))

        make_button(
            bot,
            "APPLY & EQUIP SKIN",
            GOLD_BTN,
            GOLD_HOVER,
            GOLD_FG,
            self._apply_and_close,
            14,
            8,
            10,
        ).pack(fill="x")

        self._update_mode_badge()

    def _update_mode_badge(self) -> None:
        arm_txt = "Slim 3px" if self.current_slim else "Default 4px"
        if self.current_mode == "custom":
            label = f"{self.current_preset_name or 'Custom'} · {arm_txt}"
        else:
            label = f"Auto Nick · {arm_txt}"
        self.mode_badge.configure(text=label)

    def _refresh_arm_buttons(self) -> None:
        if self.current_slim:
            self.btn_arm_slim.configure(bg=GOLD_BTN, fg=GOLD_FG)
            self.btn_arm_default.configure(bg=SURFACE_ALT, fg="#ffffff")
        else:
            self.btn_arm_default.configure(bg=GOLD_BTN, fg=GOLD_FG)
            self.btn_arm_slim.configure(bg=SURFACE_ALT, fg="#ffffff")
        self._update_mode_badge()

    def _set_arm_model(self, slim: bool) -> None:
        self.current_slim = slim
        if self.current_png_bytes:
            self.current_mode = "custom"
        self._refresh_arm_buttons()
        self._render_3d()
        self.studio_status.configure(
            text=f"Arm style set to {'Slim (Alex 3px)' if slim else 'Default (Classic 4px)'}.",
            fg="#ffffff",
        )

    def _import_png_file(self) -> None:
        path = filedialog.askopenfilename(
            parent=self,
            title="Select Minecraft Skin (.png, 64x64 or 64x32)",
            filetypes=[("PNG Skin Files", "*.png"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "rb") as f:
                data = f.read()
            if len(data) < 64 or data[:8] != b"\x89PNG\r\n\x1a\n":
                messagebox.showerror("Invalid PNG", "Selected file is not a valid PNG image.", parent=self)
                return
            if len(data) > 65536:
                messagebox.showerror("File Too Large", "Skin PNG must be 64x64 (under 64 KB).", parent=self)
                return
            self.current_png_bytes = data
            self.skin_grid = decode_skin_png(data)
            self.current_mode = "custom"
            base_name = os.path.splitext(os.path.basename(path))[0]
            self.current_preset_name = base_name
            self.preset_name_var.set(base_name)
            self._update_mode_badge()
            self._render_3d()
            self.studio_status.configure(text=f"Loaded '{os.path.basename(path)}'", fg="#ffffff")
        except Exception as exc:
            messagebox.showerror("Import Error", str(exc), parent=self)

    def _use_my_nickname_skin(self) -> None:
        nick = self.launcher.nick_var.get().strip() or self.launcher.state.get("nick", "")
        self.current_mode = "mojang"
        self.current_preset_name = ""
        if self.launcher._mojang_skin_bytes:
            self.current_png_bytes = self.launcher._mojang_skin_bytes
            self.current_slim = self.launcher._mojang_skin_slim
            self.skin_grid = decode_skin_png(self.current_png_bytes)
            self._refresh_arm_buttons()
            self._render_3d()
            self.studio_status.configure(text=f"Using official Mojang skin for '{nick}'.", fg="#ffffff")
        elif nick:
            self.fetch_nick_var.set(nick)
            self._fetch_from_nick(keep_mojang_mode=True)
        else:
            self.skin_grid = make_default_steve_grid()
            self._update_mode_badge()
            self._render_3d()
            self.studio_status.configure(text="Set to Auto Nickname skin mode.", fg="#ffffff")

    def _fetch_from_nick(self, keep_mojang_mode: bool = False) -> None:
        target = self.fetch_nick_var.get().strip()
        if not target:
            return
        self.studio_status.configure(text=f"Fetching Mojang skin for '{target}'...", fg=MUTED)

        def _worker() -> None:
            resolved, _uid, ok, png_bytes, is_slim = fetch_mojang_skin_png(target)

            def _done() -> None:
                if not self.winfo_exists():
                    return
                if ok and png_bytes:
                    self.current_png_bytes = png_bytes
                    self.current_slim = is_slim
                    self.skin_grid = decode_skin_png(png_bytes)
                    self.current_mode = "mojang" if keep_mojang_mode else "custom"
                    self.current_preset_name = "" if keep_mojang_mode else resolved
                    self.preset_name_var.set(resolved)
                    self._refresh_arm_buttons()
                    self._render_3d()
                    self.studio_status.configure(
                        text=f"Fetched '{resolved}' ({'Slim' if is_slim else 'Default'})",
                        fg="#ffffff",
                    )
                else:
                    self.studio_status.configure(text=f"No Mojang skin found for '{target}'.", fg=ERR_RED)

            self.launcher._safe_ui(_done)

        threading.Thread(target=_worker, daemon=True).start()

    def _refresh_presets_listbox(self) -> None:
        self.preset_listbox.delete(0, "end")
        for p in self.presets:
            arm = "Slim 3px" if p.get("slim") else "Default 4px"
            self.preset_listbox.insert("end", f"  {p['name']}   [{arm}]")

    def _save_current_preset(self) -> None:
        if not self.current_png_bytes:
            messagebox.showwarning("No Skin Loaded", "Import a .PNG skin or fetch a nickname skin first before saving a preset.", parent=self)
            return
        name = self.preset_name_var.get().strip()
        if not name:
            messagebox.showwarning("Preset Name", "Enter a name for this skin preset.", parent=self)
            return
        safe_fn = re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_") or "skin"
        fn = f"{safe_fn}_{uuid.uuid4().hex[:6]}.png"
        full_png = os.path.join(self.presets_dir, fn)
        with open(full_png, "wb") as f:
            f.write(self.current_png_bytes)

        existing_idx = next((i for i, p in enumerate(self.presets) if p["name"].lower() == name.lower()), None)
        entry = {"name": name, "file": fn, "slim": self.current_slim}
        if existing_idx is not None:
            old_file = os.path.join(self.presets_dir, self.presets[existing_idx].get("file", ""))
            if os.path.exists(old_file) and old_file != full_png:
                try:
                    os.remove(old_file)
                except Exception:
                    pass
            self.presets[existing_idx] = entry
        else:
            self.presets.append(entry)

        self._save_presets_list()
        self.current_mode = "custom"
        self.current_preset_name = name
        self._refresh_presets_listbox()
        self._update_mode_badge()
        self.studio_status.configure(text=f"Saved preset '{name}'", fg="#ffffff")

    def _on_preset_selected(self, _event=None) -> None:
        sel = self.preset_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.presets):
            return
        p = self.presets[idx]
        png_path = os.path.join(self.presets_dir, p["file"])
        if not os.path.exists(png_path):
            self.studio_status.configure(text="Preset file missing on disk.", fg=ERR_RED)
            return
        with open(png_path, "rb") as f:
            data = f.read()
        self.current_png_bytes = data
        self.current_slim = bool(p.get("slim", False))
        self.current_mode = "custom"
        self.current_preset_name = p["name"]
        self.preset_name_var.set(p["name"])
        self.skin_grid = decode_skin_png(data)
        self._refresh_arm_buttons()
        self._render_3d()
        self.studio_status.configure(text=f"Loaded preset '{p['name']}'", fg="#ffffff")

    def _delete_selected_preset(self) -> None:
        sel = self.preset_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Preset", "Click a preset in the list first to delete it.", parent=self)
            return
        idx = sel[0]
        if idx < 0 or idx >= len(self.presets):
            return
        removed = self.presets.pop(idx)
        png_path = os.path.join(self.presets_dir, removed.get("file", ""))
        if os.path.exists(png_path):
            try:
                os.remove(png_path)
            except Exception:
                pass
        self._save_presets_list()
        self._refresh_presets_listbox()
        self.studio_status.configure(text=f"Deleted preset '{removed['name']}'.", fg="#ffffff")

    def _apply_and_close(self) -> None:
        self.launcher.apply_skin_from_studio(
            mode=self.current_mode,
            slim=self.current_slim,
            preset_name=self.current_preset_name,
            png_bytes=self.current_png_bytes,
            grid=self.skin_grid,
        )
        self.destroy()

    def _on_canvas_down(self, event) -> None:
        # Check if user clicked one of the white corner options in the top-left corner of the canvas
        if event.x <= 125 and event.y <= 92:
            if event.y < 24:
                self._set_arm_model(not self.current_slim)
                return
            if event.y < 44:
                self.walk_pose = not self.walk_pose
                self._render_3d()
                return
            if event.y < 64:
                self.outer_layers = not self.outer_layers
                self._render_3d()
                return
            if event.y < 84:
                self.yaw = -0.52
                self.pitch = 0.22
                self._render_3d()
                return
        self._drag_last = (event.x, event.y)

    def _on_canvas_drag(self, event) -> None:
        if self._drag_last is None:
            return
        now = time.monotonic()
        if now - self._last_render_ts < 0.022:
            return
        dx = event.x - self._drag_last[0]
        dy = event.y - self._drag_last[1]
        self._drag_last = (event.x, event.y)
        self.yaw += dx * 0.018
        self.pitch = max(-1.1, min(1.1, self.pitch + dy * 0.015))
        self._last_render_ts = now
        self._render_3d(fast_drag=True)

    def _on_canvas_up(self, _event) -> None:
        if self._drag_last is not None:
            self._drag_last = None
            self._render_3d(fast_drag=False)

    def _render_3d(self, fast_drag: bool = False) -> None:
        if not self.winfo_exists():
            return
        self.canvas.delete("all")
        cw, ch = 265, 375

        # Subtle floor shadow oval (no outline border)
        self.canvas.create_oval(cw // 2 - 52, ch - 42, cw // 2 + 52, ch - 20, fill="#0c0907", outline="")

        cy_yaw, sy_yaw = math.cos(self.yaw), math.sin(self.yaw)
        cx_pit, sx_pit = math.cos(self.pitch), math.sin(self.pitch)
        scale = 7.6
        center_x = cw * 0.5
        center_y = ch * 0.52

        swing = math.sin(self.walk_phase) * 0.38 if self.walk_pose else 0.0
        arm_w = 3 if self.current_slim else 4

        # List of (z_depth, flat_xy_coords, hex_color)
        polys: list[tuple[float, list[float], str]] = []

        def transform_pt(px: float, py: float, pz: float) -> tuple[float, float, float]:
            x1 = px * cy_yaw + pz * sy_yaw
            z1 = -px * sy_yaw + pz * cy_yaw
            y2 = py * cx_pit - z1 * sx_pit
            z2 = py * sx_pit + z1 * cx_pit
            perspective = 1.0 + (z2 / 140.0)
            sx = center_x + x1 * scale * perspective
            sy = center_y - y2 * scale * perspective
            return sx, sy, z2

        def add_box(
            bx: float,
            by: float,
            bz: float,
            bw: float,
            bh: float,
            bd: float,
            u0: int,
            v0: int,
            tw: int,
            th: int,
            td: int,
            pivot_y: float = 0.0,
            rot_x: float = 0.0,
            is_overlay: bool = False,
        ) -> None:
            cr, sr = math.cos(rot_x), math.sin(rot_x)

            def local_to_world(lx: float, ly: float, lz: float) -> tuple[float, float, float]:
                if rot_x != 0.0:
                    ry = ly - pivot_y
                    ny = pivot_y + ry * cr - lz * sr
                    nz = ry * sr + lz * cr
                    return lx, ny, nz
                return lx, ly, lz

            x0, x1 = bx - bw * 0.5, bx + bw * 0.5
            y0, y1 = by - bh * 0.5, by + bh * 0.5
            z0, z1 = bz - bd * 0.5, bz + bd * 0.5

            faces = [
                ("front", u0 + td, v0 + td, tw, th, 0.96, (x0, y1, z1), (bw, 0.0, 0.0), (0.0, -bh, 0.0), (0.0, 0.0, 1.0)),
                ("back", u0 + 2 * td + tw, v0 + td, tw, th, 0.70, (x1, y1, z0), (-bw, 0.0, 0.0), (0.0, -bh, 0.0), (0.0, 0.0, -1.0)),
                ("right", u0, v0 + td, td, th, 0.80, (x0, y1, z0), (0.0, 0.0, bd), (0.0, -bh, 0.0), (-1.0, 0.0, 0.0)),
                ("left", u0 + td + tw, v0 + td, td, th, 0.84, (x1, y1, z1), (0.0, 0.0, -bd), (0.0, -bh, 0.0), (1.0, 0.0, 0.0)),
                ("top", u0 + td, v0, tw, td, 1.00, (x0, y1, z0), (bw, 0.0, 0.0), (0.0, 0.0, bd), (0.0, 1.0, 0.0)),
                ("bottom", u0 + td + tw, v0, tw, td, 0.58, (x0, y0, z1), (bw, 0.0, 0.0), (0.0, 0.0, -bd), (0.0, -1.0, 0.0)),
            ]

            min_alpha = 40 if is_overlay else 32
            tol = 22 if fast_drag else 3

            for _fname, fu, fv, uw, vh, shade, orig, uvec, vvec, norm in faces:
                nx, ny, nz = norm
                if rot_x != 0.0:
                    ny = norm[1] * cr - norm[2] * sr
                    nz = norm[1] * sr + norm[2] * cr
                cam_nz = (-nx * sy_yaw + nz * cy_yaw) * cx_pit + ny * sx_pit
                if cam_nz <= -0.05:
                    continue

                # 2D Greedy Mesh: merge adjacent similar-color texels on this face for fast rendering!
                visited = [[False] * uw for _ in range(vh)]
                for ty in range(vh):
                    v_coord = fv + ty
                    if v_coord < 0 or v_coord >= 64:
                        continue
                    for tx in range(uw):
                        if visited[ty][tx]:
                            continue
                        u_coord = fu + tx
                        if u_coord < 0 or u_coord >= 64:
                            continue
                        r, g, b, al = self.skin_grid[v_coord][u_coord]
                        if al < min_alpha:
                            visited[ty][tx] = True
                            continue

                        # Expand width (rw)
                        rw = 1
                        while tx + rw < uw and not visited[ty][tx + rw]:
                            nr, ng, nb, nal = self.skin_grid[v_coord][fu + tx + rw]
                            if nal >= min_alpha and abs(nr - r) <= tol and abs(ng - g) <= tol and abs(nb - b) <= tol:
                                rw += 1
                            else:
                                break

                        # Expand height (rh)
                        rh = 1
                        while ty + rh < vh and fv + ty + rh < 64:
                            row_ok = True
                            for k in range(rw):
                                if visited[ty + rh][tx + k]:
                                    row_ok = False
                                    break
                                nr, ng, nb, nal = self.skin_grid[fv + ty + rh][fu + tx + k]
                                if nal < min_alpha or abs(nr - r) > tol or abs(ng - g) > tol or abs(nb - b) > tol:
                                    row_ok = False
                                    break
                            if row_ok:
                                rh += 1
                            else:
                                break

                        for dy in range(rh):
                            for dx in range(rw):
                                visited[ty + dy][tx + dx] = True

                        f_u0 = tx / uw
                        f_u1 = (tx + rw) / uw
                        f_v0 = ty / vh
                        f_v1 = (ty + rh) / vh

                        p00 = local_to_world(
                            orig[0] + uvec[0] * f_u0 + vvec[0] * f_v0,
                            orig[1] + uvec[1] * f_u0 + vvec[1] * f_v0,
                            orig[2] + uvec[2] * f_u0 + vvec[2] * f_v0,
                        )
                        p10 = local_to_world(
                            orig[0] + uvec[0] * f_u1 + vvec[0] * f_v0,
                            orig[1] + uvec[1] * f_u1 + vvec[1] * f_v0,
                            orig[2] + uvec[2] * f_u1 + vvec[2] * f_v0,
                        )
                        p11 = local_to_world(
                            orig[0] + uvec[0] * f_u1 + vvec[0] * f_v1,
                            orig[1] + uvec[1] * f_u1 + vvec[1] * f_v1,
                            orig[2] + uvec[2] * f_u1 + vvec[2] * f_v1,
                        )
                        p01 = local_to_world(
                            orig[0] + uvec[0] * f_u0 + vvec[0] * f_v1,
                            orig[1] + uvec[1] * f_u0 + vvec[1] * f_v1,
                            orig[2] + uvec[2] * f_u0 + vvec[2] * f_v1,
                        )

                        s00 = transform_pt(*p00)
                        s10 = transform_pt(*p10)
                        s11 = transform_pt(*p11)
                        s01 = transform_pt(*p01)

                        z_avg = (s00[2] + s10[2] + s11[2] + s01[2]) * 0.25
                        if is_overlay:
                            z_avg += 0.12
                        sr_c = min(255, int(r * shade))
                        sg_c = min(255, int(g * shade))
                        sb_c = min(255, int(b * shade))
                        col = f"#{sr_c:02x}{sg_c:02x}{sb_c:02x}"
                        polys.append((
                            z_avg,
                            [s00[0], s00[1], s10[0], s10[1], s11[0], s11[1], s01[0], s01[1]],
                            col,
                        ))

        # Base Body Parts
        add_box(0.0, 12.0, 0.0, 8.0, 8.0, 8.0, 0, 0, 8, 8, 8)
        add_box(0.0, 2.0, 0.0, 8.0, 12.0, 4.0, 16, 16, 8, 12, 4)
        arm_x = 4.0 + arm_w * 0.5
        add_box(-arm_x, 2.0, 0.0, float(arm_w), 12.0, 4.0, 40, 16, arm_w, 12, 4, pivot_y=7.0, rot_x=swing)
        add_box(arm_x, 2.0, 0.0, float(arm_w), 12.0, 4.0, 32, 48, arm_w, 12, 4, pivot_y=7.0, rot_x=-swing)
        add_box(-2.0, -10.0, 0.0, 4.0, 12.0, 4.0, 0, 16, 4, 12, 4, pivot_y=-4.0, rot_x=-swing)
        add_box(2.0, -10.0, 0.0, 4.0, 12.0, 4.0, 16, 48, 4, 12, 4, pivot_y=-4.0, rot_x=swing)

        # Outer 3D Layers (Hat, Jacket, Sleeves, Pants)
        if self.outer_layers:
            add_box(0.0, 12.0, 0.0, 8.9, 8.9, 8.9, 32, 0, 8, 8, 8, is_overlay=True)
            add_box(0.0, 2.0, 0.0, 8.5, 12.5, 4.5, 16, 32, 8, 12, 4, is_overlay=True)
            add_box(-arm_x, 2.0, 0.0, arm_w + 0.5, 12.5, 4.5, 40, 32, arm_w, 12, 4, pivot_y=7.0, rot_x=swing, is_overlay=True)
            add_box(arm_x, 2.0, 0.0, arm_w + 0.5, 12.5, 4.5, 48, 48, arm_w, 12, 4, pivot_y=7.0, rot_x=-swing, is_overlay=True)
            add_box(-2.0, -10.0, 0.0, 4.5, 12.5, 4.5, 0, 32, 4, 12, 4, pivot_y=-4.0, rot_x=-swing, is_overlay=True)
            add_box(2.0, -10.0, 0.0, 4.5, 12.5, 4.5, 0, 48, 4, 12, 4, pivot_y=-4.0, rot_x=swing, is_overlay=True)

        polys.sort(key=lambda item: item[0])
        for _z, coords, col in polys:
            self.canvas.create_polygon(coords, fill=col, outline=col)

        # Clean White Options in the Top-Left Corner of the 3D Canvas (Seamless, clickable)
        arm_str = "Slim (3px)" if self.current_slim else "Default (4px)"
        pose_str = "ON" if self.walk_pose else "OFF"
        layer_str = "ON" if self.outer_layers else "OFF"
        self.canvas.create_text(8, 8, text=f"Arms: {arm_str}", anchor="nw", fill="#ffffff", font=("Segoe UI", 8, "bold"))
        self.canvas.create_text(8, 28, text=f"Walk Pose: {pose_str}", anchor="nw", fill="#ffffff", font=("Segoe UI", 8, "bold"))
        self.canvas.create_text(8, 48, text=f"3D Layers: {layer_str}", anchor="nw", fill="#ffffff", font=("Segoe UI", 8, "bold"))
        self.canvas.create_text(8, 68, text="Reset View", anchor="nw", fill="#ffffff", font=("Segoe UI", 8))


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
                "default_ram_gb": 6,
            },
        )
        self.state = load_json(
            STATE_PATH,
            {
                "nick": "",
                "uuid": "",
                "ram_gb": self.cfg.get("default_ram_gb", 6),
                "install_root": DEFAULT_INSTALL_ROOT,
                "skin_mode": "mojang",
                "skin_slim": False,
                "skin_preset_name": "",
                "skin_png_b64": "",
            },
        )
        if not self.state.get("install_root"):
            self.state["install_root"] = DEFAULT_INSTALL_ROOT

        self.busy = False
        self.ui_queue: queue.Queue = queue.Queue()
        self._icons: list[tk.PhotoImage] = []
        self._avatar_img: tk.PhotoImage | None = None
        self._mojang_skin_bytes: bytes | None = None
        self._mojang_skin_slim: bool = False
        self._studio_win: SkinStudioWindow | None = None
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

        if self.state.get("skin_mode") == "custom" and self.state.get("skin_png_b64"):
            try:
                raw_png = base64.b64decode(self.state["skin_png_b64"])
                self._set_avatar_from_grid(decode_skin_png(raw_png))
                self._write_client_skin_config()
            except Exception:
                pass

        initial_nick = (self.state.get("nick") or "").strip()
        if RE_VALID_NICK.match(initial_nick):
            self._trigger_lookup(initial_nick)
        self._ping_busy = False
        self.root.after(200, self._schedule_server_ping)

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

        self.srv_badge = tk.Label(
            hdr,
            text="● Checking...",
            font=("Segoe UI", 8, "bold"),
            bg=SURFACE,
            fg=MUTED,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=8,
            pady=4,
        )
        self.srv_badge.pack(side="right", anchor="center")

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
            cursor="hand2",
        )
        self.avatar_lbl.pack(side="left", padx=(0, 14))
        self.avatar_lbl.bind("<Button-1>", lambda _e: self._open_skin_studio())

        nick_col = tk.Frame(acct, bg=SURFACE)
        nick_col.pack(side="left", fill="x", expand=True)

        nick_top = tk.Frame(nick_col, bg=SURFACE)
        nick_top.pack(fill="x")
        tk.Label(nick_top, text="PLAYER NICKNAME & SKIN", font=("Segoe UI", 7, "bold"), bg=SURFACE, fg=MUTED).pack(side="left")
        make_button(
            nick_top,
            "👕 Skin Studio (3D)",
            GOLD_BTN,
            GOLD_HOVER,
            GOLD_FG,
            self._open_skin_studio,
            10,
            2,
            8,
        ).pack(side="right")

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
            text="Type a valid nick (3–16 chars) or open 3D Skin Studio",
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
        self.ram_var = tk.StringVar(value=f"{self.state.get('ram_gb', 6)} GB")
        ttk.Combobox(
            opts,
            textvariable=self.ram_var,
            values=["4 GB", "6 GB", "8 GB", "10 GB", "12 GB"],
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

    def _schedule_server_ping(self) -> None:
        if not self._ping_busy:
            self._ping_busy = True
            targets = [
                self.cfg.get("server_address", ""),
                "25.20.236.131:25565",
                "192.168.1.77:25565",
            ]
            def _run() -> None:
                try:
                    st, onl, mx = check_nest_server_status(targets)
                    def _apply() -> None:
                        if st == "online":
                            self.srv_badge.configure(text=f"● Online ({onl}/{mx})", fg=OK_GREEN, highlightbackground="#356844")
                        elif st == "starting":
                            self.srv_badge.configure(text="◐ Starting...", fg=ACCENT, highlightbackground="#8c5a16")
                        else:
                            self.srv_badge.configure(text="● Offline", fg=ERR_RED, highlightbackground="#6b2c2c")
                    self._safe_ui(_apply)
                finally:
                    self._ping_busy = False
            threading.Thread(target=_run, daemon=True).start()
        self.root.after(6000, self._schedule_server_ping)

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
        if self.state.get("skin_mode") == "custom" and self.state.get("skin_png_b64"):
            return
        self._avatar_img = None
        self.avatar_lbl.configure(image="", text="?", width=4, height=2)

    def _set_avatar_from_grid(self, grid: list[list[tuple[int, int, int, int]]]) -> None:
        try:
            img = render_head_avatar_photoimage(grid, size=36)
            self._avatar_img = img
            self.avatar_lbl.configure(image=img, text="", width=36, height=36)
        except Exception:
            pass

    def _open_skin_studio(self) -> None:
        if self._studio_win is not None and self._studio_win.winfo_exists():
            self._studio_win.lift()
            self._studio_win.focus_force()
            return
        self._studio_win = SkinStudioWindow(self)

    def apply_skin_from_studio(
        self,
        mode: str,
        slim: bool,
        preset_name: str,
        png_bytes: bytes | None,
        grid: list[list[tuple[int, int, int, int]]],
    ) -> None:
        self.state["skin_mode"] = mode
        self.state["skin_slim"] = bool(slim)
        self.state["skin_preset_name"] = preset_name
        self.state["skin_png_b64"] = base64.b64encode(png_bytes).decode("ascii") if png_bytes else ""
        save_json(STATE_PATH, self.state)

        self._write_client_skin_config()
        self._set_avatar_from_grid(grid)

        arm_txt = "Slim 3px" if slim else "Default 4px"
        if mode == "custom":
            tag = f"Preset '{preset_name}'" if preset_name else "Custom skin"
            self.acct_status.configure(text=f"{tag} equipped ({arm_txt}) · synced to game", fg=OK_GREEN)
            self._set_status(f"Skin equipped: {tag} ({arm_txt}).", OK_GREEN)
        else:
            nick = self.nick_var.get().strip() or self.state.get("nick", "Player")
            self.acct_status.configure(text=f"Auto Nickname Skin ({nick} · {arm_txt})", fg=OK_GREEN)
            self._set_status(f"Set to automatic nickname skin ({nick}).", OK_GREEN)

    def _write_client_skin_config(self) -> None:
        mode = self.state.get("skin_mode", "mojang")
        slim = bool(self.state.get("skin_slim", False))
        b64 = self.state.get("skin_png_b64", "")
        preset_name = self.state.get("skin_preset_name", "")

        # Even in mojang mode, if we already fetched the official Mojang PNG for this nickname,
        # include it so offline-mode servers & singleplayer have the texture immediately!
        effective_mode = mode
        if mode == "mojang" and self._mojang_skin_bytes:
            effective_mode = "custom"
            slim = self._mojang_skin_slim
            b64 = base64.b64encode(self._mojang_skin_bytes).decode("ascii")

        payload = {
            "mode": effective_mode,
            "slim": slim,
            "preset_name": preset_name,
            "png_base64": b64,
        }
        target_dirs = [os.path.join(self.game_dir, "config")]
        cf_cfg_dir = r"C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition\config"
        if os.path.exists(os.path.dirname(cf_cfg_dir)):
            target_dirs.append(cf_cfg_dir)

        for d in target_dirs:
            try:
                os.makedirs(d, exist_ok=True)
                save_json(os.path.join(d, "nest_skin_client.json"), payload)
            except Exception:
                pass

    def _trigger_lookup(self, nick: str) -> None:
        self._debounce_id = None
        self._lookup_seq += 1
        seq = self._lookup_seq
        threading.Thread(target=self._lookup_nick_worker, args=(nick, seq), daemon=True).start()

    def _lookup_nick_worker(self, nick: str, seq: int) -> None:
        resolved_name, uid, is_official, skin_png, is_slim = fetch_mojang_skin_png(nick)
        if seq != self._lookup_seq:
            return
        self._last_looked_up = resolved_name
        self.state["nick"] = resolved_name
        self.state["uuid"] = uid
        self._mojang_skin_bytes = skin_png
        self._mojang_skin_slim = is_slim

        if self.state.get("skin_mode", "mojang") == "mojang" and skin_png:
            self.state["skin_slim"] = is_slim
            self.state["skin_png_b64"] = base64.b64encode(skin_png).decode("ascii")
        save_json(STATE_PATH, self.state)
        self._write_client_skin_config()

        avatar_bytes = None
        if is_official and not skin_png:
            try:
                avatar_bytes = http_get_bytes(HEAD_AVATAR_URL.format(ident=uid), timeout=8)
            except Exception:
                avatar_bytes = None

        def _update_ui() -> None:
            if seq != self._lookup_seq:
                return
            custom_active = self.state.get("skin_mode") == "custom" and bool(self.state.get("skin_png_b64"))
            if custom_active:
                arm_txt = "Slim" if self.state.get("skin_slim") else "Default"
                pname = self.state.get("skin_preset_name") or "Custom skin"
                self.acct_status.configure(
                    text=f"{pname} ({arm_txt}) · {'Account matched' if is_official else 'Offline nick'} ({resolved_name})",
                    fg=OK_GREEN,
                )
                try:
                    raw = base64.b64decode(self.state["skin_png_b64"])
                    self._set_avatar_from_grid(decode_skin_png(raw))
                except Exception:
                    pass
                return

            if is_official:
                arm_txt = "Slim" if is_slim else "Default"
                self.acct_status.configure(text=f"Account matched ({resolved_name}) · {arm_txt} skin loaded", fg=OK_GREEN)
            else:
                self.acct_status.configure(text=f"Offline nick ({resolved_name}) · open Skin Studio to set skin", fg=ACCENT)

            if skin_png:
                self._set_avatar_from_grid(decode_skin_png(skin_png))
            elif avatar_bytes:
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
            resolved_name, uid, _ok, skin_png, is_slim = fetch_mojang_skin_png(self.state["nick"])
            self.state["nick"], self.state["uuid"] = resolved_name, uid
            if skin_png:
                self._mojang_skin_bytes = skin_png
                self._mojang_skin_slim = is_slim
            save_json(STATE_PATH, self.state)

            self._sync_from_github()
            self._write_client_skin_config()
            if launch_after:
                java_exe, install_dir = self._ensure_runtime()
                self._launch_game(java_exe, install_dir)
            else:
                self._set_status("Modpack is up to date.", OK_GREEN, 100)
        except _SelfUpdateTriggered:
            self._safe_ui(lambda: self.root.after(150, self.root.destroy))
            return
        except Exception as exc:
            self.busy = False
            self._set_status(f"Error: {exc}", ERR_RED)
            self._safe_ui(lambda: self.play_btn.configure(state="normal", text="PLAY"))
            self._safe_ui(lambda msg=str(exc): messagebox.showerror("Launcher Error", msg))
            return
        self.busy = False
        self._safe_ui(lambda: self.play_btn.configure(state="normal", text="PLAY"))

    def _check_self_update(self, manifest: dict) -> None:
        if not getattr(sys, "frozen", False):
            return
        remote_sha = str(manifest.get("launcher_sha256") or "").strip().lower()
        remote_url = str(manifest.get("launcher_url") or self.cfg.get("launcher_url") or "").strip()
        if not remote_sha or not remote_url or "CHANGE_ME_" in remote_url:
            return
        current_exe = sys.executable
        if not os.path.exists(current_exe):
            return
        local_sha = sha256_file(current_exe).lower()
        if local_sha == remote_sha:
            return

        new_ver = manifest.get("launcher_version", "new")
        self._set_status(f"Updating launcher to v{new_ver}...", ACCENT, 12)
        os.makedirs(STATE_DIR, exist_ok=True)
        tmp_exe = os.path.join(STATE_DIR, "TheNestLauncher.new.exe")
        download_file(remote_url, tmp_exe, remote_sha)

        cmd_path = os.path.join(STATE_DIR, "update_launcher.cmd")
        bat = (
            "@echo off\n"
            "set /a tries=0\n"
            ":waitloop\n"
            "timeout /t 1 /nobreak >nul\n"
            f'move /y "{tmp_exe}" "{current_exe}" >nul 2>&1\n'
            "if not errorlevel 1 goto launch\n"
            "set /a tries+=1\n"
            "if %tries% GEQ 15 goto end\n"
            "goto waitloop\n"
            ":launch\n"
            f'start "" "{current_exe}"\n'
            ":end\n"
            'del /f /q "%~f0" >nul 2>&1\n'
        )
        with open(cmd_path, "w", encoding="utf-8") as f:
            f.write(bat)

        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        subprocess.Popen(["cmd.exe", "/c", cmd_path], close_fds=True, creationflags=flags)
        self._set_status("Launcher updated! Restarting...", OK_GREEN, 100)
        raise _SelfUpdateTriggered()

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

        if manifest.get("server_address"):
            self.cfg["server_address"] = manifest["server_address"]

        ver = manifest.get("pack_version", self.cfg.get("pack_version", "1.0.0"))
        self._safe_ui(lambda: self.ver_lbl.configure(
            text=f"v{ver} · MC {manifest.get('mc_version', '26.3')} · NeoForge {manifest.get('neoforge_version', '26.3.0.103')}"
        ))

        self._check_self_update(manifest)

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
                    if rel not in expected and mdir in ("mods", "resourcepacks") and not fn.lower().startswith("nest_txadmin"):
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
        requested_ram_gb = int(self.state.get("ram_gb", 6))
        ram_gb, ram_note = resolve_safe_ram_gb(requested_ram_gb)
        xms_mb = min(1024, ram_gb * 512)

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

        # G1GC avoids ZGC's huge multi-mapped virtual/commit reservation on Windows alongside Voxy off-heap RAM
        jvm_args = [
            f"-Xmx{ram_gb * 1024}m",
            f"-Xms{xms_mb}m",
            "-XX:+UseG1GC",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:G1NewSizePercent=20",
            "-XX:G1ReservePercent=20",
            "-XX:MaxGCPauseMillis=50",
            "-XX:G1HeapRegionSize=32M",
            "-XX:+DisableExplicitGC",
            f"-Dminecraft.applet.TargetDirectory={game_dir}",
            "-Dfml.ignorePatchDiscrepancies=true",
            "-Dfml.ignoreInvalidMinecraftCertificates=true",
        ]
        for arg in mc_json.get("arguments", {}).get("jvm", []) + nf_json.get("arguments", {}).get("jvm", []):
            if isinstance(arg, str):
                a = (
                    arg.replace("${natives_directory}", natives_dir)
                    .replace("${launcher_name}", "TheNestLauncher")
                    .replace("${launcher_version}", self.cfg.get("launcher_version", "1.2.0"))
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

        status_msg = f"Launching as {self.state['nick']} ({ram_gb} GB)..."
        if ram_note:
            status_msg = f"{ram_note} · Launching..."
        self._set_status(status_msg, OK_GREEN, 100)
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        subprocess.Popen(
            [java_exe] + jvm_args + [nf_json["mainClass"]] + game_args,
            cwd=game_dir,
            close_fds=True,
            creationflags=flags,
        )
        self._safe_ui(lambda: self.root.after(1200, self.root.destroy))


if __name__ == "__main__":
    app_root = tk.Tk()
    NestLauncher(app_root)
    app_root.mainloop()
