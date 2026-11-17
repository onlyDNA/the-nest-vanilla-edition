# Project Rules: The Nest Vanilla Edition (Minecraft 26.3 Modpack)

## 1. Project Identity & Core Specs
- **Modpack Name:** The Nest Vanilla edition
- **Target Game Version:** Minecraft Java Edition `26.3` (Wilderness Bound drop)
- **Target Platform / Launcher:** CurseForge App (`26.3` profile / `manifest.json` + `overrides/` packaging)
- **Live CurseForge Instance Path:** `C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition`
- **Primary Mod Loader:** **NeoForge** (`26.3.0.103`) (with **Sinytra Connector** + **Forgified Fabric API** or native NeoForge bridge for Fabric compatibility)
- **Target Audience:** Community multiplayer server + seamless singleplayer experience

---

## 2. Mod Loader & Voxy + ImmersiveVFX Architecture Rules (CRITICAL)

### Rule 2.1: Use NeoForge, NOT Legacy Forge
- Always target **NeoForge** for Minecraft `26.3` when combining Forge-ecosystem mods with Fabric mods.
- **Why:** **ImmersiveVFX**, **Sodium**, **Sinytra Connector**, and **Forgified Fabric API** actively target **NeoForge**. Legacy Forge lacks modern Connector support and will fail to bridge Voxy.

### Rule 2.2: Voxy + ImmersiveVFX Rendering Stack Constraints
- **Client-Only Rendering Stack:** Never include `Voxy`, `ImmersiveVFX`, `Sodium`, or `EntityCulling` in the dedicated server `mods/` folder.
- **Use Sodium, NEVER Embeddium:** Both **Voxy** and **ImmersiveVFX** hook directly into **Sodium**'s rendering pipeline (e.g., Sodium `v0.9.3+` on NeoForge). Do not substitute Embeddium.
- **Do NOT Install Iris Shaders Alongside ImmersiveVFX:** **ImmersiveVFX** (by Shinyflvres) functions as an all-in-one visual overhaul with its own built-in lightweight shaders, independent shadow casters, biome fog, water foam/caustics, and native **Voxy** (including Voxy SeedGen) integration. Installing **Iris Shaders** alongside **ImmersiveVFX** will cause rendering pipeline conflicts.
- **Bridging Voxy on NeoForge 26.3:** Follow this priority order when configuring Voxy:
  1. **Option A (Preferred for Stability):** Native **Sodium (NeoForge)** + **ImmersiveVFX (NeoForge)** + a dedicated NeoForge Voxy port or **Roxy** compatibility bridge if available for `26.3`.
  2. **Option B (Connector Bridge):** **Sinytra Connector** + **Forgified Fabric API** + compatible **Sodium** build + **ImmersiveVFX** + **Voxy (Fabric)**.
- **CurseForge Packaging for Voxy:** Because Voxy builds are commonly distributed via Modrinth or compiled from GitHub rather than hosted on the CurseForge mod repository, place the Voxy `.jar` inside `overrides/mods/` when exporting for community distribution. (**ImmersiveVFX** is hosted directly on CurseForge and will be fetched automatically via `manifest.json`!)

---

## 3. "Vanilla Edition" Design & Mod Selection Rules

Every mod proposed or added to **The Nest Vanilla edition** must pass the **Vanilla+ Filter**:

1. **100% Vanilla World-Save Guarantee:** Do **not** add mods that inject custom block IDs, custom biomes, or custom worldgen structures. The server world must remain 100% Vanilla `26.3` compatible so the community world is never locked to a mod and can upgrade cleanly to future Minecraft drops.
2. **Preserve Vanilla Progression:** No tech trees, power generation, custom ore bloat, or overpowered gear that invalidates Vanilla `26.3` mechanics.
3. **Core Approved Feature Pillars:**
   - **Distant LODs & Visual Overhaul:** `Sodium` + `Voxy` + `ImmersiveVFX` (replaces Iris Shaders, AmbientSounds, and separate particle mods in one lightweight package with native Voxy support).
   - **Proximity Voice & Audio:** `Simple Voice Chat` + `Sound Physics Remastered`.
   - **Navigation:** `Xaero's Minimap` (Fair-Play mode recommended for multiplayer balance) + `Xaero's World Map`.
4. **Multiplayer-First Stability:** Mods must not cause server TPS lag during chunk generation or entity ticking.
5. **Zero Keybind Conflicts on First Boot:** Every newly added mod with keybinds (especially Voxy, ImmersiveVFX config, Simple Voice Chat, and Xaero's Map/Waypoints) must have its default controls audited and saved via `Default Options` before release.
6. **Mandatory Side Tagging:** Every mod added to `MODLIST_TRACKER.md` must be explicitly tagged as:
   - `[CLIENT]` — Rendering, LOD (Voxy), HUD, audio, shaders, camera, keybind helpers. **Excluded from Server Pack.**
   - `[SERVER]` — Backup utilities, spark/profiling, chunk pre-generators, server-only admin/permissions. **Optional/Excluded from Client Pack.**
   - `[BOTH]` — Gameplay QoL, voice chat (Simple Voice Chat), network optimization, shared libraries, and vanilla+ blocks/worldgen. **Required on both Client and Server.**

---

## 4. Configuration & File Structure Standards
- Keep all tracked modpack documentation, mod lists, and export checklists updated in the workspace root:
  - `WORKFLOW_AND_RULES.md` — Master design, configuration, and release runbook.
  - `MODLIST_TRACKER.md` — Canonical registry of all mods, sides, loader types (NeoForge vs Fabric-via-Connector), and status.
  - `overrides/` — Staging directory for custom `config/`, `defaultconfigs/`, `resourcepacks/`, `shaderpacks/`, and manual `mods/` (like Voxy).
  - `assets/branding/` — Profile pictures, CurseForge pack icons (`400x400` / `1024x1024` `.png`), and server icons (`64x64` `server-icon.png`).
