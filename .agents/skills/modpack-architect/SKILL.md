---
name: modpack-architect
description: >-
  Step-by-step workflow for designing, configuring, troubleshooting Voxy on NeoForge,
  and packaging "The Nest Vanilla edition" modpack for CurseForge 26.3 and community servers.
  Use this skill whenever adding mods, auditing configs, fixing crashes, or preparing a release.
---

# Modpack Architect Skill: The Nest Vanilla Edition (26.3)

Use this workflow to guide the user through designing, configuring, testing, and exporting **The Nest Vanilla edition** for Minecraft `26.3` on CurseForge.

## Workflow Stages

### Stage 1: Mod Vetting & Addition
Whenever the user wants to add a mod or asks for mod recommendations:
1. **Check the Vanilla+ Filter (`GEMINI.md`):** Does it preserve vanilla progression and aesthetics?
2. **Verify Loader Compatibility (`26.3`):**
   - Prefer native **NeoForge `26.3`** builds whenever available.
   - Only use **Fabric `26.3`** builds (via **Sinytra Connector** + **Forgified Fabric API**) when no NeoForge version exists (such as **Voxy** or specific client-only ambiance mods).
3. **Classify Side Requirement:** Tag as `[CLIENT]`, `[SERVER]`, or `[BOTH]`.
4. **Update Tracker:** Log the mod in `MODLIST_TRACKER.md` with its side, loader, and whether it is fetched via `manifest.json` (CurseForge) or placed in `overrides/mods/`.

### Stage 2: Voxy + NeoForge Setup & Crash Triage
When setting up or troubleshooting **Voxy** in the CurseForge `26.3` NeoForge profile:
1. **Verify Core Rendering Stack:**
   - Ensure **Sodium** + **ImmersiveVFX** are installed (never Embeddium, and **never Iris Shaders alongside ImmersiveVFX**).
   - Check whether a native NeoForge Voxy fork / **Roxy** bridge is available for `26.3`, or if running Fabric Voxy through **Sinytra Connector** + **Forgified Fabric API**.
2. **Audit `latest.log` / `crash-report` on Failure:**
   - Look for `MixinApplyError` or `MixinTransformerError` referencing `me.cortex.voxy` or `net.caffeinemc.mods.sodium`.
   - Verify Voxy's default config (`config/voxy-config.json` or `config/voxy/`) has compatible thread counts for community members' CPUs (defaulting to conservative ingest/saving threads so 6–8 core CPUs don't stutter).

### Stage 3: Configuration & Branding Pass
1. **Branding Assets (`assets/branding/`):**
   - CurseForge Profile Picture / Icon: Square `.png` (`1024x1024` master, `400x400` min for CurseForge).
   - Dedicated Server Icon: `64x64` `.png` named `server-icon.png`.
2. **Default Client Configs (`overrides/config/` & `overrides/defaultconfigs/`):**
   - Configure **Default Options** (or strip player-specific UUID/account lines from `options.txt`) so keybinds, resource pack load order, and sensible video settings ship pre-configured.
   - Tune **Voxy** LOD render distance defaults (e.g., `64`–`128` LOD sections by default) so low/mid-spec community PCs boot smoothly and high-spec users can turn it up.

### Stage 4: CurseForge Client Export & Server Pack Build
1. **Client Export (`.zip`):**
   - Verify no disabled `.jar.disabled` files or world test saves (`saves/`) are checked unless intentionally shipping a template world.
   - Include `config/`, `defaultconfigs/`, `resourcepacks/`, `shaderpacks/`, and `mods/` (only for non-CF jars like Voxy if distributing directly to the community).
2. **Server Pack Generation:**
   - Copy all `[BOTH]` and `[SERVER]` mods + `config/` + `defaultconfigs/`.
   - **Strictly strip all `[CLIENT]` mods:** Voxy, Sodium, Iris, EntityCulling, ImmediatelyFast (client features), Zoom/Camera mods, Sound Physics/Ambiance client mods, and Sinytra Connector (if only used for client Fabric mods).
   - Provide a startup script (`run.bat` / `run.sh`) with Aikar's / ZGC flags tuned for Minecraft `26.3` (Java 21/25+).
