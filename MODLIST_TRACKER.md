# The Nest Vanilla Edition — Modlist & Compatibility Tracker (`26.3`)

> **Live Instance Directory:** `C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition`  
> **Mod Loader:** `neoforge-26.3.0.103`

Use this tracker to manage every mod in **The Nest Vanilla edition**, keep Client and Server packs cleanly separated, and track how each mod is packaged in CurseForge (`manifest.json` vs `overrides/mods/`).

## Legend
- **Side:**
  - `[CLIENT]` = Client-only (MUST be removed from Dedicated Server pack)
  - `[SERVER]` = Server-only (Optional on Client; used for server admin/backups/profiling)
  - `[BOTH]` = Required on both Client and Dedicated Server
- **Loader:**
  - `NeoForge` = Native NeoForge `26.3` `.jar`
  - `Fabric (Connector)` = Fabric `26.3` `.jar` loaded via Sinytra Connector / Bridge
- **Packaging:**
  - `CF Manifest` = Hosted on CurseForge; automatically fetched via `manifest.json`
  - `Overrides` = Placed in `overrides/mods/` (for non-CF mods like Voxy in community `.zip` builds)

---

## 1. Core Bridge & Rendering Stack (Phase 1 — Test First!)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Sodium** | Rendering Engine | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`sodium-neoforge-0.9.3-beta.5-mc26.3.jar`). Note: monitor Voxy `0.2.20-beta` compatibility on `beta.5` (`beta.4` was previously pinned for `DefaultChunkRenderer.render`). |
| **ImmersiveVFX** | Visual Overhaul & Lighting | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`ImmersiveVFX-2.3.0-neoforge.jar`). Built-in shaders/shadows, fog, particles & Voxy support. **Do NOT install Iris alongside it.** |
| **Entity Model Features (EMF)** | Entity Animation Engine | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`entity_model_features-3.3.12-26.3-neoforge.jar`). Powers Fresh Animations & FA Player models. |
| **Entity Texture Features (ETF)** | Entity Texture Engine | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`entity_texture_features-7.2.7-26.3-neoforge.jar`). Powers blinking eyes & random mob variants. |
| **Voxy** | LOD Rendering | `[CLIENT]` | `NeoForge` (Port) | `Overrides` | **Installed** (`voxy-0.2.20-beta-MC26.3.jar`). Native NeoForge `26.3` port—no Sinytra Connector required! Pairs natively with Sodium & ImmersiveVFX. |
| **Voxy Server Side (VSS)** | Distant LOD Generation & Sync | `[BOTH]` | `NeoForge` | `Overrides` | **Installed** (`voxy-server-side-neoforge-0.21.0+26.3.jar`). Generates & streams distant LOD terrain to Voxy clients without walking there first. |
| **Continuity** | Connected Textures | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`ContinuityNeoForge-3.0.11-26.3.jar`). Connected glass, sandstone, and bookshelf textures on Sodium. |
| **EntityCulling** | Rendering Opt | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`entityculling-neoforge-1.12.1-mc26.3.jar`). Skips rendering entities/block-entities behind walls. |
| **ImmediatelyFast** | Immediate Mode Opt | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`ImmediatelyFast-NeoForge-1.17.1+26.3.jar`). Optimizes HUD, text, and entity rendering calls. |
| **FerriteCore** | Memory Optimization | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`ferritecore-9.0.0-neoforge.jar`). Shrinks blockstate/model memory footprint (`578k+` blockstates) and reduces GC pauses. |
| **Lithium** | Game Logic & Tick Opt | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`lithium-neoforge-0.26.3+mc26.3.jar`). Optimizes chunk ticking, entity AI, collisions, hoppers, and worldgen math. |
| **ScalableLux** | Multi-Threaded Lighting | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`ScalableLux-neoforge-0.3.0-alpha.0.17-all.jar`). Starlight-based async lighting engine for faster world creation & chunk loads. |
| **ModernFix-mVUS** | Startup, Memory & Model Opt | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`modernfix-neoforge-5.27.23+mc26.3.jar`). Lazy DFU/search trees/dynamic resources (`578k+` blockstates), worldgen alloc & leak fixes. |
| **Dynamic FPS** | Idle Resource Saver | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`dynamic-fps-3.11.10+minecraft-26.3.0-neoforge.jar`). Cuts GPU/CPU usage when tabbed out or minimized. |
| **Alternate Current** | Redstone Engine Opt | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`alternate_current-mc26.3-1.9.0.jar`). Fast low-overhead redstone updates (`[SERVER]`/`[BOTH]`). |
| **ServerCore** | Tick & Mobcap Opt | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`servercore-neoforge-1.5.20+26.3.jar`). Dynamic activation range, breeding/mobcap tuning & faster chunk saves. |

---

## 2. Vanilla+ QoL, Worldgen & UI (Phase 2)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **JEI (Just Enough Items)** | Recipe Viewer | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`jei-26.3-neoforge-31.14.0.72.jar`). Clean recipe & item lookup. |
| **MezzConfig** | Library (JEI) | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`mezz_config-26.3-neoforge-0.7.1-standalone.jar`). Required dependency for JEI on `26.3`. |
| **Just Enough Professions (JEP)** | Villager JEI Addon | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`JustEnoughProfessions-neoforge-26.3-130.0.jar`). Shows Villager workstation blocks in JEI. |
| **Mouse Tweaks** | Inventory QoL | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`MouseTweaks-neoforge-mc26.3-2.31.jar`). Smooth drag-crafting and inventory wheel sorting. |
| **Cinematic Zoom** | Camera / Zoom | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`CinematicZoom-NeoForge-26.3-1.3.7.jar`). Smooth scrollable camera zoom. |
| **Diorama** | Map & Waypoints / Camera | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`diorama-0.10.2-neoforge-26.3.jar`). Primary in-game world map, minimap, waypoints, and diorama viewer (`M` Map, `B` New Waypoint, `Y` Waypoints). |
| **Crops Love Rain** | Farming QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`cropsloverain-3.2.2.jar`). Crops grow faster during rain. |
| **Leaves Be Gone** | World QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`leavesbegone-v26.3.0-mc26.3.x+neoforge.jar`). Clears tree leaves quickly after logging (uses PuzzlesLib; pairs with Timber). |
| **Weather Glass** | Weather / Immersion | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`weatherglass-0.6.2-26.3-neoforge.jar`). Requires **Architectury** (`architectury-neoforge-22.0.6.jar`). |
| **Architectury API** | Shared Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`architectury-neoforge-22.0.6.jar`). Required library for Weather Glass & cross-loader mods. |
| **Terralith** | Vanilla-Block Worldgen | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`Terralith_v2.6.5+26.3-neoforge.jar`). Uses 100% vanilla blocks for overhauled terrain. |
| **Lithostitched** | Worldgen Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`lithostitched-2.0.6-neoforge-26.3.jar`). Worldgen library. |
| **Streams Reflowing** | Flowing River Worldgen | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`StreamsReflowing-26.3-neoforge-2.17.5.jar`). Flowing rivers generation. |
| **Jade** | Block/Entity Tooltip | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`Jade-mc26.3-NeoForge-26.3.5.jar`). Shows what block/entity you are looking at; installed on server for inventory/beehive data. |
| **AppleSkin** | Hunger/Saturation UI | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`appleskin-neoforge-mc26.3-3.0.10.jar`). Shows food saturation and exhaustion on the vanilla hunger bar. |
| **Enchantment Descriptions** | Tooltip QoL | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`EnchantmentDescriptions-neoforge-MC26.3-26.3.0.2.jar`). Shows enchantment info in tooltips (requires **PrickleMC**). |
| **PrickleMC** | Library (Enchantment Desc. & TrampleNoMore) | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`PrickleMC-neoforge-MC26.3-26.3.0.2.jar`). Required library for Enchantment Descriptions & TrampleNoMore (`BOTH`) on `26.3`. |
| **Controlling** | Keybind Manager | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`Controlling-neoforge-26.3-26.3.4.jar`). Search keybinds by key name and filter conflicts. |
| **Default Options** | Pack Configuration | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`defaultoptions-neoforge-26.3-26.3.0.1.jar`). Ships pre-configured conflict-free keybinds & settings in `config/defaultoptions/` without overwriting user edits. |
| **FancyMenu** | Main Menu & UI Customization | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`fancymenu_neoforge_3.10.0_MC_26.3.jar`) — Custom sunset & Nest emblem Main Menu (`the_nest_title_screen.txt`) + assets in `config/fancymenu/`. |
| **Drippy Loading Screen** | Custom Loading Screen | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`drippyloadingscreen_neoforge_3.1.6_MC_26.3.jar`) — Custom loading overlay (`the_nest_loading_screen.txt`) & `options.txt` synced to `overrides/config/`. |
| **Konkrete** | Library (FancyMenu / Drippy) | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`konkrete_neoforge_1.11.1_MC_26.3.jar`) — Required core library for FancyMenu & Drippy Loading Screen. |
| **Melody** | Library (FancyMenu Audio) | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`melody_neoforge_1.0.17_MC_26.3.jar`) — OpenAL audio engine required by FancyMenu. |

---

## 3. Community Multiplayer, Audio & Animations (Phase 2)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Simple Voice Chat** | Proximity Voice | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`voicechat-neoforge-2.6.27+26.3.jar`). Requires UDP port (default `24454`) open on server. |
| **Sound Physics Remastered** | Audio Immersion | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`sound-physics-remastered-neoforge-1.5.2+26.3.jar`). Cave reverb and sound occlusion. |
| **Simple Voice Chat: Voice Physics** | Audio Immersion Bridge | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`voice-physics-forge-neoforge-2.12.6-mc1.16.5-26.x.jar`). Bridges Simple Voice Chat with Sound Physics. |
| **Talking Heads** | Voice Animation | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Removed** (`talking-heads-1.1.4+26.3+neoforge.jar`). Replaced by **The Nest Talk Lines** (`nest_talklines`). |
| **The Nest Talk Lines** | RobRun-Style Speaking Lines | `[CLIENT]` | `NeoForge` | `overrides/mods/` | **Installed** (`nest_talklines-1.0.0-neoforge-26.3.jar`). Renders 3 pulsing comic/RobRun-style radiating speaking lines attached to a player's head while talking via Simple Voice Chat (`TalkLinesVoicePlugin` + `TalkLinesLayer`). |
| **AmbiMod** | Ambient Audio | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`ambimod-neoforge-1.1.0.jar`). Dynamic biome ambient audio (bundles Cloth Config `26.3.159`). |
| **Chat Heads** | Multiplayer Chat UI | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`chat_heads-1.3.2-neoforge-26.3.jar`). Renders player skin heads next to chat messages. |
| **3D Skin Layers** | Player Visuals | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`skinlayers3d-neoforge-1.11.4-mc26.3.jar`). Turns flat outer skin layers into 3D voxel geometry. |
| **Punchy!** | 1st-Person Animations | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`punchy-3.2b-neoforge-26.3.jar`). Fluid first-person hand & held-item animations. |
| **Punchy! Moves** | 3rd-Person Animations & Camera | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`punchy-moves-1.0.9-neoforge-26.3.jar`). Third-person player animations, emotes & shoulder camera (paired with *Fluid & Foolish*). |
| **Effectual** | Visual / Ambient Effects | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`effectual-neoforge-1.4.2-26.3.jar`). Client-side visual effects (requires **TLib**). |
| **TLib** | Library (Effectual) | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`tlib-neoforge-1.5.0-26.3.jar`). Required dependency for Effectual. |
| **Sounds** | Inventory / UI / Item SFX | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`sounds-2.6.0+26.3-neoforge.jar`). Satisfying item hover, drag/drop, hotbar & UI sounds (requires **MRU** + **YACL**). |
| **MRU** | Library (Sounds) | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`mru-1.0.45+26.3-neoforge.jar`). Required dependency for Sounds. |
| **YetAnotherConfigLib (YACL)** | Config Library | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`yet_another_config_lib_v3-3.9.7+26.3-neoforge.jar`). Required dependency for Sounds. |
| **Music Disc Maker** | Custom Music Discs / Boombox / FM Radio | `[BOTH]` | `NeoForge` | `overrides/mods/` | **Installed & Patched** (`music_disc_maker-3.1.4-neoforge-26.3.jar`). Patched `DiscSoundInstance` & `music_disc_maker.mixins.json` for directional attenuation, and merged the custom **FM Radio** (`music_disc_maker:fm_radio` with Blockbench 3D model, `Portugal (PT)` / `PT & BR` / `English` / `Worldwide` live FM directory, Favorites, Custom URL, Volume/Range/3D Audio). |

---

## 4. Installed Resource Packs (`resourcepacks/` — Staged in `overrides/resourcepacks/`)

| Resource Pack | Category | Side | Required Mods | Status |
| :--- | :--- | :---: | :---: | :--- |
| **Fresh Animations (`v1.11.2_26.1`)** | Mob & Villager Animations | `[CLIENT]` | `EMF` + `ETF` | **Installed** (`FreshAnimations_v1.11.2_26.1.zip`) — **MUST load below** *FA: All Extensions* |
| **FA: All Extensions (`v1.10.1`)** | Mob & Villager Extensions | `[CLIENT]` | `EMF` + `ETF` + `Fresh Animations` | **Installed** (`FA-All_Extensions-v1.10.1.zip`) — **MUST load above** *Fresh Animations* (prevents scrambled sheep/mob UVs) |
| **Boss Refreshed (`v3.0`)** | Boss Animations | `[CLIENT]` | `EMF` + `ETF` + `Fresh Animations` | **Installed** (`boss-refreshed-v3.0-mc26.3.zip`) — Loads above *Fresh Animations* |
| **Fluid & Foolish (`1.0.1`)** | Player Animations & Emotes | `[CLIENT]` | `Punchy! Moves` | **Installed** (`Fluid-Foolish-1.0.1.zip`) |
| **3D Held Lanterns & Torches for Punchy!** | 3D Handheld Torches & Lights | `[CLIENT]` | `Punchy!` / `Punchy! Moves` | **Installed** (`3D Handheld Lanterns and Torches.zip`) — Load **below** *Luminous Lanterns* |
| **Luminous Lanterns (Punchy Moves v2)** | 3D Lanterns + Pendulum Physics | `[CLIENT]` | `Punchy!` / `Punchy! Moves` | **Installed** (`Luminous Lanterns (Punchy Moves v2)`) — Load **above** *3D Handheld Lanterns & Torches* |
| **Abibliophobia** | Bookshelf / Library Textures | `[CLIENT]` | Vanilla | **Installed** (`Abibliophobia.zip`) |
| **Enchantment Descriptions Compat (`1.4`)** | Tooltip Resource Compat | `[CLIENT]` | `Enchantment Descriptions` | **Installed** (`Enchantment Descriptions Compat 1.4.zip`) |
| **Enhanced Boss Bars (`1.6`)** | Boss Bar UI | `[CLIENT]` | Vanilla | **Installed** (`[1.6] Enhanced Boss Bars.zip`) |
| **Extended Illumina (`26.2.x`)** | Glowing / Emissive Ores & Textures | `[CLIENT]` | `ETF` | **Installed** (`§eExtended_Illumina_26.2.x.zip`) |
| **Fancy Crops (`v1.4`)** | 3D/Varied Crop Models | `[CLIENT]` | Vanilla / `Continuity` | **Installed** (`Fancy-Crops-v1.4.zip`) |
| **Re-covered** | Block / Armor / Item Polish | `[CLIENT]` | Vanilla | **Installed** (`Re-covered.zip`) |
| **Recolourful Containers DARK (`3.1.4`)** | Dark Mode UI | `[CLIENT]` | Vanilla | **Installed** (`Recolourful Containers DARK 3.1.4 (1.19.4+).zip`) — Uses custom space-glyph fonts (ImmediatelyFast auto-disables font atlas resizing cleanly) |
| **Shinier Tools** | Tool Texture Overhaul | `[CLIENT]` | Vanilla | **Installed** (`Shinier Tools.zip`) |
| **ShivaKlans' Animated Textures** | Animated Block/Item Textures | `[CLIENT]` | Vanilla | **Installed** (`ShivaKlans' animated textures.zip`) |

---

## 4. Dedicated Server Admin & Stability (Phase 2/5)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **spark** | Performance Profiler | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`spark-1.10.187-neoforge.jar`). Diagnoses server TPS lag and client frame spikes (`/sparkc`, `/spark`). |
| **Chunky** | World Pre-Generator | `[SERVER]` | `NeoForge` | `CF Manifest` | **Installed** (`Chunky-NeoForge-1.5.66.jar`). Pre-generate a `5,000–10,000` block radius before launch so server doesn't lag on opening day. |
| **Simple Backups** | World Backups | `[SERVER]` | `NeoForge` | `CF Manifest` | **Installed** (`SimpleBackups-26.3.1.jar`). `common.toml` excludes `voxy/` (`ignored_paths = ["voxy"]`) to prevent Windows `storage/LOCK` errors. |
| **WorldEdit** | Admin / World Building | `[SERVER]` / `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`worldedit-mod-7.4.6.jar`). Includes WorldEdit CUI protocol (`[BOTH]` only if admins want CUI selection wireframes). |
| **The Nest — In-Game Admin Panel (txAdmin)** | In-Game Admin & Moderation GUI | `[BOTH]` | `NeoForge` | `overrides/mods/` | **Installed** (`nest_txadmin-1.0.0-neoforge-26.3.jar`). Opens a custom dark-mode txAdmin GUI in-game via `/adminpanel` (`/tx`, `/ap`) for any OP, plus `/god`, `/noclip`, `/fly`, `/vanish`, `/tpto`, `/bring`, `/return`, `/freeze`, `/invsee`, `/endersee`, `/heal`, Char & Teams, and TitleScreen live status badge. |
| **The Nest Revive** | Wounded Knockdown & Team Revive | `[BOTH]` | `NeoForge` | `overrides/mods/` | **Installed** (`nest_revive-1.0.0-neoforge-26.3.jar`). Intercepts fatal hits (`EventPriority.HIGH` before `Corpse`) into a `45s` wounded bleedout pose on the ground (`Pose.SWIMMING`); teammates hold `Shift` or `Right-Click` (`3.5s`) nearby to revive, hold `Space` (`1.5s`) to give up, or let bleedout expire to die cleanly and spawn the `Corpse` mod corpse (`/revive` OP command). |

---

## 5. Recently Added Mods (Structure, Storage, QoL & Content Audit)

### Vanilla-Save-Safe Additions (No Custom Block/Biome IDs)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Moog's Structure Lib** | Structure Engine | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`MoogsStructureLib-neoforge-26.3-3.4.2.jar`). Shared lib for `MNS`, `MES`, `MVS`, `MTR`; `moogs_structures.json` keeps `replace_nether_fortress: false`. |
| **MNS (Moog's Nether Structures)** | Nether Structures | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`MoogsNetherStructures-universal-1.21-3.1.1.jar`). Vanilla blocks/entities. |
| **MES (Moog's End Structures)** | End Structures | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`MoogsEndStructures-universal-1.21-2.1.1.jar`). Outer End (`>= 1000` blocks from `0,0`). |
| **MVS (Moog's Voyager Structures)** | Overworld/Nether Structures | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`MoogsVoyagerStructures-universal-1.21-5.1.3.jar`). Vanilla blocks/entities. |
| **MTR (Moog's Temples Reimagined)** | Temple Overhaul | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`MoogsTemplesReimagined-universal-1.21-2.0.4.jar`). Vanilla blocks; overrides vanilla explorer maps & temple pools. |
| **Formations + Overworld + Nether** | Structure Suite | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`formations-1.0.4-neoforge-mc26.3.jar`, `formationsoverworld-1.0.5c-mc1.21+.jar`, `formationsnether-1.0.5b-mc1.21+.jar`). |
| **Hopo Better Mineshaft** | Mineshaft Structures | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`HopoBetterMineshaft-[26.3]-1.3.8.jar`). Biome-themed vanilla-block mineshafts. |
| **Tidal Towns** | Ocean Villages | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`tidal-towns-2.0.jar`). Vanilla-block ocean villages (`joshie:village_ocean`). |
| **More Advancements Datapack** | Advancements | — | Datapack Jar | — | **Removed** (`more-advancements-datapack-1.0-1.21.9-1.21.11.jar`). Outdated `1.21` advancement JSON syntax (`minecraft:#logs`, old conditions) failed `26.3` `RegistryDataLoader` on world creation. |
| **Too Many Paintings** | Paintings | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`toomanypaintings-26.08.16-26.1-neoforge.jar`). Data-driven `minecraft:painting_variant` art (`26.1` target; verify in-game). |
| **Polymorph Plus** | Recipe Conflict UI | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`polymorph_plus-neoforge-1.5.0-26.3.0.jar`). Solves crafting collisions with JEI. |
| **Elytra Trims** | Armor/Elytra Cosmetics | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`elytratrims-neoforge-4.9.3-26.3.jar`). Trims & banner patterns on Elytra. |
| **Lanterns Belong on Walls** | Placement QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`walllanterns-3.5.1.jar`). Allows placing vanilla lanterns on walls. |
| **TrampleNoMore + Bookshelf** | Farming QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`TrampleNoMore-neoforge-MC26.3-26.3.0.1.jar`, `Bookshelf-neoforge-MC26.3-26.3.0.4.jar`). |
| **Inventory Profiles Next + libIPN** | Inventory Sorting UI | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`InventoryProfilesNext-neoforge-26.3-2.3.8.jar`, `libIPN-neoforge-26.3-6.9.0.jar`). Overlaps with `MouseTweaks`/`Inventory Essentials`; verify hotkeys. |
| **Swinging Lanterns** | Visual Lantern Physics | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`swinginglanterns-neoforge-26.3-2.1.0.jar`). Uses Sodium mixins — monitor with Voxy + ImmersiveVFX. |
| **Scribble** | Book & Quill UI | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`scribble-2.1.0+mc26.3.jar`). Bundles `Tapestry` + `Tapestry Config`. |
| **No More Popups** | Toast/Popup Suppressor | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`nomorepopups-neoforge-26.2-2.3.1.jar`). `26.2` build; watch overlap with advancement toasts. |

### Mods Adding Custom Blocks, Items, Biomes, or Entities (`[BOTH]` — Tie World Saves)

| Mod Name | Category | Side | Loader | Status / Notes |
| :--- | :--- | :---: | :---: | :--- |
| **Sophisticated Backpacks + Core** | Storage / Backpacks | `[BOTH]` | `NeoForge` | **Installed** (`sophisticatedbackpacks-26.3-3.26.21.2255.jar`, `sophisticatedcore-26.3-1.5.39.2487.jar`). Open Backpack bound to `B` (`Default Options`); Diorama New Waypoint moved to `N`. |
| **Nullscape** | End Overhaul | `[BOTH]` | `NeoForge` | **Installed** (`Nullscape_26.3_v2.0.1+26.3.jar`). Adds 4 custom End biomes + 3 structures; test `MES` structure density in End. |
| **Ecologics** | Biome / Nature Expansion | `[BOTH]` | `NeoForge` | **Installed** (`Ecologics-NeoFab-26.3-2.7.3.jar`). 132 blockstates, new trees/mobs/structure. |
| **Blocks You Need** | Decorative Blocks | `[BOTH]` | `NeoForge` | **Installed** (`blocksyouneed_luna-1.12.7-neoforge-26.3.jar`). Large pack (`3,755` blockstates). |
| **Dawn of Time Builder** | Architecture Blocks | `[BOTH]` | `NeoForge` | **Installed** (`dawnoftimebuilder-neoforge-26.3-1.11.0.jar`). `638` themed blockstates + Fusion compat. |
| **More Concrete** | Building Blocks | `[BOTH]` | `NeoForge` | **Installed** (`moreconcrete-neoforge-1.7.0-26.3.jar`). Concrete stairs/slabs/walls. |
| **Seamless Ores** | Stone-Variant Ore Blocks | `[BOTH]` | `NeoForge` | **Installed** (`seamlessores-neoforge-6.1.0.jar`). Loads inner `26.x` jar via Monolith (`690` ore blockstates). |
| **Easy NPC (+ Config UI + Bundle)** | Custom NPCs | `[BOTH]` | `NeoForge` | **Installed** (`easy_npc*` `7.19.0`). Server hub/quest NPCs, blocks & items. |
| **MineVegas Casino** | Casino / Minigames | `[BOTH]` | `NeoForge` | **Patched (`overrides/mods/`)** (`minevegas-casino-neoforge-26.3-1.1.2.jar`). `79` casino blockstates + items/sounds; all `111` crafting recipe JSONs & `88` recipe advancements stripped so only admins/spawn/villager trade can supply items. |
| **Better Nether Portals** | Portal Overhaul | `[BOTH]` | `NeoForge` | **Installed** (`BetterNetherPortals-26.3.jar`). Adds `flat_nether_portal` & `portal_obsidian`; verify visuals with ImmersiveVFX. |
| **More Frogs** | Frog Variants / Spawn | `[BOTH]` | `NeoForge` | **Installed** (`morefrogs-neoforge-26.3-1.26.10.1.jar`). Custom frog entities + 6 blocks; uses Almanac's newer `DungeonConfig 1.26.11.1`. |
| **More Berry Uses** | Food Items | `[BOTH]` | `NeoForge` | **Installed** (`moreberryuses-2.0.1-for-neoforge-26.3.jar`). Adds sweet-berry foods. |
| **More Axolotl Variants (Removed)** | Mob Variants | — | `NeoForge` | **Removed** (`mavapi-neoforge-2.4.0+26.3.jar`, `mavm-neoforge-2.2.0+26.3.jar`). Crashed NeoForge `26.3.0.103` on missing `DataPackRegistryEvent$NewRegistry`. |
| **Emotecraft (Removed)** | Emotes | — | `NeoForge` | **Removed** (`emotecraft-for-MC26.3-3.5.0-b.build.179.jar`). Threw `NullPointerException` (`ClientNetworkImpl.isServerChannelOpen` -> `stopRelayedEmotes`) on client join and auth errors; `Punchy! Moves` + `Fluid & Foolish` already cover player animations/emotes. |

---

## 6. Full Mod Audit — Remaining Content, Visuals, QoL & Libraries (`mods/`)

### Content, Tech, Building & World Expansion (`[BOTH]`)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Create: Adapted** | Mechanical Tech | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`create-adapted-26.3-1.31-public-external-assets.jar`). Contraption entities excluded in `ServerCore` `activation-range`. |
| **Create: Connected (Adapted)** | Create Addon | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`create_connected-1.3.3-adapted-26.3-0.7.jar`). |
| **Create Crafts & Additions: Adapted** | Create Addon | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`createaddition-26.3-1.7.0-adapted-0.17.jar`). |
| **SecurityCraft** | Security & Traps | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`[26.3] SecurityCraft v1.10.2.1-beta4.jar`). Requires `fml.toml` `versionCheck = true` (`Tips.isOutdated` NPE otherwise). |
| **Naturalist** | Ambient Wildlife | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`naturalist-2.0.7-neoforge-26.3.jar`). Adds vanilla-style animals. |
| **Stormie's Spiders** | Spider Wall-Climbing | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`stormiespiders-neoforge-26.3-3.3.1.jar`). |
| **Lootr** | Instanced Loot Chests | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`lootr-neoforge-26.3-1.25.42.124.jar`). Essential multiplayer per-player dungeon loot. |
| **Corpse** | Death Corpse Recovery | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`corpse-neoforge-1.1.22+26.3.jar`). |
| **Chisel Reborn** | Decorative Blocks | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`chisel-neoforge-2.2.1+mc26.3.jar`). |
| **Rechiseled** | Connected Decorative Blocks | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`rechiseled-1.2.6a-neoforge-mc26.3.jar`). |
| **Decor4All** | Furniture & Props | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`decor4all-26.3-NeoForge-2.0.0.jar`). |
| **Factory Blocks** | Industrial Decorative Blocks | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`factory_blocks-neoforge-1.4.2+mc26.3.jar`). |
| **Macaw's Suite (12 Mods)** | Building & Furniture | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed**: `mcw-bridges-3.1.2-mc26.3neoforge.jar`, `mcw-doors-1.1.5-mc26.3neoforge.jar`, `mcw-fences-1.2.1-mc26.3neoforge.jar`, `mcw-furniture-3.4.2-mc26.3neoforge.jar`, `mcw-holidays-1.1.3-mc26.3neoforge.jar`, `mcw-lights-1.1.5-mc26.3neoforge.jar`, `mcw-paintings-1.1.0-mc26.3neoforge.jar`, `mcw-paths-1.1.1-mc26.3neoforge.jar`, `mcw-roofs-2.3.3-mc26.3neoforge.jar`, `mcw-stairs-1.0.2-mc26.3neoforge.jar`, `mcw-trapdoors-1.1.5-mc26.3neoforge.jar`, `mcw-windows-2.4.3-mc26.3neoforge.jar`. |
| **Easy NPC (+ Core, Config UI, Bundle)** | Custom NPCs | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`easy_npc-neoforge-26.3-7.19.0.jar`, `easy_npc_config_ui-neoforge-26.3-7.19.0.jar`, `easy_npc_bundle-neoforge-26.3-7.19.0.jar`). |
| **Right Click Harvest** | Crop Harvest QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`rightclickharvest-neoforge-4.7.1-26.3.x.jar`). |
| **Inventory Essentials** | Inventory Click QoL | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`inventoryessentials-neoforge-26.3-26.3.0.5.jar`). |
| **Cut Through** | Attack Through Passable Blocks | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`cutthrough-v26.3.0-mc26.3.x+neoforge.jar`). |
| **Timber** | Tree Felling | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`Timber-1.3.5-forge.jar`). |
| **Ping Wheel** | Multiplayer Pings | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`Ping-Wheel-1.12.2-neoforge-26.3.jar`). |
| **LetMeDespawn** | Item-Holding Mob Despawn Fix | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`letmedespawn-neoforge-26.3-1.26.11.1.jar`). Prevents mob cap bloat from mobs picking up items. |

### Client Visuals, UI & Client-Only Utilities (`[CLIENT]`)

| Mod Name | Category | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Subtle Effects** | Ambient & Block Particles | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`SubtleEffects-neoforge-26.3-1.15.2.jar`). |
| **Particular Reforged** | Waterfalls, Splash & Fireflies | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`particular-26.3-NeoForge-1.6.1.jar`). |
| **Wakes** | Boat & Water Ripples | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`wakes-26.3-NeoForge-1.4.1.jar`). |
| **Footprint Particle** | Player & Mob Footprints | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`footprintparticle-0.7.1+26.1-neobric.jar`). |
| **Tread Lightly** | Foliage & Snow Step Physics | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`TreadLightly-1.1.1-26.3-neoforge.jar`). |
| **BetterF3** | Clean F3 Debug HUD | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`BetterF3-20.0.0-NeoForge-26.3.jar`). |
| **GUI Tween** | Smooth Screen Transitions | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`guitween-3.4.2-26.3+neoforge.jar`). |
| **Highlighter** | New-Item Slot Glow | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`Highlighter-26.3-neoforge-1.2.3.jar`). |
| **Legendary Tooltips** | Bordered Item Tooltips | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`LegendaryTooltips-26.3-neoforge-1.6.3.jar`). |
| **Not Enough Recipe Book (NERB)** | Recipe Book Remover (JEI) | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`nerb-neoforge-0.6.2-26.3.jar`). |
| **Screenshot Manager** | Screenshot Gallery UI | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`screenshotmanager-0.2.0-26.3.jar`). |

### Shared Libraries & Dependencies

| Mod Name | Role | Side | Loader | Packaging | Status / Notes |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **Almanac** | Mob/Worldgen Lib | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`almanac-neoforge-26.3-1.26.11.1.jar`). |
| **Anvian's Lib** | Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`anvianslib-neoforge-26.1-1.5.0.jar`). |
| **BaguetteLib** | Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`baguettelib-26.3-NeoForge-2.0.8.jar`). |
| **Balm** | Multi-loader Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`balm-neoforge-26.3-26.3.0.3.jar`). |
| **Cloth Config v26.3 API** | Config GUI Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`cloth-config-neoforge-26.3.159.jar`). Required by Seamless Ores embedded jar on `26.3`. |
| **CreativeCore** | Shared Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`CreativeCore_NEOFORGE_v2.14.25_mc26.3.jar`). |
| **Cryonic Config** | Config Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`cryonicconfig-neoforge-1.0.0+mc26.3.jar`). |
| **CTM Reborn (Athena)** | Connected Textures Lib | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`ctm-reborn-neoforge-4.9.2.jar`). |
| **Fusion** | Connected/Emissive Textures Lib | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`fusion-1.3.16a-neoforge-mc26.3.jar`). |
| **Fzzy Config** | Config Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`fzzy_config-0.7.7+fix3+26.3+neoforge.jar`). |
| **GeckoLib 5** | Animation Engine | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`geckolib-neoforge-26.3-5.5.7.jar`). |
| **Iceberg** | UI / Client Library | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`Iceberg-26.3-neoforge-1.4.3.2.jar`). |
| **JamLib** | Multi-loader Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`jamlib-neoforge-2.3.3-26.3.x.jar`). |
| **KotlinLangForge** | Kotlin Runtime | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`KotlinLangForge-2.20.0-k2.4.21-3.1-neoforge.jar`). |
| **Player Animation Library** | Player Animation Engine | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`PlayerAnimationLibMerged-1.2.9-mc.26.3.jar`). Required by `Punchy! Moves`. |
| **Prism** | UI Color/Rendering Lib | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`Prism-26.3-neoforge-1.1.3.jar`). |
| **Puzzles Lib** | Multi-loader Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`puzzleslib-v26.3.18-mc26.3.x-neoforge.jar`). |
| **Searchables** | GUI Search Helper | `[CLIENT]` | `NeoForge` | `CF Manifest` | **Installed** (`Searchables-neoforge-26.3-1.0.3.jar`). |
| **ShatterLib** | Library | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`shatterlib-neoforge-0.7.0-beta.5-26.3.jar`). |
| **SuperMartijn642's Config + Core Libs** | Building Mod Libs | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`supermartijn642configlib-1.1.8-neoforge-mc26.3.jar`, `supermartijn642corelib-1.1.26d-neoforge-mc26.3.jar`). |
| **tctcore** | Library (`CTM` / Building) | `[BOTH]` | `NeoForge` | `CF Manifest` | **Installed** (`tctcore-2.2-neoforge-26.3.jar`). |
