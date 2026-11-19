"""Snapshot the verified live instance into ./pack/ and generate ./pack-manifest.json for GitHub."""

import hashlib
import json
import os
import shutil
import time

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE_INSTANCE = r"C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition"
PACK_DIR = os.path.join(WORKSPACE_DIR, "pack")
MANIFEST_PATH = os.path.join(WORKSPACE_DIR, "pack-manifest.json")
LAUNCHER_CFG = os.path.join(WORKSPACE_DIR, "client_launcher", "launcher_config.json")
ALT_LAUNCHER_CFG = os.path.join(WORKSPACE_DIR, "client_launcher", "alt_launcher_config.json")
LAUNCHER_EXE_PATH = os.path.join(WORKSPACE_DIR, "release", "The Nest Launcher.exe")
ALT_LAUNCHER_EXE_PATH = os.path.join(WORKSPACE_DIR, "release", "The Nest Alt Launcher.exe")

MANAGED_DIRS = ("mods", "config", "resourcepacks", "defaultconfigs")
ROOT_FILES = ("servers.dat",)
SKIP_FILES = {
    "defaultoptions-local.toml",
    "inventoryessentials-local.toml",
    "nest_skin_client.json",
    "etf_warnings.json",
    "desktop.ini",
}
SKIP_EXTS = (".bak", ".tmp", ".log")


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def should_skip(rel_path: str) -> bool:
    name = os.path.basename(rel_path).lower()
    if name in SKIP_FILES or name.startswith("defaultoptions-local"):
        return True
    return name.endswith(SKIP_EXTS)


def sync_pack() -> dict:
    if not os.path.isdir(LIVE_INSTANCE):
        raise FileNotFoundError(f"Live instance not found: {LIVE_INSTANCE}")

    if os.path.exists(PACK_DIR):
        shutil.rmtree(PACK_DIR)
    os.makedirs(PACK_DIR, exist_ok=True)

    cfg = {}
    if os.path.exists(LAUNCHER_CFG):
        with open(LAUNCHER_CFG, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    files_meta: dict[str, dict] = {}
    total_bytes = 0

    for folder in MANAGED_DIRS:
        src_root = os.path.join(LIVE_INSTANCE, folder)
        if not os.path.exists(src_root):
            continue
        for root, _dirs, files in os.walk(src_root):
            for fname in files:
                src_file = os.path.join(root, fname)
                rel = os.path.relpath(src_file, LIVE_INSTANCE).replace("\\", "/")
                if should_skip(rel):
                    continue
                dst_file = os.path.join(PACK_DIR, rel.replace("/", os.sep))
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)
                size = os.path.getsize(dst_file)
                total_bytes += size
                files_meta[rel] = {
                    "sha256": sha256_file(dst_file),
                    "size": size,
                }

    for fname in ROOT_FILES:
        src_file = os.path.join(LIVE_INSTANCE, fname)
        if not os.path.isfile(src_file):
            continue
        dst_file = os.path.join(PACK_DIR, fname)
        shutil.copy2(src_file, dst_file)
        size = os.path.getsize(dst_file)
        total_bytes += size
        files_meta[fname] = {
            "sha256": sha256_file(dst_file),
            "size": size,
        }

    alt_cfg = {}
    if os.path.exists(ALT_LAUNCHER_CFG):
        with open(ALT_LAUNCHER_CFG, "r", encoding="utf-8") as f:
            alt_cfg = json.load(f)

    launcher_sha = sha256_file(LAUNCHER_EXE_PATH) if os.path.exists(LAUNCHER_EXE_PATH) else ""
    alt_launcher_sha = sha256_file(ALT_LAUNCHER_EXE_PATH) if os.path.exists(ALT_LAUNCHER_EXE_PATH) else ""
    manifest = {
        "pack_name": cfg.get("pack_name", "The Nest Vanilla Edition"),
        "pack_version": cfg.get("pack_version", "1.0.0"),
        "launcher_version": cfg.get("launcher_version", "1.1.0"),
        "launcher_sha256": launcher_sha,
        "launcher_url": cfg.get("launcher_url", ""),
        "alt_launcher_version": alt_cfg.get("launcher_version", "1.0.0"),
        "alt_launcher_sha256": alt_launcher_sha,
        "alt_launcher_url": alt_cfg.get("launcher_url", ""),
        "server_address": cfg.get("server_address", ""),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mc_version": cfg.get("mc_version", "26.3"),
        "neoforge_version": cfg.get("neoforge_version", "26.3.0.103"),
        "asset_index": cfg.get("asset_index", "34"),
        "managed_dirs": list(MANAGED_DIRS),
        "total_files": len(files_meta),
        "total_bytes": total_bytes,
        "files": dict(sorted(files_meta.items())),
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(
        f"Built {MANIFEST_PATH}: {manifest['total_files']} files "
        f"({total_bytes / (1024 * 1024):.2f} MB) -> ./pack/"
    )
    return manifest


if __name__ == "__main__":
    sync_pack()
