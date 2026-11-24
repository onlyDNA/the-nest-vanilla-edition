import glob
import os
import shutil
import struct
import subprocess
import zipfile
import zlib

ROOT = r"c:\Users\katen\Desktop\Minecraft Modpack"
WORK = os.path.join(ROOT, "scratch", "talklines_build")
SRC_DIR = os.path.join(WORK, "src")
CLS_DIR = os.path.join(WORK, "classes")

JAVAC = r"C:\Users\katen\.jdks\openjdk-26.0.1\bin\javac.exe"
LIB_ROOT = r"C:\Users\katen\curseforge\minecraft\Install\libraries"
MC_PATCHED = os.path.join(
    LIB_ROOT,
    r"net\neoforged\minecraft-client-patched\26.3.0.103\minecraft-client-patched-26.3.0.103.jar",
)
NF_UNIV = os.path.join(
    LIB_ROOT,
    r"net\neoforged\neoforge\26.3.0.103\neoforge-26.3.0.103-universal.jar",
)


def _find_voicechat_jar() -> str:
    candidates = [
        r"c:\Users\katen\AppData\Local\TheNestVanilla\instance\mods\voicechat-neoforge-*.jar",
        r"C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition\mods\voicechat-neoforge-*.jar",
        r"C:\Users\katen\Desktop\TheNest VanillaEditon Server\mods\voicechat-neoforge-*.jar",
    ]
    for pat in candidates:
        hits = glob.glob(pat)
        if hits:
            return hits[0]
    raise FileNotFoundError("Could not find voicechat-neoforge-*.jar for compilation")


VOICECHAT_JAR = _find_voicechat_jar()

if os.path.exists(WORK):
    shutil.rmtree(WORK)
os.makedirs(SRC_DIR, exist_ok=True)
os.makedirs(CLS_DIR, exist_ok=True)


def _make_png(width: int, height: int, pixels_rgba: list[tuple[int, int, int, int]]) -> bytes:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        row_start = y * width
        for x in range(width):
            r, g, b, a = pixels_rgba[row_start + x]
            raw.extend((r & 255, g & 255, b & 255, a & 255))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")


def build_talk_line_png() -> bytes:
    """Generate a crisp 32x16 cube-net texture for a 8x3x2 RobRun comic speech bar."""
    w, h = 32, 16
    DARK = (24, 22, 30, 255)
    WHITE = (255, 255, 255, 255)
    px = [DARK] * (w * h)

    def paint_rect(x0, y0, x1, y1, col):
        for y in range(y0, y1):
            for x in range(x0, x1):
                if 0 <= x < w and 0 <= y < h:
                    px[y * w + x] = col

    # Minecraft cube net for size (W=8, H=3, D=2) at (0,0):
    # Front face: x=2..10, y=2..5 -> white center row with 1px dark comic border
    paint_rect(3, 3, 9, 4, WHITE)
    # Back face: x=12..20, y=2..5 -> white center row with 1px dark comic border
    paint_rect(13, 3, 19, 4, WHITE)
    # Top & Bottom faces: keep clean white inner strip? Keep dark/white contrast:
    paint_rect(3, 0, 9, 2, WHITE)
    paint_rect(11, 0, 17, 2, WHITE)
    # Left & Right end caps (0..2, 2..5 and 10..12, 2..5) remain DARK comic caps
    return _make_png(w, h, px)


FILES: dict[str, str] = {}

MODS_TOML = """modLoader = "javafml"
loaderVersion = "[1,)"
license = "All Rights Reserved"

[[mods]]
modId = "nest_talklines"
version = "1.0.0"
displayName = "The Nest Talk Lines"
authors = "The Nest"
description = '''Renders 3 RobRun-style comic speaking lines beside a player's head while talking via Simple Voice Chat.'''

[[dependencies.nest_talklines]]
modId = "neoforge"
type = "required"
versionRange = "[26.3.0.48-beta,)"
ordering = "NONE"
side = "CLIENT"

[[dependencies.nest_talklines]]
modId = "minecraft"
type = "required"
versionRange = "[26.3,26.4)"
ordering = "NONE"
side = "CLIENT"

[[dependencies.nest_talklines]]
modId = "voicechat"
type = "required"
versionRange = "[2.6.0,)"
ordering = "AFTER"
side = "CLIENT"
"""

FILES["com/thenest/talklines/NestTalkLinesMod.java"] = r"""package com.thenest.talklines;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@Mod(NestTalkLinesMod.MODID)
public final class NestTalkLinesMod {
    public static final String MODID = "nest_talklines";
    public static final Logger LOGGER = LoggerFactory.getLogger(MODID);

    public NestTalkLinesMod(IEventBus modBus) {
        if (FMLEnvironment.getDist().isClient()) {
            com.thenest.talklines.client.TalkLinesClient.init(modBus);
        }
    }
}
"""

FILES["com/thenest/talklines/client/TalkLinesConfig.java"] = r"""package com.thenest.talklines.client;

import com.thenest.talklines.NestTalkLinesMod;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Properties;

public final class TalkLinesConfig {
    private static final Path CONFIG_PATH = Paths.get("config", "nest_talklines.properties");

    private static volatile boolean enabled = true;
    private static volatile boolean showSelf = true;
    private static volatile double minDb = -66.0;
    private static volatile float scale = 1.0F;
    private static volatile long holdMs = 280L;
    private static volatile int tintRgb = 0xFFFFFF;

    private TalkLinesConfig() {}

    public static synchronized void load() {
        Properties p = new Properties();
        if (Files.isRegularFile(CONFIG_PATH)) {
            try (InputStream in = Files.newInputStream(CONFIG_PATH)) {
                p.load(in);
            } catch (IOException e) {
                NestTalkLinesMod.LOGGER.warn("Failed reading nest_talklines.properties", e);
            }
        }
        enabled = Boolean.parseBoolean(p.getProperty("enabled", "true"));
        showSelf = Boolean.parseBoolean(p.getProperty("showSelfInThirdPerson", "true"));
        minDb = parseDouble(p.getProperty("minThresholdDb"), -66.0);
        scale = (float) Math.max(0.4, Math.min(2.5, parseDouble(p.getProperty("scale"), 1.0)));
        holdMs = Math.max(80L, Math.min(800L, parseLong(p.getProperty("holdMs"), 240L)));
        tintRgb = parseHexRgb(p.getProperty("colorHex"), 0xFFFFFF);

        if (!Files.exists(CONFIG_PATH)) {
            saveDefaults();
        }
    }

    private static void saveDefaults() {
        try {
            Files.createDirectories(CONFIG_PATH.getParent());
            Properties p = new Properties();
            p.setProperty("enabled", String.valueOf(enabled));
            p.setProperty("showSelfInThirdPerson", String.valueOf(showSelf));
            p.setProperty("minThresholdDb", String.valueOf(minDb));
            p.setProperty("scale", String.valueOf(scale));
            p.setProperty("holdMs", String.valueOf(holdMs));
            p.setProperty("colorHex", String.format("%06X", tintRgb));
            try (OutputStream out = Files.newOutputStream(CONFIG_PATH)) {
                p.store(out, "The Nest Talk Lines (RobRun-style 3 speaking lines)");
            }
        } catch (IOException e) {
            NestTalkLinesMod.LOGGER.warn("Failed writing nest_talklines.properties", e);
        }
    }

    private static double parseDouble(String s, double def) {
        if (s == null || s.isBlank()) return def;
        try { return Double.parseDouble(s.trim()); } catch (NumberFormatException ignored) { return def; }
    }

    private static long parseLong(String s, long def) {
        if (s == null || s.isBlank()) return def;
        try { return Long.parseLong(s.trim()); } catch (NumberFormatException ignored) { return def; }
    }

    private static int parseHexRgb(String s, int def) {
        if (s == null || s.isBlank()) return def;
        try {
            String clean = s.trim().replace("#", "");
            return Integer.parseInt(clean, 16) & 0xFFFFFF;
        } catch (NumberFormatException ignored) {
            return def;
        }
    }

    public static boolean isEnabled() { return enabled; }
    public static boolean showSelf() { return showSelf; }
    public static double minDb() { return minDb; }
    public static float scale() { return scale; }
    public static long holdMs() { return holdMs; }
    public static int tintRgb() { return tintRgb; }
}
"""

FILES["com/thenest/talklines/client/TalkLinesManager.java"] = r"""package com.thenest.talklines.client;

import com.thenest.talklines.NestTalkLinesMod;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

public final class TalkLinesManager {
    private static final class VoiceState {
        volatile float targetLevel = 0.0F;
        volatile float smoothedLevel = 0.0F;
        volatile long lastActiveMs = 0L;
        volatile long lastSampleMs = 0L;
    }

    private static final Map<UUID, VoiceState> STATES = new ConcurrentHashMap<>();
    private static volatile boolean loggedFirstSpeech = false;

    private TalkLinesManager() {}

    public static void pushPcm(UUID playerId, short[] pcm) {
        if (playerId == null || pcm == null || pcm.length == 0 || !TalkLinesConfig.isEnabled()) {
            return;
        }
        double sumSq = 0.0;
        for (short s : pcm) {
            double norm = s / 32768.0;
            sumSq += norm * norm;
        }
        double rms = Math.sqrt(sumSq / pcm.length);
        double db = rms > 1e-7 ? (20.0 * Math.log10(rms)) : -127.0;

        double minDb = TalkLinesConfig.minDb();
        double maxDb = -22.0;
        float linear = (float) Math.max(0.0, Math.min(1.0, (db - minDb) / Math.max(1.0, maxDb - minDb)));
        if (linear <= 0.02F) {
            return;
        }
        float level = (float) Math.pow(linear, 0.52);

        if (!loggedFirstSpeech) {
            loggedFirstSpeech = true;
            NestTalkLinesMod.LOGGER.info("TalkLines received voice audio for {} (db={}, level={})", playerId, String.format("%.1f", db), String.format("%.2f", level));
        }

        long now = System.currentTimeMillis();
        VoiceState st = STATES.computeIfAbsent(playerId, id -> new VoiceState());
        st.targetLevel = Math.max(st.targetLevel * 0.65F, level);
        st.lastActiveMs = now;
        if (st.lastSampleMs == 0L) {
            st.lastSampleMs = now;
        }
    }

    public static float getAnimatedLevel(UUID playerId) {
        if (playerId == null || !TalkLinesConfig.isEnabled()) {
            return 0.0F;
        }
        boolean vcTalking = TalkLinesVoicePlugin.isVoicechatTalking(playerId);
        long now = System.currentTimeMillis();
        VoiceState st = vcTalking ? STATES.computeIfAbsent(playerId, id -> new VoiceState()) : STATES.get(playerId);
        if (st == null) {
            return 0.0F;
        }
        if (vcTalking) {
            st.targetLevel = Math.max(st.targetLevel, 0.72F);
            st.lastActiveMs = now;
            if (st.lastSampleMs == 0L) {
                st.lastSampleMs = now;
            }
        }

        long dtMs = Math.max(1L, Math.min(100L, now - st.lastSampleMs));
        st.lastSampleMs = now;

        long silentFor = now - st.lastActiveMs;
        float desired = (silentFor <= TalkLinesConfig.holdMs()) ? Math.max(0.50F, st.targetLevel) : 0.0F;
        if (silentFor > 70L) {
            st.targetLevel *= (float) Math.pow(0.88, dtMs / 16.0);
        }

        float rate = (desired > st.smoothedLevel) ? 0.42F : 0.18F;
        float alpha = 1.0F - (float) Math.pow(1.0F - rate, dtMs / 16.0);
        st.smoothedLevel += (desired - st.smoothedLevel) * alpha;

        if (st.smoothedLevel < 0.015F && desired == 0.0F) {
            st.smoothedLevel = 0.0F;
            if (silentFor > 3000L) {
                STATES.remove(playerId, st);
            }
            return 0.0F;
        }
        return st.smoothedLevel;
    }

    public static void clear() {
        STATES.clear();
    }
}
"""

FILES["com/thenest/talklines/client/TalkLinesVoicePlugin.java"] = r"""package com.thenest.talklines.client;

import com.thenest.talklines.NestTalkLinesMod;
import de.maxhenkel.voicechat.api.ForgeVoicechatPlugin;
import de.maxhenkel.voicechat.api.VoicechatApi;
import de.maxhenkel.voicechat.api.VoicechatClientApi;
import de.maxhenkel.voicechat.api.VoicechatPlugin;
import de.maxhenkel.voicechat.api.events.ClientReceiveSoundEvent;
import de.maxhenkel.voicechat.api.events.ClientSoundEvent;
import de.maxhenkel.voicechat.api.events.ClientVoicechatConnectionEvent;
import de.maxhenkel.voicechat.api.events.ClientVoicechatInitializationEvent;
import de.maxhenkel.voicechat.api.events.EventRegistration;
import java.util.UUID;
import net.minecraft.client.Minecraft;

@ForgeVoicechatPlugin
public class TalkLinesVoicePlugin implements VoicechatPlugin {
    private static volatile VoicechatClientApi clientApi;

    @Override
    public String getPluginId() {
        return NestTalkLinesMod.MODID;
    }

    @Override
    public void initialize(VoicechatApi api) {
        if (api instanceof VoicechatClientApi cApi) {
            clientApi = cApi;
        }
        NestTalkLinesMod.LOGGER.info("The Nest Talk Lines Simple Voice Chat plugin initialized");
    }

    @Override
    public void registerEvents(EventRegistration registration) {
        registration.registerEvent(ClientVoicechatInitializationEvent.class, this::onClientInit);
        registration.registerEvent(ClientSoundEvent.class, this::onLocalPlayerSound);
        registration.registerEvent(ClientReceiveSoundEvent.EntitySound.class, this::onRemotePlayerSound);
        registration.registerEvent(ClientReceiveSoundEvent.StaticSound.class, this::onRemotePlayerSound);
        registration.registerEvent(ClientReceiveSoundEvent.LocationalSound.class, this::onRemotePlayerSound);
        registration.registerEvent(ClientVoicechatConnectionEvent.class, this::onConnectionChanged);
    }

    private void onClientInit(ClientVoicechatInitializationEvent event) {
        if (event.getVoicechat() != null) {
            clientApi = event.getVoicechat();
        }
    }

    private void onConnectionChanged(ClientVoicechatConnectionEvent event) {
        if (!event.isConnected()) {
            TalkLinesManager.clear();
        }
    }

    public static boolean isVoicechatTalking(UUID playerUuid) {
        VoicechatClientApi api = clientApi;
        if (api == null || playerUuid == null || api.isDisabled()) {
            return false;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.player != null && playerUuid.equals(mc.player.getUUID())) {
            if (!TalkLinesConfig.showSelf() || api.isMuted()) {
                return false;
            }
            return api.isTalking();
        }
        if (api.getVolumeConfig().getVolume(playerUuid) <= 0.0) {
            return false;
        }
        return api.isTalking(playerUuid);
    }

    private void onLocalPlayerSound(ClientSoundEvent event) {
        if (!TalkLinesConfig.isEnabled() || !TalkLinesConfig.showSelf()) {
            return;
        }
        VoicechatClientApi api = event.getVoicechat();
        if (api != null) {
            clientApi = api;
            if (api.isMuted() || api.isDisabled()) {
                return;
            }
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null) {
            return;
        }
        TalkLinesManager.pushPcm(mc.player.getUUID(), event.getRawAudio());
    }

    private void onRemotePlayerSound(ClientReceiveSoundEvent event) {
        if (!TalkLinesConfig.isEnabled()) {
            return;
        }
        VoicechatClientApi api = event.getVoicechat();
        if (api != null) {
            clientApi = api;
            if (api.isDisabled()) return;
            if (api.getVolumeConfig().getVolume(event.getId()) <= 0.0) return;
        }
        TalkLinesManager.pushPcm(event.getId(), event.getRawAudio());
    }
}
"""

FILES["com/thenest/talklines/client/TalkLinesLayer.java"] = r"""package com.thenest.talklines.client;

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.thenest.talklines.NestTalkLinesMod;
import net.minecraft.client.Minecraft;
import net.minecraft.client.model.geom.ModelPart;
import net.minecraft.client.model.geom.PartPose;
import net.minecraft.client.model.geom.builders.CubeListBuilder;
import net.minecraft.client.model.geom.builders.LayerDefinition;
import net.minecraft.client.model.geom.builders.MeshDefinition;
import net.minecraft.client.model.geom.builders.PartDefinition;
import net.minecraft.client.model.player.PlayerModel;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.SubmitNodeCollector;
import net.minecraft.client.renderer.entity.RenderLayerParent;
import net.minecraft.client.renderer.entity.layers.RenderLayer;
import net.minecraft.client.renderer.entity.state.AvatarRenderState;
import net.minecraft.client.renderer.rendertype.RenderType;
import net.minecraft.client.renderer.rendertype.RenderTypes;
import net.minecraft.client.renderer.texture.OverlayTexture;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.Entity;

public class TalkLinesLayer extends RenderLayer<AvatarRenderState, PlayerModel> {
    private static final Identifier LINE_TEXTURE =
            Identifier.fromNamespaceAndPath(NestTalkLinesMod.MODID, "textures/talk_line.png");
    private static final RenderType LINE_RENDER_TYPE = RenderTypes.entityCutout(LINE_TEXTURE);
    private static final int FULL_BRIGHT = 0x00F000F0;

    private static volatile boolean loggedFirstRender = false;
    private final ModelPart barPart;

    public TalkLinesLayer(RenderLayerParent<AvatarRenderState, PlayerModel> parent) {
        super(parent);
        MeshDefinition mesh = new MeshDefinition();
        PartDefinition root = mesh.getRoot();
        root.addOrReplaceChild(
                "bar",
                CubeListBuilder.create().texOffs(0, 0).addBox(0.0F, -1.5F, -1.0F, 8.0F, 3.0F, 2.0F),
                PartPose.ZERO
        );
        this.barPart = LayerDefinition.create(mesh, 32, 16).bakeRoot().getChild("bar");
    }

    @Override
    public void submit(
            PoseStack poseStack,
            SubmitNodeCollector collector,
            int packedLight,
            AvatarRenderState state,
            float yRot,
            float xRot
    ) {
        if (!TalkLinesConfig.isEnabled() || state.isSpectator || state.isInvisible) {
            return;
        }
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null) {
            return;
        }
        Entity entity = mc.level.getEntity(state.id);
        if (!(entity instanceof AbstractClientPlayer player)) {
            return;
        }
        if (player == mc.player && !TalkLinesConfig.showSelf()) {
            return;
        }

        float level = TalkLinesManager.getAnimatedLevel(player.getUUID());
        if (level <= 0.015F) {
            return;
        }

        if (!loggedFirstRender) {
            loggedFirstRender = true;
            NestTalkLinesMod.LOGGER.info("Rendering RobRun TalkLines for {} (level={})", player.getName().getString(), String.format("%.2f", level));
        }

        float cfgScale = TalkLinesConfig.scale();
        int rgb = TalkLinesConfig.tintRgb();
        int alpha = Math.max(185, Math.min(255, Math.round(255.0F * Math.min(1.0F, 0.68F + level * 0.45F))));
        int argb = (alpha << 24) | (rgb & 0xFFFFFF);

        float timeSec = (System.currentTimeMillis() % 100000L) / 1000.0F;

        poseStack.pushPose();
        // Anchor directly to the player's head bone so lines follow head rotation & animations
        this.getParentModel().head.translateAndRotate(poseStack);
        // Top-right corner of the head/hat (-Z is forward, -Y is up)
        poseStack.translate(0.24F, -0.52F, -0.06F);
        poseStack.rotate(Axis.YP.rotationDegrees(16.0F));
        // Tilt the whole fan ~42 deg upward at the top corner (negative Z = up)
        poseStack.rotate(Axis.ZP.rotationDegrees(-42.0F));
        poseStack.scale(cfgScale, cfgScale, cfgScale);

        final float[] angles = new float[] { -36.0F, 0.0F, 34.0F };
        final float[] baseLengths = new float[] { 0.72F, 1.18F, 0.58F };
        final float[] yOffsets = new float[] { -0.062F, 0.0F, 0.062F };

        for (int i = 0; i < 3; i++) {
            float wave = 0.88F + 0.12F * (float) Math.sin(timeSec * 18.0F + i * 1.15F);
            float pulse = (0.72F + 0.44F * level) * wave;
            float startX = 0.02F + 0.03F * level;

            poseStack.pushPose();
            poseStack.translate(startX, yOffsets[i], 0.0F);
            poseStack.rotate(Axis.ZP.rotationDegrees(angles[i]));
            // Sleek smaller comic lines (~0.14-0.30 blocks long, thin stroke)
            poseStack.scale(0.44F * baseLengths[i] * pulse, 0.28F, 0.28F);

            collector.submitModelPart(
                    this.barPart,
                    poseStack,
                    LINE_RENDER_TYPE,
                    FULL_BRIGHT,
                    OverlayTexture.NO_OVERLAY,
                    null,
                    argb,
                    0
            );

            poseStack.popPose();
        }

        poseStack.popPose();
    }
}
"""

FILES["com/thenest/talklines/client/TalkLinesClient.java"] = r"""package com.thenest.talklines.client;

import com.thenest.talklines.NestTalkLinesMod;
import net.minecraft.client.player.AbstractClientPlayer;
import net.minecraft.client.renderer.entity.player.AvatarRenderer;
import net.minecraft.world.entity.player.PlayerModelType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.client.event.EntityRenderersEvent;

public final class TalkLinesClient {
    private TalkLinesClient() {}

    public static void init(IEventBus modBus) {
        TalkLinesConfig.load();
        modBus.addListener(TalkLinesClient::onAddLayers);
    }

    private static void onAddLayers(EntityRenderersEvent.AddLayers event) {
        int attached = 0;
        for (PlayerModelType skin : event.getSkins()) {
            AvatarRenderer<AbstractClientPlayer> renderer = event.getPlayerRenderer(skin);
            if (renderer != null) {
                renderer.addLayer(new TalkLinesLayer(renderer));
                attached++;
            }
        }
        NestTalkLinesMod.LOGGER.info("Attached RobRun TalkLinesLayer to {} player skin renderer(s)", attached);
    }
}
"""

java_paths = []
for rel, content in FILES.items():
    full = os.path.join(SRC_DIR, rel.replace("/", os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    java_paths.append(full)

cp_jars = [MC_PATCHED, NF_UNIV, VOICECHAT_JAR]
for pattern in [
    "net/neoforged/**/*.jar",
    "com/mojang/**/*.jar",
    "com/google/guava/**/*.jar",
    "org/joml/**/*.jar",
    "org/slf4j/**/*.jar",
    "it/unimi/dsi/**/*.jar",
]:
    cp_jars.extend(glob.glob(os.path.join(LIB_ROOT, pattern), recursive=True))

cp_str = ";".join(dict.fromkeys(cp_jars)).replace("\\", "/")
cp_file = os.path.join(WORK, "cp.txt")
with open(cp_file, "w", encoding="utf-8") as f:
    f.write(f'-cp "{cp_str}"\n')
    for jp in java_paths:
        f.write(f'"{jp.replace(chr(92), "/")}"\n')

cmd = [JAVAC, "-encoding", "UTF-8", "--release", "25", "-d", CLS_DIR, f"@{cp_file}"]
res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
if res.returncode != 0:
    print("JAVAC FAILED:")
    print(res.stdout)
    print(res.stderr)
    raise SystemExit(1)

print("JAVAC SUCCEEDED!")

meta_dir = os.path.join(CLS_DIR, "META-INF")
os.makedirs(meta_dir, exist_ok=True)
with open(os.path.join(meta_dir, "neoforge.mods.toml"), "w", encoding="utf-8") as f:
    f.write(MODS_TOML)

tex_dir = os.path.join(CLS_DIR, "assets", "nest_talklines", "textures")
os.makedirs(tex_dir, exist_ok=True)
with open(os.path.join(tex_dir, "talk_line.png"), "wb") as f:
    f.write(build_talk_line_png())

jar_name = "nest_talklines-1.0.0-neoforge-26.3.jar"
out_jar = os.path.join(WORK, jar_name)
with zipfile.ZipFile(out_jar, "w", zipfile.ZIP_DEFLATED) as zf:
    for root_dir, _, files in os.walk(CLS_DIR):
        for fn in files:
            full_p = os.path.join(root_dir, fn)
            rel_p = os.path.relpath(full_p, CLS_DIR).replace(os.sep, "/")
            zf.write(full_p, rel_p)

targets = [
    os.path.join(r"C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition\mods", jar_name),
    os.path.join(ROOT, "overrides", "mods", jar_name),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "TheNestVanilla", "instance", "mods", jar_name),
]
for t in targets:
    if os.path.exists(os.path.dirname(t)):
        try:
            shutil.copy2(out_jar, t)
            print("Installed:", t, os.path.getsize(t), "bytes")
        except PermissionError:
            print("LOCKED (Game Running):", t)

shutil.rmtree(WORK, ignore_errors=True)
