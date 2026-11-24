import glob
import os
import shutil
import subprocess
import zipfile

ROOT = r"c:\Users\katen\Desktop\Minecraft Modpack"
WORK = os.path.join(ROOT, "scratch", "txadmin_build")
SRC_DIR = os.path.join(WORK, "src")
CLS_DIR = os.path.join(WORK, "classes")

JAVAC = r"C:\Users\katen\.jdks\openjdk-26.0.1\bin\javac.exe"
LIB_ROOT = r"C:\Users\katen\curseforge\minecraft\Install\libraries"
MC_PATCHED = os.path.join(LIB_ROOT, r"net\neoforged\minecraft-client-patched\26.3.0.103\minecraft-client-patched-26.3.0.103.jar")
NF_UNIV = os.path.join(LIB_ROOT, r"net\neoforged\neoforge\26.3.0.103\neoforge-26.3.0.103-universal.jar")

if os.path.exists(WORK):
    shutil.rmtree(WORK)
os.makedirs(SRC_DIR, exist_ok=True)
os.makedirs(CLS_DIR, exist_ok=True)

FILES = {}

# 1. META-INF/neoforge.mods.toml
MODS_TOML = """modLoader = "javafml"
loaderVersion = "[1,)"
license = "All Rights Reserved"

[[mods]]
modId = "nest_txadmin"
version = "1.0.0"
displayName = "The Nest — In-Game Admin Panel (txAdmin)"
authors = "The Nest"
description = '''In-game txAdmin-style Admin Panel (/adminpanel, /tx, /ap) with Godmode, NoClip, Fly, Vanish, TP To, Bring, Return, Freeze, InvSee, EnderSee, World & Gamerule controls, Voxy/ServerCore/Chunky/Spark tools, and Casino item spawner.'''

[[dependencies.nest_txadmin]]
modId = "neoforge"
type = "required"
versionRange = "[26.3.0.48-beta,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.nest_txadmin]]
modId = "minecraft"
type = "required"
versionRange = "[26.3,26.4)"
ordering = "NONE"
side = "BOTH"
"""

# 2. NestTxAdminMod.java
FILES["com/thenest/txadmin/NestTxAdminMod.java"] = """package com.thenest.txadmin;

import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

@Mod(NestTxAdminMod.MODID)
public final class NestTxAdminMod {
    public static final String MODID = "nest_txadmin";

    public NestTxAdminMod(IEventBus modBus) {
        modBus.addListener(this::registerPayloads);
        TxAdminServer.registerEvents();
        SkinServerManager.registerEvents();
        CharCustomServerManager.registerEvents();
        if (FMLEnvironment.getDist().isClient()) {
            com.thenest.txadmin.client.TxAdminClient.init();
            com.thenest.txadmin.client.SkinClientManager.init();
            com.thenest.txadmin.client.CharCustomClientManager.init();
        }
    }

    private void registerPayloads(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar reg = event.registrar("1").optional();
        OpenTxAdminPayload.registerInto(reg);
        TxActionPayload.registerInto(reg);
        UploadSkinPayload.registerInto(reg);
        BroadcastSkinPayload.registerInto(reg);
        SyncCharProfilesPayload.registerInto(reg);
    }
}
"""

# 2b. UploadSkinPayload.java
FILES["com/thenest/txadmin/UploadSkinPayload.java"] = """package com.thenest.txadmin;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record UploadSkinPayload(String targetPlayer, String mode, boolean slim, byte[] pngBytes) implements CustomPacketPayload {

    public static final CustomPacketPayload.Type<UploadSkinPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "upload_skin"));

    public static final StreamCodec<RegistryFriendlyByteBuf, UploadSkinPayload> STREAM_CODEC =
            StreamCodec.of(UploadSkinPayload::encode, UploadSkinPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, UploadSkinPayload p) {
        buf.writeUtf(p.targetPlayer() != null ? p.targetPlayer() : "", 64);
        buf.writeUtf(p.mode() != null ? p.mode() : "mojang", 32);
        buf.writeBoolean(p.slim());
        byte[] data = p.pngBytes() != null ? p.pngBytes() : new byte[0];
        if (data.length > 65536) {
            data = new byte[0];
        }
        buf.writeByteArray(data);
    }

    private static UploadSkinPayload decode(RegistryFriendlyByteBuf buf) {
        String target = buf.readUtf(64);
        String mode = buf.readUtf(32);
        boolean slim = buf.readBoolean();
        byte[] data = buf.readByteArray(65536);
        return new UploadSkinPayload(target, mode, slim, data);
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToServer(TYPE, STREAM_CODEC, UploadSkinPayload::handleServer);
    }

    private static void handleServer(UploadSkinPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            if (ctx.player() instanceof ServerPlayer sp) {
                SkinServerManager.onClientUploadSkin(sp, payload);
            }
        });
    }
}
"""

# 2c. BroadcastSkinPayload.java
FILES["com/thenest/txadmin/BroadcastSkinPayload.java"] = """package com.thenest.txadmin;

import java.util.UUID;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record BroadcastSkinPayload(UUID playerUuid, String playerName, boolean slim, byte[] pngBytes) implements CustomPacketPayload {

    public interface ClientHandler {
        void handleSkin(BroadcastSkinPayload payload);
    }

    private static volatile ClientHandler clientHandler;

    public static void setClientHandler(ClientHandler handler) {
        clientHandler = handler;
    }

    public static final CustomPacketPayload.Type<BroadcastSkinPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "broadcast_skin"));

    public static final StreamCodec<RegistryFriendlyByteBuf, BroadcastSkinPayload> STREAM_CODEC =
            StreamCodec.of(BroadcastSkinPayload::encode, BroadcastSkinPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, BroadcastSkinPayload p) {
        buf.writeUUID(p.playerUuid() != null ? p.playerUuid() : new UUID(0L, 0L));
        buf.writeUtf(p.playerName() != null ? p.playerName() : "", 64);
        buf.writeBoolean(p.slim());
        byte[] data = p.pngBytes() != null ? p.pngBytes() : new byte[0];
        if (data.length > 65536) {
            data = new byte[0];
        }
        buf.writeByteArray(data);
    }

    private static BroadcastSkinPayload decode(RegistryFriendlyByteBuf buf) {
        UUID id = buf.readUUID();
        String name = buf.readUtf(64);
        boolean slim = buf.readBoolean();
        byte[] data = buf.readByteArray(65536);
        return new BroadcastSkinPayload(id, name, slim, data);
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToClient(TYPE, STREAM_CODEC, BroadcastSkinPayload::handleClient);
    }

    private static void handleClient(BroadcastSkinPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            ClientHandler h = clientHandler;
            if (h != null) {
                h.handleSkin(payload);
            }
        });
    }
}
"""

# 2d. SkinServerManager.java
FILES["com/thenest/txadmin/SkinServerManager.java"] = r"""package com.thenest.txadmin;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Base64;
import java.util.Locale;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.network.PacketDistributor;

public final class SkinServerManager {
    public record SkinRecord(UUID playerUuid, String playerName, boolean slim, byte[] pngBytes) {}

    private static final Map<String, SkinRecord> ACTIVE_SKINS = new ConcurrentHashMap<>();
    private static final ExecutorService SKIN_POOL = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "Nest-SkinFetcher");
        t.setDaemon(true);
        return t;
    });

    private static final Pattern ID_PAT = Pattern.compile("\"id\"\\s*:\\s*\"([0-9a-fA-F]+)\"");
    private static final Pattern VAL_PAT = Pattern.compile("\"value\"\\s*:\\s*\"([A-Za-z0-9+/=]+)\"");
    private static final Pattern URL_PAT = Pattern.compile("\"SKIN\"\\s*:\\s*\\{[^}]*\"url\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern SLIM_PAT = Pattern.compile("\"model\"\\s*:\\s*\"slim\"");
    private static final Pattern JSON_SLIM_PAT = Pattern.compile("\"slim\"\\s*:\\s*(true|false)");
    private static final Pattern JSON_B64_PAT = Pattern.compile("\"png_base64\"\\s*:\\s*\"([A-Za-z0-9+/=\\r\\n]+)\"");

    private SkinServerManager() {}

    public static void registerEvents() {
        NeoForge.EVENT_BUS.addListener(SkinServerManager::onPlayerJoin);
        NeoForge.EVENT_BUS.addListener(SkinServerManager::onRegisterCommands);
    }

    private static Path getSkinStoreDir() {
        Path dir = Paths.get("nest_skins");
        try {
            Files.createDirectories(dir);
        } catch (Exception ignored) {}
        return dir;
    }

    private static Path getSavedSkinFile(String playerName) {
        String safe = playerName.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_.-]", "_");
        return getSkinStoreDir().resolve(safe + ".json");
    }

    private static void saveCustomSkinToDisk(String playerName, boolean slim, byte[] pngBytes) {
        try {
            String b64 = Base64.getEncoder().encodeToString(pngBytes);
            String json = "{\n  \"slim\": " + slim + ",\n  \"png_base64\": \"" + b64 + "\"\n}\n";
            Files.writeString(getSavedSkinFile(playerName), json, StandardCharsets.UTF_8);
        } catch (Exception ignored) {}
    }

    private static SkinRecord loadSavedSkinFromDisk(UUID uuid, String playerName) {
        try {
            Path p = getSavedSkinFile(playerName);
            if (!Files.exists(p)) return null;
            String raw = Files.readString(p, StandardCharsets.UTF_8);
            boolean slim = false;
            Matcher mSlim = JSON_SLIM_PAT.matcher(raw);
            if (mSlim.find()) {
                slim = Boolean.parseBoolean(mSlim.group(1));
            }
            Matcher mB64 = JSON_B64_PAT.matcher(raw);
            if (mB64.find()) {
                String clean = mB64.group(1).replaceAll("\\s+", "");
                byte[] bytes = Base64.getDecoder().decode(clean);
                if (bytes.length > 64 && bytes.length <= 65536) {
                    return new SkinRecord(uuid, playerName, slim, bytes);
                }
            }
        } catch (Exception ignored) {}
        return null;
    }

    public static void onPlayerJoin(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer sp)) return;
        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return;

        // 1. Send all currently active skins to the joining player
        for (SkinRecord rec : ACTIVE_SKINS.values()) {
            sendSkinSafe(sp, new BroadcastSkinPayload(rec.playerUuid(), rec.playerName(), rec.slim(), rec.pngBytes()));
        }

        // 2. Check if this player has a saved custom skin on the server; otherwise fetch their Mojang nickname skin!
        String name = sp.getGameProfile().name();
        String key = name.toLowerCase(Locale.ROOT);
        SkinRecord saved = loadSavedSkinFromDisk(sp.getUUID(), name);
        if (saved != null) {
            ACTIVE_SKINS.put(key, saved);
            broadcastSkinToAll(srv, saved);
        } else {
            fetchMojangSkinAsync(srv, sp.getUUID(), name, name, false, null);
        }
    }

    public static void onClientUploadSkin(ServerPlayer sp, UploadSkinPayload payload) {
        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return;
        String senderName = sp.getGameProfile().name();
        String targetReq = payload.targetPlayer() != null ? payload.targetPlayer().trim() : "";
        boolean isSelf = targetReq.isEmpty() || targetReq.equalsIgnoreCase(senderName) || targetReq.equalsIgnoreCase("@s");

        if (!isSelf && !TxAdminServer.isAdmin(sp)) {
            sp.sendSystemMessage(Component.literal("§c[The Nest] Only Server Operators can change other players' skins."));
            return;
        }

        if ("@a".equalsIgnoreCase(targetReq)) {
            for (ServerPlayer online : srv.getPlayerList().getPlayers()) {
                applySkinBytesToTarget(srv, online.getUUID(), online.getGameProfile().name(), payload.mode(), payload.slim(), payload.pngBytes());
            }
            return;
        }

        ServerPlayer targetPlayer = isSelf ? sp : srv.getPlayerList().getPlayerByName(targetReq);
        String resolvedName = targetPlayer != null ? targetPlayer.getGameProfile().name() : (isSelf ? senderName : targetReq);
        UUID resolvedUuid = targetPlayer != null ? targetPlayer.getUUID() : sp.getUUID();
        applySkinBytesToTarget(srv, resolvedUuid, resolvedName, payload.mode(), payload.slim(), payload.pngBytes());
    }

    public static void applySkinBytesToTarget(MinecraftServer srv, UUID targetUuid, String targetName, String mode, boolean slim, byte[] bytes) {
        String key = targetName.toLowerCase(Locale.ROOT);
        if ("mojang".equalsIgnoreCase(mode) || bytes == null || bytes.length < 64) {
            try {
                Files.deleteIfExists(getSavedSkinFile(targetName));
            } catch (Exception ignored) {}
            fetchMojangSkinAsync(srv, targetUuid, targetName, targetName, false, null);
            return;
        }

        SkinRecord rec = new SkinRecord(targetUuid, targetName, slim, bytes);
        ACTIVE_SKINS.put(key, rec);
        saveCustomSkinToDisk(targetName, slim, bytes);
        broadcastSkinToAll(srv, rec);
    }

    public static void setTargetArmStyle(MinecraftServer srv, String targetName, boolean slim) {
        if ("@a".equalsIgnoreCase(targetName)) {
            for (ServerPlayer p : srv.getPlayerList().getPlayers()) {
                setTargetArmStyle(srv, p.getGameProfile().name(), slim);
            }
            return;
        }
        String key = targetName.toLowerCase(Locale.ROOT);
        SkinRecord cur = ACTIVE_SKINS.get(key);
        if (cur == null) return;
        SkinRecord updated = new SkinRecord(cur.playerUuid(), cur.playerName(), slim, cur.pngBytes());
        ACTIVE_SKINS.put(key, updated);
        saveCustomSkinToDisk(cur.playerName(), slim, cur.pngBytes());
        broadcastSkinToAll(srv, updated);
    }

    public static void resetTargetSkin(MinecraftServer srv, String targetName, ServerPlayer feedback) {
        if ("@a".equalsIgnoreCase(targetName)) {
            for (ServerPlayer p : srv.getPlayerList().getPlayers()) {
                resetTargetSkin(srv, p.getGameProfile().name(), null);
            }
            if (feedback != null) {
                feedback.sendSystemMessage(Component.literal("§6[The Nest] §aReset skins for all online players to their Mojang nicknames."));
            }
            return;
        }
        try {
            Files.deleteIfExists(getSavedSkinFile(targetName));
        } catch (Exception ignored) {}
        ServerPlayer sp = srv.getPlayerList().getPlayerByName(targetName);
        UUID id = sp != null ? sp.getUUID() : new UUID(0L, 0L);
        String name = sp != null ? sp.getGameProfile().name() : targetName;
        fetchMojangSkinAsync(srv, id, name, name, false, feedback);
    }

    public static void fetchMojangSkinAsync(MinecraftServer srv, UUID targetPlayerUuid, String targetPlayerName, String mojangLookupName, boolean persistAsCustom, ServerPlayer feedbackPlayer) {
        SKIN_POOL.submit(() -> {
            SkinRecord fetched = downloadMojangSkin(targetPlayerUuid, targetPlayerName, mojangLookupName);
            if (fetched != null) {
                srv.execute(() -> {
                    ACTIVE_SKINS.put(targetPlayerName.toLowerCase(Locale.ROOT), fetched);
                    if (persistAsCustom) {
                        saveCustomSkinToDisk(targetPlayerName, fetched.slim(), fetched.pngBytes());
                    }
                    broadcastSkinToAll(srv, fetched);
                    if (feedbackPlayer != null) {
                        feedbackPlayer.sendSystemMessage(Component.literal("§6[The Nest] §aApplied skin of §f" + mojangLookupName + " §7(" + (fetched.slim() ? "Slim Arms" : "Default Arms") + ")§a!"));
                    }
                });
            } else if (feedbackPlayer != null) {
                srv.execute(() -> feedbackPlayer.sendSystemMessage(Component.literal("§c[The Nest] Could not find a Mojang skin for nickname '" + mojangLookupName + "'.")));
            }
        });
    }

    public static SkinRecord downloadMojangSkin(UUID playerUuid, String playerName, String lookupName) {
        try {
            String profJson = httpGetString("https://api.mojang.com/users/profiles/minecraft/" + lookupName.trim());
            if (profJson == null) return null;
            Matcher mId = ID_PAT.matcher(profJson);
            if (!mId.find()) return null;
            String mojangId = mId.group(1);

            String sessJson = httpGetString("https://sessionserver.mojang.com/session/minecraft/profile/" + mojangId);
            if (sessJson == null) return null;
            Matcher mVal = VAL_PAT.matcher(sessJson);
            if (!mVal.find()) return null;
            String decoded = new String(Base64.getDecoder().decode(mVal.group(1)), StandardCharsets.UTF_8);

            Matcher mUrl = URL_PAT.matcher(decoded);
            if (!mUrl.find()) return null;
            String skinUrl = mUrl.group(1);
            boolean slim = SLIM_PAT.matcher(decoded).find();

            byte[] pngBytes = httpGetBytes(skinUrl);
            if (pngBytes != null && pngBytes.length > 64 && pngBytes.length <= 65536) {
                return new SkinRecord(playerUuid, playerName, slim, pngBytes);
            }
        } catch (Exception ignored) {}
        return null;
    }

    private static String httpGetString(String urlStr) {
        byte[] b = httpGetBytes(urlStr);
        return b != null ? new String(b, StandardCharsets.UTF_8) : null;
    }

    private static byte[] httpGetBytes(String urlStr) {
        try {
            HttpURLConnection conn = (HttpURLConnection) URI.create(urlStr).toURL().openConnection();
            conn.setRequestMethod("GET");
            conn.setConnectTimeout(5000);
            conn.setReadTimeout(5000);
            conn.setRequestProperty("User-Agent", "TheNestVanilla/26.3");
            if (conn.getResponseCode() != 200) return null;
            try (InputStream in = conn.getInputStream(); ByteArrayOutputStream out = new ByteArrayOutputStream()) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) != -1) {
                    out.write(buf, 0, n);
                    if (out.size() > 65536) return null;
                }
                return out.toByteArray();
            }
        } catch (Exception e) {
            return null;
        }
    }

    private static void broadcastSkinToAll(MinecraftServer srv, SkinRecord rec) {
        BroadcastSkinPayload pkt = new BroadcastSkinPayload(rec.playerUuid(), rec.playerName(), rec.slim(), rec.pngBytes());
        for (ServerPlayer p : srv.getPlayerList().getPlayers()) {
            sendSkinSafe(p, pkt);
        }
    }

    private static void sendSkinSafe(ServerPlayer target, BroadcastSkinPayload pkt) {
        try {
            PacketDistributor.sendToPlayer(target, pkt);
        } catch (Throwable ignored) {}
    }

    private static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();
        d.register(Commands.literal("skin")
                .then(Commands.literal("set")
                        .then(Commands.argument("username", StringArgumentType.word())
                                .executes(ctx -> {
                                    ServerPlayer sp = ctx.getSource().getPlayerOrException();
                                    String targetName = StringArgumentType.getString(ctx, "username");
                                    sp.sendSystemMessage(Component.literal("§6[The Nest] §7Fetching Mojang skin for §f" + targetName + "§7..."));
                                    fetchMojangSkinAsync(sp.level().getServer(), sp.getUUID(), sp.getGameProfile().name(), targetName, true, sp);
                                    return 1;
                                })))
                .then(Commands.literal("arm")
                        .then(Commands.literal("slim").executes(ctx -> setArmStyle(ctx.getSource().getPlayerOrException(), true)))
                        .then(Commands.literal("default").executes(ctx -> setArmStyle(ctx.getSource().getPlayerOrException(), false)))
                        .then(Commands.literal("wide").executes(ctx -> setArmStyle(ctx.getSource().getPlayerOrException(), false))))
                .then(Commands.literal("reset")
                        .executes(ctx -> {
                            ServerPlayer sp = ctx.getSource().getPlayerOrException();
                            String name = sp.getGameProfile().name();
                            try {
                                Files.deleteIfExists(getSavedSkinFile(name));
                            } catch (Exception ignored) {}
                            sp.sendSystemMessage(Component.literal("§6[The Nest] §7Resetting skin to your nickname (§f" + name + "§7)..."));
                            fetchMojangSkinAsync(sp.level().getServer(), sp.getUUID(), name, name, false, sp);
                            return 1;
                        })));
    }

    private static int setArmStyle(ServerPlayer sp, boolean slim) {
        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return 0;
        String name = sp.getGameProfile().name();
        String key = name.toLowerCase(Locale.ROOT);
        SkinRecord cur = ACTIVE_SKINS.get(key);
        if (cur == null) {
            sp.sendSystemMessage(Component.literal("§c[The Nest] No active custom/Mojang skin loaded yet."));
            return 0;
        }
        SkinRecord updated = new SkinRecord(sp.getUUID(), name, slim, cur.pngBytes());
        ACTIVE_SKINS.put(key, updated);
        saveCustomSkinToDisk(name, slim, cur.pngBytes());
        broadcastSkinToAll(srv, updated);
        sp.sendSystemMessage(Component.literal("§6[The Nest] §aArm model switched to §f" + (slim ? "Slim (3px Alex)" : "Default (4px Classic)") + "§a!"));
        return 1;
    }
}
"""


# 3. OpenTxAdminPayload.java
FILES["com/thenest/txadmin/OpenTxAdminPayload.java"] = """package com.thenest.txadmin;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record OpenTxAdminPayload(
        boolean god,
        boolean noclip,
        boolean fly,
        boolean vanish,
        boolean nv,
        int speed,
        int selfGm,
        String playersCsv
) implements CustomPacketPayload {

    public interface ClientHandler {
        void handleOpen(OpenTxAdminPayload payload);
    }

    private static volatile ClientHandler clientHandler;

    public static void setClientHandler(ClientHandler handler) {
        clientHandler = handler;
    }

    public static final CustomPacketPayload.Type<OpenTxAdminPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "open_panel"));

    public static final StreamCodec<RegistryFriendlyByteBuf, OpenTxAdminPayload> STREAM_CODEC =
            StreamCodec.of(OpenTxAdminPayload::encode, OpenTxAdminPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, OpenTxAdminPayload p) {
        buf.writeBoolean(p.god());
        buf.writeBoolean(p.noclip());
        buf.writeBoolean(p.fly());
        buf.writeBoolean(p.vanish());
        buf.writeBoolean(p.nv());
        buf.writeVarInt(p.speed());
        buf.writeVarInt(p.selfGm());
        buf.writeUtf(p.playersCsv() != null ? p.playersCsv() : "", 8192);
    }

    private static OpenTxAdminPayload decode(RegistryFriendlyByteBuf buf) {
        return new OpenTxAdminPayload(
                buf.readBoolean(),
                buf.readBoolean(),
                buf.readBoolean(),
                buf.readBoolean(),
                buf.readBoolean(),
                buf.readVarInt(),
                buf.readVarInt(),
                buf.readUtf(8192)
        );
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToClient(TYPE, STREAM_CODEC, OpenTxAdminPayload::handleClient);
    }

    private static void handleClient(OpenTxAdminPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            ClientHandler h = clientHandler;
            if (h != null) {
                h.handleOpen(payload);
            }
        });
    }
}
"""

# 4. TxActionPayload.java
FILES["com/thenest/txadmin/TxActionPayload.java"] = """package com.thenest.txadmin;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record TxActionPayload(String kind, String action, String target) implements CustomPacketPayload {

    public static final CustomPacketPayload.Type<TxActionPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "tx_action"));

    public static final StreamCodec<RegistryFriendlyByteBuf, TxActionPayload> STREAM_CODEC =
            StreamCodec.of(TxActionPayload::encode, TxActionPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, TxActionPayload p) {
        buf.writeUtf(p.kind() != null ? p.kind() : "", 64);
        buf.writeUtf(p.action() != null ? p.action() : "", 1024);
        buf.writeUtf(p.target() != null ? p.target() : "", 256);
    }

    private static TxActionPayload decode(RegistryFriendlyByteBuf buf) {
        return new TxActionPayload(
                buf.readUtf(64),
                buf.readUtf(1024),
                buf.readUtf(256)
        );
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToServer(TYPE, STREAM_CODEC, TxActionPayload::handleServer);
    }

    public static void handleServer(TxActionPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            if (!(ctx.player() instanceof ServerPlayer sp)) return;
            if (!TxAdminServer.isAdmin(sp)) {
                sp.sendSystemMessage(net.minecraft.network.chat.Component.literal("§c[The Nest] Only Server Operators (OP) can use txAdmin."));
                return;
            }
            String k = payload.kind();
            String act = payload.action();
            String tgt = payload.target();
            switch (k) {
                case "self" -> TxAdminServer.applySelfAction(sp, act, true);
                case "player" -> TxAdminServer.applyPlayerAction(sp, act, tgt, true);
                case "char" -> CharCustomServerManager.applyCharAction(sp.level().getServer(), sp, act, tgt, true);
                case "cmd" -> {
                    TxAdminServer.runAsAdmin(sp, act);
                    TxAdminServer.sendPanelState(sp, false);
                }
            }
        });
    }
}
"""

# 4b. SyncCharProfilesPayload.java
FILES["com/thenest/txadmin/SyncCharProfilesPayload.java"] = """package com.thenest.txadmin;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record SyncCharProfilesPayload(String profilesData) implements CustomPacketPayload {

    public interface ClientHandler {
        void handleSync(SyncCharProfilesPayload payload);
    }

    private static volatile ClientHandler clientHandler;

    public static void setClientHandler(ClientHandler handler) {
        clientHandler = handler;
    }

    public static final CustomPacketPayload.Type<SyncCharProfilesPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "sync_char_profiles"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SyncCharProfilesPayload> STREAM_CODEC =
            StreamCodec.of(SyncCharProfilesPayload::encode, SyncCharProfilesPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, SyncCharProfilesPayload p) {
        buf.writeUtf(p.profilesData() != null ? p.profilesData() : "", 16384);
    }

    private static SyncCharProfilesPayload decode(RegistryFriendlyByteBuf buf) {
        return new SyncCharProfilesPayload(buf.readUtf(16384));
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToClient(TYPE, STREAM_CODEC, SyncCharProfilesPayload::handleClient);
    }

    private static void handleClient(SyncCharProfilesPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            ClientHandler h = clientHandler;
            if (h != null) {
                h.handleSync(payload);
            }
        });
    }
}
"""

# 4c. CharCustomServerManager.java
FILES["com/thenest/txadmin/CharCustomServerManager.java"] = r"""package com.thenest.txadmin;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundPlayerInfoUpdatePacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.ServerScoreboard;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.scores.PlayerTeam;
import net.minecraft.world.scores.Team;
import net.minecraft.world.scores.TeamColor;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.network.PacketDistributor;

public final class CharCustomServerManager {
    public record CharProfile(
            String realName,
            String customNick,
            String colorCode,
            boolean bold,
            int opacityMode,
            boolean tabHidden,
            String teamName,
            String teamColorCode
    ) {
        public String buildFormattedString() {
            StringBuilder sb = new StringBuilder();
            if (teamName != null && !teamName.isEmpty()) {
                String tc = (teamColorCode != null && !teamColorCode.isEmpty()) ? teamColorCode : "6";
                sb.append("§").append(tc).append("[").append(teamName).append("] §r");
            }
            String cc = (colorCode != null && !colorCode.isEmpty()) ? colorCode : "f";
            sb.append("§").append(cc);
            if (bold) {
                sb.append("§l");
            }
            String nick = (customNick != null && !customNick.isBlank()) ? customNick : realName;
            sb.append(nick).append("§r");
            return sb.toString();
        }

        public Component buildFormattedComponent() {
            return Component.literal(buildFormattedString());
        }
    }

    private static final Map<String, CharProfile> PROFILES = new ConcurrentHashMap<>();
    private static volatile boolean loadedFromDisk = false;

    private CharCustomServerManager() {}

    public static void registerEvents() {
        NeoForge.EVENT_BUS.addListener(CharCustomServerManager::onPlayerJoin);
        NeoForge.EVENT_BUS.addListener(CharCustomServerManager::onNameFormat);
        NeoForge.EVENT_BUS.addListener(CharCustomServerManager::onTabListNameFormat);
        NeoForge.EVENT_BUS.addListener(CharCustomServerManager::onRegisterCommands);
    }

    private static Path getProfilesFile() {
        Path dir = Paths.get("nest_skins");
        try {
            Files.createDirectories(dir);
        } catch (Exception ignored) {}
        return dir.resolve("char_profiles.tsv");
    }

    private static synchronized void ensureLoaded() {
        if (loadedFromDisk) return;
        loadedFromDisk = true;
        Path p = getProfilesFile();
        if (!Files.exists(p)) return;
        try {
            for (String line : Files.readAllLines(p, StandardCharsets.UTF_8)) {
                if (line.isBlank()) continue;
                String[] parts = line.split("\\|", -1);
                if (parts.length >= 8) {
                    CharProfile prof = new CharProfile(
                            parts[0],
                            parts[1],
                            parts[2].isEmpty() ? "f" : parts[2],
                            "1".equals(parts[3]),
                            parseInt(parts[4], 0),
                            "1".equals(parts[5]),
                            parts[6],
                            parts[7].isEmpty() ? "6" : parts[7]
                    );
                    PROFILES.put(prof.realName().toLowerCase(Locale.ROOT), prof);
                }
            }
        } catch (Exception ignored) {}
    }

    private static synchronized void saveToDisk() {
        try {
            List<String> lines = new ArrayList<>();
            for (CharProfile prof : PROFILES.values()) {
                lines.add(encodeProfileLine(prof));
            }
            Files.write(getProfilesFile(), lines, StandardCharsets.UTF_8);
        } catch (Exception ignored) {}
    }

    private static String encodeProfileLine(CharProfile p) {
        return cleanPipe(p.realName()) + "|"
                + cleanPipe(p.customNick()) + "|"
                + cleanPipe(p.colorCode()) + "|"
                + (p.bold() ? "1" : "0") + "|"
                + p.opacityMode() + "|"
                + (p.tabHidden() ? "1" : "0") + "|"
                + cleanPipe(p.teamName()) + "|"
                + cleanPipe(p.teamColorCode());
    }

    private static String cleanPipe(String s) {
        return s == null ? "" : s.replace("|", "").replace("\n", "").replace("\r", "");
    }

    private static int parseInt(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    public static CharProfile getOrCreate(String realName) {
        ensureLoaded();
        String key = realName.toLowerCase(Locale.ROOT);
        return PROFILES.computeIfAbsent(key, k -> new CharProfile(realName, "", "f", false, 0, false, "", "6"));
    }

    public static void onPlayerJoin(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer sp)) return;
        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return;
        ensureLoaded();
        CharProfile prof = getOrCreate(sp.getGameProfile().name());
        applyScoreboardTeamForPlayer(srv, sp.getGameProfile().name(), prof.teamName(), prof.teamColorCode());
        sp.refreshDisplayName();
        sp.refreshTabListName();
        syncAllToClients(srv);
    }

    public static void onNameFormat(PlayerEvent.NameFormat event) {
        String name = event.getEntity().getGameProfile().name();
        if (name == null) return;
        ensureLoaded();
        CharProfile prof = PROFILES.get(name.toLowerCase(Locale.ROOT));
        if (prof != null) {
            event.setDisplayname(prof.buildFormattedComponent());
        }
    }

    public static void onTabListNameFormat(PlayerEvent.TabListNameFormat event) {
        String name = event.getEntity().getGameProfile().name();
        if (name == null) return;
        ensureLoaded();
        CharProfile prof = PROFILES.get(name.toLowerCase(Locale.ROOT));
        if (prof != null) {
            event.setDisplayName(prof.buildFormattedComponent());
        }
    }

    public static void syncAllToClients(MinecraftServer srv) {
        if (srv == null) return;
        ensureLoaded();
        for (ServerPlayer sp : srv.getPlayerList().getPlayers()) {
            getOrCreate(sp.getGameProfile().name());
            sp.refreshDisplayName();
            sp.refreshTabListName();
            try {
                srv.getPlayerList().broadcastAll(new ClientboundPlayerInfoUpdatePacket(ClientboundPlayerInfoUpdatePacket.Action.UPDATE_DISPLAY_NAME, sp));
            } catch (Throwable ignored) {}
        }
        StringBuilder sb = new StringBuilder();
        for (CharProfile prof : PROFILES.values()) {
            if (sb.length() > 0) sb.append("\n");
            sb.append(encodeProfileLine(prof));
        }
        SyncCharProfilesPayload pkt = new SyncCharProfilesPayload(sb.toString());
        for (ServerPlayer sp : srv.getPlayerList().getPlayers()) {
            try {
                PacketDistributor.sendToPlayer(sp, pkt);
            } catch (Throwable ignored) {}
        }
    }

    private static List<String> resolveTargetNames(MinecraftServer srv, ServerPlayer sender, String target) {
        List<String> out = new ArrayList<>();
        if (target == null || target.isBlank() || "@s".equalsIgnoreCase(target)) {
            if (sender != null) out.add(sender.getGameProfile().name());
            return out;
        }
        if ("@a".equalsIgnoreCase(target)) {
            for (ServerPlayer sp : srv.getPlayerList().getPlayers()) {
                out.add(sp.getGameProfile().name());
            }
            for (CharProfile p : PROFILES.values()) {
                if (!out.contains(p.realName())) out.add(p.realName());
            }
            return out;
        }
        ServerPlayer online = srv.getPlayerList().getPlayerByName(target);
        out.add(online != null ? online.getGameProfile().name() : target.trim());
        return out;
    }

    public static void applyCharAction(MinecraftServer srv, ServerPlayer admin, String action, String target, boolean syncGui) {
        if (srv == null || action == null) return;
        ensureLoaded();

        if (action.startsWith("fetchskin:")) {
            String lookup = action.substring("fetchskin:".length()).trim();
            if (lookup.isEmpty() && admin != null) lookup = admin.getGameProfile().name();
            if ("@a".equalsIgnoreCase(target)) {
                for (ServerPlayer p : srv.getPlayerList().getPlayers()) {
                    SkinServerManager.fetchMojangSkinAsync(srv, p.getUUID(), p.getGameProfile().name(), lookup, true, null);
                }
            } else {
                ServerPlayer tp = srv.getPlayerList().getPlayerByName(target);
                String tName = tp != null ? tp.getGameProfile().name() : target;
                java.util.UUID tId = tp != null ? tp.getUUID() : (admin != null ? admin.getUUID() : new java.util.UUID(0L, 0L));
                SkinServerManager.fetchMojangSkinAsync(srv, tId, tName, lookup, true, admin);
            }
            return;
        }
        if ("arm:slim".equals(action)) {
            SkinServerManager.setTargetArmStyle(srv, target, true);
            return;
        }
        if ("arm:default".equals(action)) {
            SkinServerManager.setTargetArmStyle(srv, target, false);
            return;
        }
        if ("skinreset".equals(action)) {
            SkinServerManager.resetTargetSkin(srv, target, admin);
            return;
        }

        if (action.startsWith("allcolor:")) {
            String cc = action.substring("allcolor:".length()).trim();
            for (String n : resolveTargetNames(srv, admin, "@a")) {
                CharProfile cur = getOrCreate(n);
                PROFILES.put(n.toLowerCase(Locale.ROOT), new CharProfile(cur.realName(), cur.customNick(), cc, cur.bold(), cur.opacityMode(), cur.tabHidden(), cur.teamName(), cur.teamColorCode()));
            }
            saveToDisk();
            syncAllToClients(srv);
            if (syncGui && admin != null) TxAdminServer.sendPanelState(admin, false);
            return;
        }
        if ("tab:showall".equals(action) || "tab:hideall".equals(action)) {
            boolean hide = "tab:hideall".equals(action);
            for (String n : resolveTargetNames(srv, admin, "@a")) {
                CharProfile cur = getOrCreate(n);
                PROFILES.put(n.toLowerCase(Locale.ROOT), new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), hide, cur.teamName(), cur.teamColorCode()));
            }
            saveToDisk();
            syncAllToClients(srv);
            if (syncGui && admin != null) TxAdminServer.sendPanelState(admin, false);
            return;
        }
        if ("clearteams".equals(action)) {
            for (String n : resolveTargetNames(srv, admin, "@a")) {
                CharProfile cur = getOrCreate(n);
                PROFILES.put(n.toLowerCase(Locale.ROOT), new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), cur.tabHidden(), "", "6"));
                applyScoreboardTeamForPlayer(srv, cur.realName(), "", "6");
            }
            saveToDisk();
            syncAllToClients(srv);
            if (syncGui && admin != null) TxAdminServer.sendPanelState(admin, false);
            return;
        }
        if (action.startsWith("teampvp:")) {
            boolean pvp = "on".equalsIgnoreCase(action.substring("teampvp:".length()).trim());
            ServerScoreboard sb = srv.getScoreboard();
            for (PlayerTeam pt : sb.getPlayerTeams()) {
                pt.setAllowFriendlyFire(pvp);
            }
            return;
        }
        if (action.startsWith("teamvis:")) {
            String mode = action.substring("teamvis:".length()).trim().toLowerCase(Locale.ROOT);
            Team.Visibility vis = switch (mode) {
                case "never" -> Team.Visibility.NEVER;
                case "own" -> Team.Visibility.HIDE_FOR_OTHER_TEAMS;
                case "other" -> Team.Visibility.HIDE_FOR_OWN_TEAM;
                default -> Team.Visibility.ALWAYS;
            };
            ServerScoreboard sb = srv.getScoreboard();
            for (PlayerTeam pt : sb.getPlayerTeams()) {
                pt.setNameTagVisibility(vis);
            }
            return;
        }

        List<String> targets = resolveTargetNames(srv, admin, target);
        for (String n : targets) {
            CharProfile cur = getOrCreate(n);
            CharProfile updated = cur;

            if (action.startsWith("nick:")) {
                String newNick = action.substring("nick:".length()).trim();
                updated = new CharProfile(cur.realName(), newNick, cur.colorCode(), cur.bold(), cur.opacityMode(), cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if ("nickreset".equals(action)) {
                updated = new CharProfile(cur.realName(), "", cur.colorCode(), cur.bold(), cur.opacityMode(), cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if (action.startsWith("color:")) {
                String cc = action.substring("color:".length()).trim();
                updated = new CharProfile(cur.realName(), cur.customNick(), cc, cur.bold(), cur.opacityMode(), cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if ("bold:toggle".equals(action)) {
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), !cur.bold(), cur.opacityMode(), cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if (action.startsWith("opacity:")) {
                int op = parseInt(action.substring("opacity:".length()), 0);
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), op, cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if ("tab:toggle".equals(action)) {
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), !cur.tabHidden(), cur.teamName(), cur.teamColorCode());
            } else if ("tab:hide".equals(action)) {
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), true, cur.teamName(), cur.teamColorCode());
            } else if ("tab:show".equals(action)) {
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), false, cur.teamName(), cur.teamColorCode());
            } else if (action.startsWith("team:")) {
                // team:<TeamName>:<colorCode>
                String[] parts = action.split(":", 3);
                String tName = parts.length > 1 ? parts[1].trim() : "Red";
                String tCol = parts.length > 2 ? parts[2].trim() : "c";
                updated = new CharProfile(cur.realName(), cur.customNick(), tCol, cur.bold(), cur.opacityMode(), cur.tabHidden(), tName, tCol);
                applyScoreboardTeamForPlayer(srv, cur.realName(), tName, tCol);
            } else if (action.startsWith("mkteam:")) {
                // mkteam:<colorCode>:<CustomName>
                String[] parts = action.split(":", 3);
                String tCol = parts.length > 1 ? parts[1].trim() : "6";
                String tName = parts.length > 2 ? parts[2].trim() : "VIP";
                if (tName.isEmpty()) tName = "VIP";
                updated = new CharProfile(cur.realName(), cur.customNick(), tCol, cur.bold(), cur.opacityMode(), cur.tabHidden(), tName, tCol);
                applyScoreboardTeamForPlayer(srv, cur.realName(), tName, tCol);
            } else if ("teamleave".equals(action)) {
                updated = new CharProfile(cur.realName(), cur.customNick(), cur.colorCode(), cur.bold(), cur.opacityMode(), cur.tabHidden(), "", "6");
                applyScoreboardTeamForPlayer(srv, cur.realName(), "", "6");
            } else if ("resetall".equals(action)) {
                updated = new CharProfile(cur.realName(), "", "f", false, 0, false, "", "6");
                applyScoreboardTeamForPlayer(srv, cur.realName(), "", "6");
            }

            PROFILES.put(n.toLowerCase(Locale.ROOT), updated);
        }

        saveToDisk();
        syncAllToClients(srv);
        if (syncGui && admin != null) {
            TxAdminServer.sendPanelState(admin, false);
        }
    }

    private static void applyScoreboardTeamForPlayer(MinecraftServer srv, String playerName, String teamName, String colorCode) {
        try {
            ServerScoreboard sb = srv.getScoreboard();
            if (teamName == null || teamName.isBlank()) {
                sb.removePlayerFromTeam(playerName);
                return;
            }
            String safeId = "nest_" + teamName.toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_]", "");
            if (safeId.length() > 16) safeId = safeId.substring(0, 16);
            PlayerTeam pt = sb.getPlayerTeam(safeId);
            if (pt == null) {
                pt = sb.addPlayerTeam(safeId);
            }
            pt.setDisplayName(Component.literal(teamName));
            pt.setPlayerPrefix(Component.literal("§" + colorCode + "[" + teamName + "] §r"));
            pt.setColor(Optional.of(codeToTeamColor(colorCode)));
            sb.addPlayerToTeam(playerName, pt);
        } catch (Throwable ignored) {}
    }

    private static TeamColor codeToTeamColor(String code) {
        if (code == null) return TeamColor.WHITE;
        return switch (code.toLowerCase(Locale.ROOT)) {
            case "0" -> TeamColor.BLACK;
            case "1" -> TeamColor.DARK_BLUE;
            case "2" -> TeamColor.DARK_GREEN;
            case "3" -> TeamColor.DARK_AQUA;
            case "4" -> TeamColor.DARK_RED;
            case "5" -> TeamColor.DARK_PURPLE;
            case "6" -> TeamColor.GOLD;
            case "7" -> TeamColor.GRAY;
            case "8" -> TeamColor.DARK_GRAY;
            case "9" -> TeamColor.BLUE;
            case "a" -> TeamColor.GREEN;
            case "b" -> TeamColor.AQUA;
            case "c" -> TeamColor.RED;
            case "d" -> TeamColor.LIGHT_PURPLE;
            case "e" -> TeamColor.YELLOW;
            default -> TeamColor.WHITE;
        };
    }

    private static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();
        // /nestchar <target> <action...> (used by Desktop Server Admin Panel & OP commands)
        d.register(Commands.literal("nestchar")
                .then(Commands.argument("target", StringArgumentType.word())
                        .then(Commands.argument("action", StringArgumentType.greedyString())
                                .executes(ctx -> {
                                    CommandSourceStack src = ctx.getSource();
                                    ServerPlayer sp = src.getPlayer();
                                    if (sp != null && !TxAdminServer.isAdmin(sp)) {
                                        sp.sendSystemMessage(Component.literal("§c[The Nest] Only Server Operators can use /nestchar."));
                                        return 0;
                                    }
                                    String tgt = StringArgumentType.getString(ctx, "target");
                                    String act = StringArgumentType.getString(ctx, "action");
                                    applyCharAction(src.getServer(), sp, act, tgt, true);
                                    return 1;
                                }))));
    }
}
"""

# 5. TxAdminServer.java
FILES["com/thenest/txadmin/TxAdminServer.java"] = r"""package com.thenest.txadmin;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.world.Container;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.gamerules.GameRule;
import net.minecraft.world.level.gamerules.GameRules;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;

public final class TxAdminServer {
    public record SavedPos(ResourceKey<Level> dimension, double x, double y, double z, float yRot, float xRot) {}

    public static final Set<UUID> GOD_PLAYERS = ConcurrentHashMap.newKeySet();
    public static final Map<UUID, GameType> NOCLIP_PREV_MODE = new ConcurrentHashMap<>();
    public static final Set<UUID> FLY_PLAYERS = ConcurrentHashMap.newKeySet();
    public static final Set<UUID> VANISH_PLAYERS = ConcurrentHashMap.newKeySet();
    public static final Set<UUID> NV_PLAYERS = ConcurrentHashMap.newKeySet();
    public static final Map<UUID, Integer> SPEED_PLAYERS = new ConcurrentHashMap<>();
    public static final Map<UUID, SavedPos> RETURN_POSITIONS = new ConcurrentHashMap<>();
    public static final Map<UUID, SavedPos> FROZEN_PLAYERS = new ConcurrentHashMap<>();

    private static int tickCounter = 0;

    private TxAdminServer() {}

    public static void registerEvents() {
        NeoForge.EVENT_BUS.addListener(TxAdminServer::onRegisterCommands);
        NeoForge.EVENT_BUS.addListener(TxAdminServer::onLivingDamage);
        NeoForge.EVENT_BUS.addListener(TxAdminServer::onServerTick);
    }

    public static boolean isAdmin(ServerPlayer player) {
        if (player == null) return false;
        MinecraftServer srv = player.level().getServer();
        if (srv == null) return false;
        return srv.getPlayerList().isOp(player.nameAndId())
                || srv.isSingleplayerOwner(player.nameAndId())
                || player.canUseGameMasterBlocks();
    }

    private static boolean checkAdminOrReply(CommandSourceStack src) {
        ServerPlayer p = src.getPlayer();
        if (p == null) return true;
        if (!isAdmin(p)) {
            p.sendSystemMessage(Component.literal("§c[The Nest] Only Server Operators (OP) can use txAdmin commands."));
            return false;
        }
        return true;
    }

    public static int gmToInt(GameType gm) {
        if (gm == GameType.CREATIVE) return 1;
        if (gm == GameType.ADVENTURE) return 2;
        if (gm == GameType.SPECTATOR) return 3;
        return 0;
    }

    public static void sendPanelState(ServerPlayer admin, boolean openScreen) {
        MinecraftServer srv = admin.level().getServer();
        if (srv == null) return;
        UUID id = admin.getUUID();
        boolean god = GOD_PLAYERS.contains(id);
        boolean noclip = admin.gameMode() == GameType.SPECTATOR && NOCLIP_PREV_MODE.containsKey(id);
        boolean fly = FLY_PLAYERS.contains(id) || admin.getAbilities().mayfly;
        boolean vanish = VANISH_PLAYERS.contains(id);
        boolean nv = NV_PLAYERS.contains(id);
        int speed = SPEED_PLAYERS.getOrDefault(id, 0);
        int selfGm = gmToInt(admin.gameMode());

        // Encode each online player as name|gm|op|frozen
        List<String> entries = srv.getPlayerList().getPlayers().stream()
                .sorted(Comparator.comparing(sp -> sp.getGameProfile().name(), String::compareToIgnoreCase))
                .map(sp -> {
                    String n = sp.getGameProfile().name();
                    int gm = gmToInt(sp.gameMode());
                    int op = srv.getPlayerList().isOp(sp.nameAndId()) ? 1 : 0;
                    int frz = FROZEN_PLAYERS.containsKey(sp.getUUID()) ? 1 : 0;
                    return n + "|" + gm + "|" + op + "|" + frz;
                })
                .collect(Collectors.toList());
        String worldMeta = "";
        try {
            ServerLevel ov = srv.overworld();
            long dayTime = srv.clockManager().getInstance(
                    ov.registryAccess().lookupOrThrow(net.minecraft.core.registries.Registries.WORLD_CLOCK)
                            .getOrThrow(net.minecraft.world.clock.WorldClocks.OVERWORLD)
            ).totalTicks() % 24000L;
            int weather = ov.isThundering() ? 2 : (ov.isRaining() ? 1 : 0);
            int diff = srv.getWorldData().getDifficulty().getId();
            int tickRate = (int) Math.round(srv.tickRateManager().tickrate());
            int tickFrozen = srv.tickRateManager().isFrozen() ? 1 : 0;
            long border = Math.round(ov.getWorldBorder().getSize());
            GameRules gr = ov.getGameRules();
            int sleepPct = gr.get(GameRules.PLAYERS_SLEEPING_PERCENTAGE);
            int tickSpeed = gr.get(GameRules.RANDOM_TICK_SPEED);
            int fireSpread = gr.get(GameRules.FIRE_SPREAD_RADIUS_AROUND_PLAYER);
            @SuppressWarnings("unchecked")
            GameRule<Boolean>[] boolRules = new GameRule[] {
                    GameRules.KEEP_INVENTORY,
                    GameRules.MOB_GRIEFING,
                    GameRules.PVP,
                    GameRules.LOCATOR_BAR,
                    GameRules.SPAWN_PHANTOMS,
                    GameRules.ADVANCE_TIME,
                    GameRules.ADVANCE_WEATHER,
                    GameRules.SPAWN_PATROLS,
                    GameRules.SPAWN_WANDERING_TRADERS,
                    GameRules.SPAWN_WARDENS,
                    GameRules.SPAWN_MOBS,
                    GameRules.FALL_DAMAGE,
                    GameRules.TNT_EXPLODES,
                    GameRules.SHOW_ADVANCEMENT_MESSAGES,
                    GameRules.SHOW_DEATH_MESSAGES,
                    GameRules.IMMEDIATE_RESPAWN
            };
            int grMask = 0;
            for (int i = 0; i < boolRules.length; i++) {
                if (Boolean.TRUE.equals(gr.get(boolRules[i]))) {
                    grMask |= (1 << i);
                }
            }
            worldMeta = ";W:" + dayTime + "|" + weather + "|" + diff + "|" + tickRate + "|" + tickFrozen
                    + "|" + border + "|" + sleepPct + "|" + tickSpeed + "|" + fireSpread + "|" + grMask;
        } catch (Throwable ignored) {}

        String csv = (openScreen ? "OPEN:" : "SYNC:") + String.join(",", entries) + worldMeta;
        try {
            PacketDistributor.sendToPlayer(admin, new OpenTxAdminPayload(god, noclip, fly, vanish, nv, speed, selfGm, csv));
        } catch (Throwable t) {
            if (openScreen) {
                TxAdminChestGui.open(admin, 0, 0);
            }
        }
    }

    private static void onLivingDamage(LivingIncomingDamageEvent event) {
        if (event.getEntity() instanceof ServerPlayer sp) {
            if (GOD_PLAYERS.contains(sp.getUUID()) || FROZEN_PLAYERS.containsKey(sp.getUUID())) {
                event.setCanceled(true);
            }
        }
    }

    private static void onServerTick(ServerTickEvent.Post event) {
        MinecraftServer srv = event.getServer();
        tickCounter++;

        if (!FROZEN_PLAYERS.isEmpty() && (tickCounter % 2 == 0)) {
            for (Map.Entry<UUID, SavedPos> e : FROZEN_PLAYERS.entrySet()) {
                ServerPlayer sp = srv.getPlayerList().getPlayer(e.getKey());
                if (sp != null) {
                    SavedPos pos = e.getValue();
                    ServerLevel targetLvl = srv.getLevel(pos.dimension());
                    if (targetLvl != null) {
                        double dx = sp.getX() - pos.x();
                        double dy = sp.getY() - pos.y();
                        double dz = sp.getZ() - pos.z();
                        if (sp.level() != targetLvl || (dx * dx + dy * dy + dz * dz) > 0.04) {
                            sp.teleportTo(targetLvl, pos.x(), pos.y(), pos.z(), Set.of(), pos.yRot(), pos.xRot(), false);
                        }
                    }
                    if (tickCounter % 20 == 0) {
                        runServerCmd(srv, "title " + sp.getGameProfile().name()
                                + " actionbar {\"text\":\"❄ FROZEN BY ADMIN — DO NOT DISCONNECT\",\"color\":\"aqua\",\"bold\":true}");
                    }
                }
            }
        }

        if (tickCounter % 20 == 0) {
            for (ServerPlayer sp : srv.getPlayerList().getPlayers()) {
                UUID id = sp.getUUID();
                if (GOD_PLAYERS.contains(id)) {
                    sp.setHealth(sp.getMaxHealth());
                    sp.getFoodData().setFoodLevel(20);
                    sp.getFoodData().setSaturation(20.0f);
                    sp.clearFire();
                    if (!sp.getAbilities().invulnerable) {
                        sp.getAbilities().invulnerable = true;
                        sp.onUpdateAbilities();
                    }
                }
                if (FLY_PLAYERS.contains(id) && !sp.getAbilities().mayfly) {
                    sp.getAbilities().mayfly = true;
                    sp.onUpdateAbilities();
                }
                if (VANISH_PLAYERS.contains(id)) {
                    sp.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, 400, 0, true, false, true));
                }
                if (NV_PLAYERS.contains(id)) {
                    sp.addEffect(new MobEffectInstance(MobEffects.NIGHT_VISION, 400, 0, true, false, true));
                }
                Integer spd = SPEED_PLAYERS.get(id);
                if (spd != null && spd > 0) {
                    sp.addEffect(new MobEffectInstance(MobEffects.SPEED, 400, spd - 1, true, false, true));
                }
            }
        }
    }

    private static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();

        for (String rootName : new String[]{"adminpanel", "ap", "tx"}) {
            d.register(Commands.literal(rootName)
                    .executes(ctx -> {
                        if (!checkAdminOrReply(ctx.getSource())) return 0;
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        sendPanelState(sp, true);
                        return 1;
                    })
                    .then(Commands.literal("gui")
                            .executes(ctx -> {
                                if (!checkAdminOrReply(ctx.getSource())) return 0;
                                ServerPlayer sp = ctx.getSource().getPlayerOrException();
                                TxAdminChestGui.open(sp, 0, 0);
                                return 1;
                            }))
                    .then(Commands.literal("self")
                            .then(Commands.argument("action", StringArgumentType.word())
                                    .executes(TxAdminServer::execSelfAction)))
                    .then(Commands.literal("p")
                            .then(Commands.argument("action", StringArgumentType.word())
                                    .then(Commands.argument("target", StringArgumentType.greedyString())
                                            .executes(TxAdminServer::execPlayerAction))))
                    .then(Commands.literal("cmd")
                            .then(Commands.argument("raw", StringArgumentType.greedyString())
                                    .executes(ctx -> {
                                        if (!checkAdminOrReply(ctx.getSource())) return 0;
                                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                                        String raw = StringArgumentType.getString(ctx, "raw");
                                        runAsAdmin(sp, raw);
                                        sendPanelState(sp, false);
                                        return 1;
                                    })))
            );
        }

        d.register(Commands.literal("god").executes(ctx -> runQuickSelf(ctx, "god")));
        d.register(Commands.literal("noclip").executes(ctx -> runQuickSelf(ctx, "noclip")));
        d.register(Commands.literal("fly").executes(ctx -> runQuickSelf(ctx, "fly")));
        d.register(Commands.literal("vanish").executes(ctx -> runQuickSelf(ctx, "vanish")));
        d.register(Commands.literal("heal")
                .executes(ctx -> runQuickSelf(ctx, "heal"))
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "heal"))));
        d.register(Commands.literal("tpto")
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "tpto"))));
        d.register(Commands.literal("bring")
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "bring"))));
        d.register(Commands.literal("return")
                .executes(ctx -> {
                    if (!checkAdminOrReply(ctx.getSource())) return 0;
                    ServerPlayer sp = ctx.getSource().getPlayerOrException();
                    returnPlayer(sp, sp);
                    return 1;
                })
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "back"))));
        d.register(Commands.literal("freeze")
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "freeze"))));
        d.register(Commands.literal("invsee")
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "invsee"))));
        d.register(Commands.literal("endersee")
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> runQuickPlayer(ctx, "endersee"))));
    }

    private static int runQuickSelf(CommandContext<CommandSourceStack> ctx, String act) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        if (!checkAdminOrReply(ctx.getSource())) return 0;
        ServerPlayer sp = ctx.getSource().getPlayerOrException();
        applySelfAction(sp, act, false);
        return 1;
    }

    private static int runQuickPlayer(CommandContext<CommandSourceStack> ctx, String act) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        if (!checkAdminOrReply(ctx.getSource())) return 0;
        ServerPlayer sp = ctx.getSource().getPlayerOrException();
        String target = StringArgumentType.getString(ctx, "target");
        applyPlayerAction(sp, act, target, false);
        return 1;
    }

    private static int execSelfAction(CommandContext<CommandSourceStack> ctx) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        if (!checkAdminOrReply(ctx.getSource())) return 0;
        ServerPlayer sp = ctx.getSource().getPlayerOrException();
        String act = StringArgumentType.getString(ctx, "action");
        applySelfAction(sp, act, true);
        return 1;
    }

    public static void applySelfAction(ServerPlayer sp, String act, boolean syncGui) {
        UUID id = sp.getUUID();
        switch (act) {
            case "god" -> {
                if (GOD_PLAYERS.contains(id)) {
                    GOD_PLAYERS.remove(id);
                    if (sp.gameMode() == GameType.SURVIVAL || sp.gameMode() == GameType.ADVENTURE) {
                        sp.getAbilities().invulnerable = false;
                        sp.onUpdateAbilities();
                    }
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fGod Mode: §cOFF"));
                } else {
                    GOD_PLAYERS.add(id);
                    sp.setHealth(sp.getMaxHealth());
                    sp.getFoodData().setFoodLevel(20);
                    sp.getFoodData().setSaturation(20.0f);
                    sp.clearFire();
                    sp.getAbilities().invulnerable = true;
                    sp.onUpdateAbilities();
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fGod Mode: §aON"));
                }
            }
            case "noclip" -> {
                if (sp.gameMode() == GameType.SPECTATOR) {
                    GameType prev = NOCLIP_PREV_MODE.getOrDefault(id, GameType.SURVIVAL);
                    NOCLIP_PREV_MODE.remove(id);
                    sp.setGameMode(prev);
                    if (FLY_PLAYERS.contains(id) || GOD_PLAYERS.contains(id)) {
                        sp.getAbilities().mayfly = true;
                        sp.getAbilities().flying = true;
                        sp.onUpdateAbilities();
                    }
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fNoClip: §cOFF §7(" + prev.getName() + ")"));
                } else {
                    NOCLIP_PREV_MODE.put(id, sp.gameMode());
                    sp.setGameMode(GameType.SPECTATOR);
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fNoClip: §aON §7(Spectator pass-through)"));
                }
            }
            case "fly" -> {
                if (FLY_PLAYERS.contains(id)) {
                    FLY_PLAYERS.remove(id);
                    if (sp.gameMode() == GameType.SURVIVAL || sp.gameMode() == GameType.ADVENTURE) {
                        sp.getAbilities().mayfly = false;
                        sp.getAbilities().flying = false;
                        sp.onUpdateAbilities();
                    }
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fSurvival Flight: §cOFF"));
                } else {
                    FLY_PLAYERS.add(id);
                    sp.getAbilities().mayfly = true;
                    sp.onUpdateAbilities();
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fSurvival Flight: §aON"));
                }
            }
            case "vanish" -> {
                if (VANISH_PLAYERS.contains(id)) {
                    VANISH_PLAYERS.remove(id);
                    sp.removeEffect(MobEffects.INVISIBILITY);
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fVanish: §cOFF (Visible)"));
                } else {
                    VANISH_PLAYERS.add(id);
                    sp.addEffect(new MobEffectInstance(MobEffects.INVISIBILITY, 400, 0, true, false, true));
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fVanish: §aON (Invisible)"));
                }
            }
            case "nv" -> {
                if (NV_PLAYERS.contains(id)) {
                    NV_PLAYERS.remove(id);
                    sp.removeEffect(MobEffects.NIGHT_VISION);
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fNight Vision: §cOFF"));
                } else {
                    NV_PLAYERS.add(id);
                    sp.addEffect(new MobEffectInstance(MobEffects.NIGHT_VISION, 400, 0, true, false, true));
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fNight Vision: §aON"));
                }
            }
            case "speed0", "speed1", "speed2", "speed3" -> {
                int lvl = Integer.parseInt(act.substring(5));
                if (lvl <= 0) {
                    SPEED_PLAYERS.remove(id);
                    sp.removeEffect(MobEffects.SPEED);
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fSpeed Boost: §7Normal (1x)"));
                } else {
                    SPEED_PLAYERS.put(id, lvl);
                    sp.addEffect(new MobEffectInstance(MobEffects.SPEED, 400, lvl - 1, true, false, true));
                    sp.sendSystemMessage(Component.literal("§6[txAdmin] §fSpeed Boost: §aLevel " + lvl));
                }
            }
            case "heal" -> {
                healAndFeed(sp);
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §aRestored full health, hunger, and saturation!"));
            }
            case "clearfx" -> {
                sp.removeAllEffects();
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §eCleared all active potion effects."));
            }
            case "gms" -> {
                NOCLIP_PREV_MODE.remove(id);
                sp.setGameMode(GameType.SURVIVAL);
                if (FLY_PLAYERS.contains(id) || GOD_PLAYERS.contains(id)) {
                    sp.getAbilities().mayfly = true;
                    sp.onUpdateAbilities();
                }
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §fPersonal Gamemode: §aSURVIVAL"));
            }
            case "gmc" -> {
                NOCLIP_PREV_MODE.remove(id);
                sp.setGameMode(GameType.CREATIVE);
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §fPersonal Gamemode: §aCREATIVE"));
            }
            case "gma" -> {
                NOCLIP_PREV_MODE.remove(id);
                sp.setGameMode(GameType.ADVENTURE);
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §fPersonal Gamemode: §aADVENTURE"));
            }
            case "gmsp" -> {
                sp.setGameMode(GameType.SPECTATOR);
                sp.sendSystemMessage(Component.literal("§6[txAdmin] §fPersonal Gamemode: §aSPECTATOR"));
            }
        }
        if (syncGui) {
            sendPanelState(sp, false);
        }
    }

    private static int execPlayerAction(CommandContext<CommandSourceStack> ctx) throws com.mojang.brigadier.exceptions.CommandSyntaxException {
        if (!checkAdminOrReply(ctx.getSource())) return 0;
        ServerPlayer admin = ctx.getSource().getPlayerOrException();
        String act = StringArgumentType.getString(ctx, "action");
        String targetName = StringArgumentType.getString(ctx, "target").trim();
        applyPlayerAction(admin, act, targetName, true);
        return 1;
    }

    public static void applyPlayerAction(ServerPlayer admin, String act, String targetName) {
        applyPlayerAction(admin, act, targetName, false);
    }

    public static void applyPlayerAction(ServerPlayer admin, String act, String targetName, boolean syncGui) {
        MinecraftServer srv = admin.level().getServer();
        if (srv == null) return;
        ServerPlayer target = srv.getPlayerList().getPlayerByName(targetName);

        switch (act) {
            case "tpto" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                savePos(admin);
                admin.teleportTo(target.level(), target.getX(), target.getY(), target.getZ(), Set.of(), target.getYRot(), target.getXRot(), false);
                admin.sendSystemMessage(Component.literal("§6[txAdmin] §aTeleported to §e" + target.getGameProfile().name()));
            }
            case "bring" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                savePos(target);
                target.teleportTo(admin.level(), admin.getX(), admin.getY(), admin.getZ(), Set.of(), admin.getYRot(), admin.getXRot(), false);
                admin.sendSystemMessage(Component.literal("§6[txAdmin] §aBrought §e" + target.getGameProfile().name() + " §ato your location."));
                target.sendSystemMessage(Component.literal("§6[The Nest] §eAn admin teleported you to their location."));
            }
            case "back" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                returnPlayer(admin, target);
            }
            case "spectate" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                savePos(admin);
                NOCLIP_PREV_MODE.putIfAbsent(admin.getUUID(), admin.gameMode());
                admin.setGameMode(GameType.SPECTATOR);
                admin.teleportTo(target.level(), target.getX(), target.getY() + 1.0, target.getZ(), Set.of(), target.getYRot(), target.getXRot(), false);
                admin.sendSystemMessage(Component.literal("§6[txAdmin] §bSpectating §e" + target.getGameProfile().name() + " §7(use /noclip or /return to exit)"));
            }
            case "freeze" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                UUID tid = target.getUUID();
                if (FROZEN_PLAYERS.containsKey(tid)) {
                    FROZEN_PLAYERS.remove(tid);
                    admin.sendSystemMessage(Component.literal("§6[txAdmin] §aUnfroze §e" + target.getGameProfile().name()));
                    target.sendSystemMessage(Component.literal("§a[The Nest] You have been unfrozen by an admin."));
                } else {
                    FROZEN_PLAYERS.put(tid, new SavedPos(target.level().dimension(), target.getX(), target.getY(), target.getZ(), target.getYRot(), target.getXRot()));
                    admin.sendSystemMessage(Component.literal("§6[txAdmin] §bFroze §e" + target.getGameProfile().name() + " §bin place."));
                    target.sendSystemMessage(Component.literal("§c§l[The Nest] You have been frozen by an Admin! Do not disconnect."));
                }
            }
            case "unfreeze" -> {
                if (target != null) {
                    FROZEN_PLAYERS.remove(target.getUUID());
                    admin.sendSystemMessage(Component.literal("§6[txAdmin] §aUnfroze §e" + target.getGameProfile().name()));
                    target.sendSystemMessage(Component.literal("§a[The Nest] You have been unfrozen by an admin."));
                }
            }
            case "heal" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                healAndFeed(target);
                admin.sendSystemMessage(Component.literal("§6[txAdmin] §aHealed and fed §e" + target.getGameProfile().name()));
                target.sendSystemMessage(Component.literal("§a[The Nest] You were healed and fed by an admin!"));
            }
            case "gms", "gmc", "gma", "gmsp" -> {
                if ("@a".equals(targetName)) {
                    String modeStr = switch (act) {
                        case "gmc" -> "creative";
                        case "gma" -> "adventure";
                        case "gmsp" -> "spectator";
                        default -> "survival";
                    };
                    runAsAdmin(admin, "gamemode " + modeStr + " @a");
                    admin.sendSystemMessage(Component.literal("§6[txAdmin] §fSet §e@a §fgamemode to §a" + modeStr.toUpperCase()));
                } else if (target != null) {
                    GameType gt = switch (act) {
                        case "gmc" -> GameType.CREATIVE;
                        case "gma" -> GameType.ADVENTURE;
                        case "gmsp" -> GameType.SPECTATOR;
                        default -> GameType.SURVIVAL;
                    };
                    NOCLIP_PREV_MODE.remove(target.getUUID());
                    target.setGameMode(gt);
                    if (gt == GameType.SURVIVAL && (FLY_PLAYERS.contains(target.getUUID()) || GOD_PLAYERS.contains(target.getUUID()))) {
                        target.getAbilities().mayfly = true;
                        target.onUpdateAbilities();
                    }
                    admin.sendSystemMessage(Component.literal("§6[txAdmin] §fSet §e" + target.getGameProfile().name() + " §fgamemode to §a" + gt.getName().toUpperCase()));
                } else {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                }
            }
            case "invsee" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                openInvSee(admin, target);
                return;
            }
            case "endersee" -> {
                if (target == null) {
                    admin.sendSystemMessage(Component.literal("§c[txAdmin] Player '" + targetName + "' is not online."));
                    return;
                }
                admin.openMenu(new SimpleMenuProvider(
                        (id, adminInv, p) -> ChestMenu.threeRows(id, adminInv, target.getEnderChestInventory()),
                        Component.literal("§8EnderChest: §6" + target.getGameProfile().name())
                ));
                return;
            }
        }
        if (syncGui) {
            sendPanelState(admin, false);
        }
    }

    private static void openInvSee(ServerPlayer admin, ServerPlayer target) {
        Inventory targetInv = target.getInventory();
        Container wrapper = new Container() {
            @Override
            public int getContainerSize() {
                return 36;
            }

            @Override
            public boolean isEmpty() {
                return targetInv.isEmpty();
            }

            @Override
            public ItemStack getItem(int slot) {
                return slot >= 0 && slot < 36 ? targetInv.getItem(slot) : ItemStack.EMPTY;
            }

            @Override
            public ItemStack removeItem(int slot, int amount) {
                return slot >= 0 && slot < 36 ? targetInv.removeItem(slot, amount) : ItemStack.EMPTY;
            }

            @Override
            public ItemStack removeItemNoUpdate(int slot) {
                return slot >= 0 && slot < 36 ? targetInv.removeItemNoUpdate(slot) : ItemStack.EMPTY;
            }

            @Override
            public void setItem(int slot, ItemStack stack) {
                if (slot >= 0 && slot < 36) {
                    targetInv.setItem(slot, stack);
                }
            }

            @Override
            public void setChanged() {
                targetInv.setChanged();
            }

            @Override
            public boolean stillValid(Player player) {
                return !target.isRemoved();
            }

            @Override
            public void clearContent() {
                for (int i = 0; i < 36; i++) targetInv.setItem(i, ItemStack.EMPTY);
            }
        };

        admin.openMenu(new SimpleMenuProvider(
                (id, adminInv, p) -> new ChestMenu(net.minecraft.world.inventory.MenuType.GENERIC_9x4, id, adminInv, wrapper, 4),
                Component.literal("§8Inventory: §6" + target.getGameProfile().name())
        ));
    }

    private static void savePos(ServerPlayer p) {
        RETURN_POSITIONS.put(p.getUUID(), new SavedPos(
                p.level().dimension(), p.getX(), p.getY(), p.getZ(), p.getYRot(), p.getXRot()
        ));
    }

    private static void returnPlayer(ServerPlayer admin, ServerPlayer target) {
        SavedPos pos = RETURN_POSITIONS.remove(target.getUUID());
        if (pos == null) {
            admin.sendSystemMessage(Component.literal("§e[txAdmin] No saved return position for " + target.getGameProfile().name()));
            return;
        }
        MinecraftServer srv = admin.level().getServer();
        if (srv == null) return;
        ServerLevel lvl = srv.getLevel(pos.dimension());
        if (lvl != null) {
            target.teleportTo(lvl, pos.x(), pos.y(), pos.z(), Set.of(), pos.yRot(), pos.xRot(), false);
            admin.sendSystemMessage(Component.literal("§6[txAdmin] §aReturned §e" + target.getGameProfile().name() + " §ato previous location."));
        }
    }

    private static void healAndFeed(ServerPlayer p) {
        p.setHealth(p.getMaxHealth());
        p.getFoodData().setFoodLevel(20);
        p.getFoodData().setSaturation(20.0f);
        p.clearFire();
    }

    public static void runAsAdmin(ServerPlayer admin, String rawCmd) {
        MinecraftServer srv = admin.level().getServer();
        if (srv == null) return;
        String clean = rawCmd.startsWith("/") ? rawCmd.substring(1) : rawCmd;
        CommandSourceStack elevated = admin.createCommandSourceStack().withMaximumPermission(PermissionSet.ALL_PERMISSIONS);
        srv.getCommands().performPrefixedCommand(elevated, clean);
    }

    private static void runServerCmd(MinecraftServer srv, String rawCmd) {
        srv.getCommands().performPrefixedCommand(srv.createCommandSourceStack().withSuppressedOutput(), rawCmd);
    }
}
"""

# 6. TxAdminChestGui.java
FILES["com/thenest/txadmin/TxAdminChestGui.java"] = r"""package com.thenest.txadmin;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.function.BiConsumer;
import java.util.stream.Collectors;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.SimpleMenuProvider;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.ChestMenu;
import net.minecraft.world.inventory.ContainerInput;
import net.minecraft.world.inventory.MenuType;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.component.ItemLore;
import net.minecraft.world.level.GameType;

public final class TxAdminChestGui extends ChestMenu {
    private final ServerPlayer admin;
    private final SimpleContainer box;
    private int category;
    private int playerIdx;
    private final Map<Integer, BiConsumer<ServerPlayer, Integer>> actions = new HashMap<>();

    public static void open(ServerPlayer admin, int category, int playerIdx) {
        SimpleContainer box = new SimpleContainer(54);
        admin.openMenu(new SimpleMenuProvider(
                (id, inv, p) -> new TxAdminChestGui(id, inv, box, admin, category, playerIdx),
                Component.literal("§6§lThe Nest §8— §fAdmin Panel")
        ));
    }

    private TxAdminChestGui(int id, Inventory inv, SimpleContainer box, ServerPlayer admin, int category, int playerIdx) {
        super(MenuType.GENERIC_9x6, id, inv, box, 6);
        this.admin = admin;
        this.box = box;
        this.category = category;
        this.playerIdx = playerIdx;
        rebuild();
    }

    private List<String> getPlayerList() {
        List<String> list = new ArrayList<>();
        MinecraftServer srv = admin.level().getServer();
        if (srv != null) {
            list.addAll(srv.getPlayerList().getPlayers().stream()
                    .map(sp -> sp.getGameProfile().name())
                    .sorted(String::compareToIgnoreCase)
                    .collect(Collectors.toList()));
        }
        if (list.isEmpty()) list.add(admin.getGameProfile().name());
        list.add("@a");
        return list;
    }

    private String getTarget() {
        List<String> list = getPlayerList();
        if (playerIdx < 0 || playerIdx >= list.size()) playerIdx = 0;
        return list.get(playerIdx);
    }

    private static ItemStack icon(Item item, String name, boolean glint, String... loreLines) {
        ItemStack st = new ItemStack(item);
        st.set(DataComponents.CUSTOM_NAME, Component.literal(name));
        if (glint) {
            st.set(DataComponents.ENCHANTMENT_GLINT_OVERRIDE, Boolean.TRUE);
        }
        if (loreLines.length > 0) {
            List<Component> lines = new ArrayList<>();
            for (String l : loreLines) lines.add(Component.literal(l));
            st.set(DataComponents.LORE, new ItemLore(lines));
        }
        return st;
    }

    private void putSlot(int slot, ItemStack stack, BiConsumer<ServerPlayer, Integer> onClick) {
        box.setItem(slot, stack);
        if (onClick != null) {
            actions.put(slot, onClick);
        }
    }

    private void rebuild() {
        box.clearContent();
        actions.clear();

        String[] catNames = {
                "§6§l1. Self (txAdmin)",
                "§6§l2. Player Actions",
                "§6§l3. World, Time & Weather",
                "§6§l4. Gamerules",
                "§6§l5. Mods & Performance",
                "§6§l6. Casino & Admin Items"
        };
        Item[] catItems = {
                Items.TOTEM_OF_UNDYING,
                Items.PLAYER_HEAD,
                Items.CLOCK,
                Items.WRITABLE_BOOK,
                Items.COMPARATOR,
                Items.GOLD_INGOT
        };
        for (int i = 0; i < 6; i++) {
            final int cat = i;
            boolean sel = (this.category == i);
            putSlot(i * 9, icon(catItems[i], catNames[i], sel,
                    sel ? "§a► Currently Selected" : "§7Click to view category"), (sp, btn) -> {
                this.category = cat;
                rebuild();
            });
        }

        String target = getTarget();
        putSlot(1, icon(Items.NAME_TAG, "§e§lTarget: §f" + target, true,
                "§7Left-Click: §fNext Player",
                "§7Right-Click: §fPrevious Player"), (sp, btn) -> {
            List<String> list = getPlayerList();
            this.playerIdx = (this.playerIdx + (btn == 1 ? -1 : 1) + list.size()) % list.size();
            rebuild();
        });
        ItemStack pane = icon(Items.GLASS_PANE, " ", false);
        putSlot(10, pane, null);
        putSlot(19, pane, null);
        putSlot(28, pane, null);
        putSlot(37, icon(Items.EMERALD, "§a§lSave World (/save-all)", false, "§7Click to save all chunks"),
                (sp, btn) -> TxAdminServer.runAsAdmin(sp, "save-all"));
        putSlot(46, icon(Items.CHEST, "§b§lBackup Now (/simplebackups)", false, "§7Click to start incremental world backup"),
                (sp, btn) -> TxAdminServer.runAsAdmin(sp, "simplebackups backup start"));

        int[] contentSlots = new int[42];
        int k = 0;
        for (int r = 0; r < 6; r++) {
            for (int c = 2; c < 9; c++) {
                contentSlots[k++] = r * 9 + c;
            }
        }
        int idx = 0;
        UUID id = admin.getUUID();

        switch (this.category) {
            case 0 -> {
                boolean god = TxAdminServer.GOD_PLAYERS.contains(id);
                boolean noclip = admin.gameMode() == GameType.SPECTATOR && TxAdminServer.NOCLIP_PREV_MODE.containsKey(id);
                boolean fly = TxAdminServer.FLY_PLAYERS.contains(id) || admin.getAbilities().mayfly;
                boolean vanish = TxAdminServer.VANISH_PLAYERS.contains(id);
                boolean nv = TxAdminServer.NV_PLAYERS.contains(id);
                int spd = TxAdminServer.SPEED_PLAYERS.getOrDefault(id, 0);

                putSlot(contentSlots[idx++], icon(Items.TOTEM_OF_UNDYING, "§6§lGod Mode: " + (god ? "§aON" : "§cOFF"), god,
                        "§7Invulnerable + Full Hunger + No Fire", "§eClick to toggle"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "god", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.ENDER_PEARL, "§6§lNoClip: " + (noclip ? "§aON" : "§cOFF"), noclip,
                        "§7Pass through walls in Spectator", "§eClick to toggle"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "noclip", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.FEATHER, "§6§lSurvival Flight: " + (fly ? "§aON" : "§cOFF"), fly,
                        "§7Fly while staying in Survival Mode", "§eClick to toggle"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "fly", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.GLASS_BOTTLE, "§6§lVanish: " + (vanish ? "§aON" : "§cOFF"), vanish,
                        "§7True particle-free invisibility", "§eClick to toggle"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "vanish", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.GOLDEN_CARROT, "§6§lNight Vision: " + (nv ? "§aON" : "§cOFF"), nv,
                        "§7Infinite fullbright night vision", "§eClick to toggle"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "nv", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.ENCHANTED_GOLDEN_APPLE, "§a§lFull Heal & Feed Self", false,
                        "§7Restores full health, food & saturation"), (sp, b) -> TxAdminServer.applySelfAction(sp, "heal", false));
                putSlot(contentSlots[idx++], icon(Items.MILK_BUCKET, "§e§lClear Potion Effects", false,
                        "§7Removes all active effects"), (sp, b) -> TxAdminServer.applySelfAction(sp, "clearfx", false));

                idx = 7;
                putSlot(contentSlots[idx++], icon(Items.SUGAR, "§b§lSpeed: Normal (1x)", spd == 0, "§7Reset movement speed"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "speed0", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.SUGAR, "§b§lSpeed Boost: 2x", spd == 1, "§7Speed I"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "speed1", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.SUGAR, "§b§lSpeed Boost: 4x", spd == 2, "§7Speed II"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "speed2", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.SUGAR, "§b§lSpeed Boost: 8x", spd == 3, "§7Speed III"), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "speed3", false);
                    rebuild();
                });

                idx = 14;
                GameType myGm = admin.gameMode();
                putSlot(contentSlots[idx++], icon(Items.IRON_SWORD, "§f§lGamemode: Survival", myGm == GameType.SURVIVAL), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "gms", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.GRASS_BLOCK, "§b§lGamemode: Creative", myGm == GameType.CREATIVE), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "gmc", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.MAP, "§e§lGamemode: Adventure", myGm == GameType.ADVENTURE), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "gma", false);
                    rebuild();
                });
                putSlot(contentSlots[idx++], icon(Items.ENDER_EYE, "§7§lGamemode: Spectator", myGm == GameType.SPECTATOR), (sp, b) -> {
                    TxAdminServer.applySelfAction(sp, "gmsp", false);
                    rebuild();
                });
            }
            case 1 -> {
                putSlot(contentSlots[idx++], icon(Items.ENDER_PEARL, "§6§lTP To Player (Goto)", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "tpto", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.LEAD, "§a§lBring Player Here", false, "§7Target: §e" + target, "§7Saves their old position for Return"),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "bring", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.COMPASS, "§e§lReturn Player (Send Back)", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "back", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.SPYGLASS, "§b§lSpectate Player", false, "§7Target: §e" + target), (sp, b) -> {
                    sp.closeContainer();
                    TxAdminServer.applyPlayerAction(sp, "spectate", getTarget());
                });
                putSlot(contentSlots[idx++], icon(Items.BLUE_ICE, "§b§lFreeze / Unfreeze Player", false, "§7Locks §e" + target + " §7in place"),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "freeze", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.CHEST, "§6§lInspect Inventory (InvSee)", false, "§7Open live inventory of §e" + target),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "invsee", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.ENDER_CHEST, "§d§lInspect EnderChest (EnderSee)", false, "§7Open live EnderChest of §e" + target),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "endersee", getTarget()));

                idx = 7;
                putSlot(contentSlots[idx++], icon(Items.GOLDEN_APPLE, "§a§lHeal & Feed Player", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.applyPlayerAction(sp, "heal", getTarget()));
                putSlot(contentSlots[idx++], icon(Items.SKELETON_SKULL, "§6§lCorpse Death History", false, "§7Open /deathhistory for §e" + target), (sp, b) -> {
                    sp.closeContainer();
                    TxAdminServer.runAsAdmin(sp, "deathhistory " + getTarget());
                });
                putSlot(contentSlots[idx++], icon(Items.TRAPPED_CHEST, "§e§lReset Player Lootr Chests", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "lootr clear " + getTarget()));
                putSlot(contentSlots[idx++], icon(Items.REDSTONE, "§c§lVoice Mute (15m)", false, "§7Mute proximity mic of §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vcd mute " + getTarget() + " 15m Admin_Mute"));
                putSlot(contentSlots[idx++], icon(Items.EMERALD, "§a§lVoice Unmute", false, "§7Unmute proximity mic of §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vcd unmute " + getTarget()));

                idx = 14;
                putSlot(contentSlots[idx++], icon(Items.NETHER_STAR, "§a§lGrant OP", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "op " + getTarget()));
                putSlot(contentSlots[idx++], icon(Items.COAL, "§7§lDe-OP", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "deop " + getTarget()));
                putSlot(contentSlots[idx++], icon(Items.PAPER, "§b§lWhitelist Add", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "whitelist add " + getTarget()));
                putSlot(contentSlots[idx++], icon(Items.BOOK, "§7§lWhitelist Remove", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "whitelist remove " + getTarget()));
                putSlot(contentSlots[idx++], icon(Items.IRON_BOOTS, "§e§lKick Player", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "kick " + getTarget() + " Kicked by Admin"));
                putSlot(contentSlots[idx++], icon(Items.BARRIER, "§c§lBan Player", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "ban " + getTarget() + " Banned by Admin"));
                putSlot(contentSlots[idx++], icon(Items.EMERALD, "§a§lUnban (Pardon)", false, "§7Target: §e" + target),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "pardon " + getTarget()));
            }
            case 2 -> {
                putSlot(contentSlots[idx++], icon(Items.SUNFLOWER, "§e§lTime: Sunrise (0)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set 0"));
                putSlot(contentSlots[idx++], icon(Items.CLOCK, "§6§lTime: Day (1000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set day"));
                putSlot(contentSlots[idx++], icon(Items.GLOWSTONE_DUST, "§e§lTime: Noon (6000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set noon"));
                putSlot(contentSlots[idx++], icon(Items.GLOW_BERRIES, "§6§lTime: Sunset (12000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set 12000"));
                putSlot(contentSlots[idx++], icon(Items.ENDER_PEARL, "§9§lTime: Night (13000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set night"));
                putSlot(contentSlots[idx++], icon(Items.COAL, "§8§lTime: Midnight (18000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time set midnight"));
                putSlot(contentSlots[idx++], icon(Items.BELL, "§a§lAdd +1 Day (+24000)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "time add 24000"));

                idx = 7;
                putSlot(contentSlots[idx++], icon(Items.BUCKET, "§a§lWeather: Clear Sky", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "weather clear"));
                putSlot(contentSlots[idx++], icon(Items.SUNFLOWER, "§a§lWeather: Clear (1 Hour)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "weather clear 3600s"));
                putSlot(contentSlots[idx++], icon(Items.WATER_BUCKET, "§b§lWeather: Rain", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "weather rain"));
                putSlot(contentSlots[idx++], icon(Items.BLAZE_ROD, "§e§lWeather: Thunderstorm", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "weather thunder"));

                idx = 14;
                putSlot(contentSlots[idx++], icon(Items.FEATHER, "§a§lDifficulty: Peaceful", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "difficulty peaceful"));
                putSlot(contentSlots[idx++], icon(Items.WOODEN_SWORD, "§b§lDifficulty: Easy", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "difficulty easy"));
                putSlot(contentSlots[idx++], icon(Items.IRON_SWORD, "§6§lDifficulty: Normal", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "difficulty normal"));
                putSlot(contentSlots[idx++], icon(Items.NETHERITE_SWORD, "§c§lDifficulty: Hard", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "difficulty hard"));

                idx = 21;
                putSlot(contentSlots[idx++], icon(Items.REPEATER, "§a§lTick Rate: 20 TPS (Normal)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "tick rate 20"));
                putSlot(contentSlots[idx++], icon(Items.PACKED_ICE, "§b§lFreeze World (/tick freeze)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "tick freeze"));
                putSlot(contentSlots[idx++], icon(Items.BLAZE_POWDER, "§a§lUnfreeze World (/tick unfreeze)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "tick unfreeze"));
                putSlot(contentSlots[idx++], icon(Items.SOUL_SAND, "§e§lSlow-Mo (10 TPS)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "tick rate 10"));

                idx = 28;
                putSlot(contentSlots[idx++], icon(Items.STRUCTURE_VOID, "§e§lWorld Border: 2,500m", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "worldborder set 2500"));
                putSlot(contentSlots[idx++], icon(Items.STRUCTURE_VOID, "§6§lWorld Border: 5,000m", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "worldborder set 5000"));
                putSlot(contentSlots[idx++], icon(Items.STRUCTURE_VOID, "§a§lWorld Border: 10,000m", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "worldborder set 10000"));
                putSlot(contentSlots[idx++], icon(Items.COMPASS, "§b§lCenter Border at (0, 0)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "worldborder center 0 0"));
                putSlot(contentSlots[idx++], icon(Items.BARRIER, "§7§lReset Border (60M)", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "worldborder set 59999968"));
            }
            case 3 -> {
                putSlot(contentSlots[idx++], icon(Items.CLOCK, "§6§l1-Player Sleep (1%)", true, "§7playersSleepingPercentage = 1"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule playersSleepingPercentage 1"));
                putSlot(contentSlots[idx++], icon(Items.CLOCK, "§e§l50% Players Sleep", false, "§7playersSleepingPercentage = 50"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule playersSleepingPercentage 50"));
                putSlot(contentSlots[idx++], icon(Items.CLOCK, "§7§l100% Players Sleep", false, "§7playersSleepingPercentage = 100"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule playersSleepingPercentage 100"));
                putSlot(contentSlots[idx++], icon(Items.WHEAT_SEEDS, "§a§lRandom Tick Speed: 3 (Default)", false),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule randomTickSpeed 3"));
                putSlot(contentSlots[idx++], icon(Items.WHEAT, "§6§lRandom Tick Speed: 6 (2x)", false),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule randomTickSpeed 6"));
                putSlot(contentSlots[idx++], icon(Items.HAY_BLOCK, "§e§lRandom Tick Speed: 12 (4x)", false),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule randomTickSpeed 12"));
                putSlot(contentSlots[idx++], icon(Items.DEAD_BUSH, "§c§lRandom Tick Speed: 0 (Off)", false),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "gamerule randomTickSpeed 0"));

                String[][] rules = {
                        {"Keep Inventory", "keepInventory"},
                        {"Mob Griefing", "mobGriefing"},
                        {"PvP Combat", "pvp"},
                        {"26.3 Locator Bar", "locatorBar"},
                        {"Phantom Spawning", "doInsomnia"},
                        {"Fire Spread", "doFireTick"},
                        {"Daylight Cycle", "doDaylightCycle"},
                        {"Weather Cycle", "doWeatherCycle"},
                        {"Pillager Patrols", "doPatrolSpawning"},
                        {"Wandering Traders", "doTraderSpawning"},
                        {"Warden Spawning", "doWardenSpawning"},
                        {"Natural Mob Spawning", "doMobSpawning"},
                        {"Fall Damage", "fallDamage"},
                        {"TNT Detonation", "tntExplodes"},
                        {"Announce Advancements", "announceAdvancements"},
                        {"Show Death Messages", "showDeathMessages"}
                };
                for (String[] r : rules) {
                    if (idx >= contentSlots.length) break;
                    String title = r[0];
                    String ruleId = r[1];
                    putSlot(contentSlots[idx++], icon(Items.BOOK, "§6§l" + title + " §7(" + ruleId + ")", false,
                            "§aLeft-Click: §fSet TRUE (ON)",
                            "§cRight-Click: §fSet FALSE (OFF)"), (sp, btn) -> {
                        boolean val = (btn != 1);
                        TxAdminServer.runAsAdmin(sp, "gamerule " + ruleId + " " + val);
                    });
                }
            }
            case 4 -> {
                putSlot(contentSlots[idx++], icon(Items.SPYGLASS, "§6§lVoxy Server Side: Status", false, "§7/vsslod status"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vsslod status"));
                putSlot(contentSlots[idx++], icon(Items.RECOVERY_COMPASS, "§a§lVoxy Server Side: Hot-Reload", true, "§7/vsslod reload"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vsslod reload"));
                putSlot(contentSlots[idx++], icon(Items.EMERALD_BLOCK, "§a§lVoxy: Start LOD Backfill", false, "§7/vsslod backfill start"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vsslod backfill start"));
                putSlot(contentSlots[idx++], icon(Items.REDSTONE_BLOCK, "§c§lVoxy: Stop LOD Backfill", false, "§7/vsslod backfill stop"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "vsslod backfill stop"));

                idx = 7;
                putSlot(contentSlots[idx++], icon(Items.COMPARATOR, "§6§lServerCore: Status", false, "§7/servercore status"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "servercore status"));
                putSlot(contentSlots[idx++], icon(Items.ZOMBIE_HEAD, "§b§lServerCore: Mobcaps", false, "§7/mobcaps"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "mobcaps"));
                putSlot(contentSlots[idx++], icon(Items.REPEATER, "§a§lServerCore: Hot-Reload", true, "§7/servercore reload"),
                        (sp, b) -> TxAdminServer.runAsAdmin(sp, "servercore reload"));

                idx = 14;
                putSlot(contentSlots[idx++], icon(Items.GRASS_BLOCK, "§a§lChunky: Start 5,000m Pre-Gen", false, "§7Overworld (0,0) radius 5000"), (sp, b) -> {
                    TxAdminServer.runAsAdmin(sp, "chunky world minecraft:overworld");
                    TxAdminServer.runAsAdmin(sp, "chunky center 0 0");
                    TxAdminServer.runAsAdmin(sp, "chunky radius 5000");
                    TxAdminServer.runAsAdmin(sp, "chunky start");
                });
                putSlot(contentSlots[idx++], icon(Items.GOLD_BLOCK, "§e§lChunky: Pause", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "chunky pause"));
                putSlot(contentSlots[idx++], icon(Items.EMERALD, "§a§lChunky: Continue", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "chunky continue"));
                putSlot(contentSlots[idx++], icon(Items.COMPASS, "§b§lChunky: Progress", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "chunky progress"));
                putSlot(contentSlots[idx++], icon(Items.BARRIER, "§c§lChunky: Cancel", false), (sp, b) -> TxAdminServer.runAsAdmin(sp, "chunky cancel"));

                idx = 21;
                putSlot(contentSlots[idx++], icon(Items.CLOCK, "§6§lSpark: TPS & MSPT", false, "§7/spark tps"), (sp, b) -> TxAdminServer.runAsAdmin(sp, "spark tps"));
                putSlot(contentSlots[idx++], icon(Items.GOLDEN_APPLE, "§a§lSpark: Health Report", false, "§7/spark health"), (sp, b) -> TxAdminServer.runAsAdmin(sp, "spark health"));
                putSlot(contentSlots[idx++], icon(Items.IRON_INGOT, "§b§lSpark: Memory Report", false, "§7/spark memory"), (sp, b) -> TxAdminServer.runAsAdmin(sp, "spark memory"));
                putSlot(contentSlots[idx++], icon(Items.EMERALD, "§a§lSpark: Start CPU Profiler", false, "§7/spark profiler start"), (sp, b) -> TxAdminServer.runAsAdmin(sp, "spark profiler start"));
                putSlot(contentSlots[idx++], icon(Items.REDSTONE, "§e§lSpark: Stop & Get Web URL", false, "§7/spark profiler stop"), (sp, b) -> TxAdminServer.runAsAdmin(sp, "spark profiler stop"));
            }
            case 5 -> {
                String[][] items = {
                        {"§6§lSlot Machine", "casinodeco:slot_machine"},
                        {"§6§lRoulette Table", "casinodeco:roulette_table"},
                        {"§6§lBlackjack Table", "casinodeco:blackjack_table"},
                        {"§6§lPoker Table", "casinodeco:poker_table"},
                        {"§6§lFortune Wheel", "casinodeco:fortune_wheel"},
                        {"§6§lPlinko", "casinodeco:plinko"},
                        {"§6§lDuck Derby", "casinodeco:duck_derby"},
                        {"§a§lCroupier Hiring Card", "casinodeco:croupier_hiring_card"},
                        {"§a§lChip Case", "casinodeco:chip_case"},
                        {"§e§lCasino Chip Pile", "casinodeco:casino_chip_pile"},
                        {"§e§lCash Register", "casinodeco:cash_register"},
                        {"§b§lFM Radio (Live Streams)", "music_disc_maker:fm_radio"},
                        {"§b§lBoombox", "music_disc_maker:boombox"},
                        {"§d§lWorldEdit Wand", "minecraft:wooden_axe"},
                        {"§a§lEasy NPC Wand", "easy_npc:easy_npc_wand"},
                        {"§c§lSecurityCraft Admin Tool", "securitycraft:universal_block_modifier"}
                };
                Item[] icons = {
                        Items.GOLD_BLOCK, Items.DIAMOND, Items.EMERALD, Items.DARK_OAK_SIGN,
                        Items.CLOCK, Items.AMETHYST_SHARD, Items.FEATHER, Items.NAME_TAG,
                        Items.CHEST, Items.GOLD_NUGGET, Items.IRON_BLOCK, Items.JUKEBOX,
                        Items.NOTE_BLOCK, Items.WOODEN_AXE, Items.BLAZE_ROD, Items.NETHERITE_INGOT
                };
                for (int i = 0; i < items.length; i++) {
                    String lbl = items[i][0];
                    String iid = items[i][1];
                    putSlot(contentSlots[idx++], icon(icons[i], lbl, true,
                            "§7Give 1x §f" + iid,
                            "§7To Target: §e" + target), (sp, b) -> TxAdminServer.runAsAdmin(sp, "give " + getTarget() + " " + iid + " 1"));
                }
            }
        }
        broadcastChanges();
    }

    @Override
    public void clicked(int slotId, int button, ContainerInput input, Player player) {
        if (slotId >= 0 && slotId < 54 && player instanceof ServerPlayer sp) {
            BiConsumer<ServerPlayer, Integer> act = actions.get(slotId);
            if (act != null) {
                act.accept(sp, button);
            }
            broadcastChanges();
            return;
        }
        if (slotId >= 54) {
            return;
        }
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        return ItemStack.EMPTY;
    }

    @Override
    public boolean stillValid(Player player) {
        return true;
    }
}
"""

# 7. TxAdminClient.java
FILES["com/thenest/txadmin/client/TxAdminClient.java"] = r"""package com.thenest.txadmin.client;

import com.thenest.txadmin.OpenTxAdminPayload;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.lang.reflect.Method;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.TitleScreen;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;

public final class TxAdminClient {
    private static volatile int serverStatus = 0; // 0=checking, 1=online, 2=starting, 3=offline
    private static volatile int onlinePlayers = 0;
    private static volatile int maxPlayers = 20;
    private static volatile long lastPingMs = 0L;
    private static volatile boolean pinging = false;
    private static volatile List<String> cachedTargets;
    private static volatile Method fmGetLayerMethod;
    private static volatile Method fmGetElementMethod;
    private static volatile Method fmAbsXMethod;
    private static volatile Method fmAbsYMethod;
    private static volatile Method fmAbsWMethod;
    private static volatile Method fmAbsHMethod;
    private static volatile boolean fmLookupInit = false;

    private static final Pattern PAT_ONLINE = Pattern.compile("\"online\"\\s*:\\s*(\\d+)");
    private static final Pattern PAT_MAX = Pattern.compile("\"max\"\\s*:\\s*(\\d+)");

    private TxAdminClient() {}

    public static void init() {
        OpenTxAdminPayload.setClientHandler(TxAdminClient::onOpenPayload);
        NeoForge.EVENT_BUS.addListener(EventPriority.LOWEST, TxAdminClient::onRenderTitleScreen);
    }

    private static List<String> getPingTargets() {
        if (cachedTargets != null) return cachedTargets;
        Set<String> out = new LinkedHashSet<>();
        try {
            Path fm = Paths.get("config", "fancymenu", "customization", "the_nest_title_screen.txt");
            if (Files.exists(fm)) {
                for (String line : Files.readAllLines(fm, StandardCharsets.UTF_8)) {
                    int idx = line.indexOf("[action_type:joinserver]");
                    if (idx >= 0) {
                        int eq = line.indexOf('=', idx);
                        if (eq >= 0) {
                            String addr = line.substring(eq + 1).trim();
                            if (!addr.isEmpty()) out.add(addr);
                        }
                    }
                }
            }
        } catch (Throwable ignored) {}
        out.add("46.102.16.196:25565");
        out.add("192.168.1.167:25565");
        cachedTargets = new ArrayList<>(out);
        return cachedTargets;
    }

    private static void writeVarInt(DataOutputStream out, int v) throws Exception {
        while ((v & ~0x7F) != 0) {
            out.writeByte((v & 0x7F) | 0x80);
            v >>>= 7;
        }
        out.writeByte(v);
    }

    private static int readVarInt(DataInputStream in) throws Exception {
        int numRead = 0;
        int result = 0;
        byte read;
        do {
            read = in.readByte();
            int value = (read & 0x7F);
            result |= (value << (7 * numRead));
            numRead++;
            if (numRead > 5) throw new RuntimeException("VarInt too big");
        } while ((read & 0x80) != 0);
        return result;
    }

    private static int trySlpPing(String hostPort) {
        String host = hostPort;
        int port = 25565;
        int colon = hostPort.lastIndexOf(':');
        if (colon > 0) {
            host = hostPort.substring(0, colon);
            try { port = Integer.parseInt(hostPort.substring(colon + 1)); } catch (Exception ignored) {}
        }
        boolean connected = false;
        try (Socket sock = new Socket()) {
            sock.connect(new InetSocketAddress(host, port), 1200);
            connected = true;
            sock.setSoTimeout(1500);
            DataOutputStream out = new DataOutputStream(sock.getOutputStream());
            DataInputStream in = new DataInputStream(sock.getInputStream());

            byte[] hb = host.getBytes(StandardCharsets.UTF_8);
            java.io.ByteArrayOutputStream hs = new java.io.ByteArrayOutputStream();
            DataOutputStream hsd = new DataOutputStream(hs);
            writeVarInt(hsd, 0x00);
            writeVarInt(hsd, 769);
            writeVarInt(hsd, hb.length);
            hsd.write(hb);
            hsd.writeShort(port);
            writeVarInt(hsd, 1);
            byte[] hsBytes = hs.toByteArray();

            writeVarInt(out, hsBytes.length);
            out.write(hsBytes);
            out.writeByte(0x01);
            out.writeByte(0x00);
            out.flush();

            readVarInt(in); // packet length
            int pid = readVarInt(in);
            if (pid != 0x00) return 2;
            int slen = readVarInt(in);
            if (slen <= 0 || slen > 65536) return 2;
            byte[] data = new byte[slen];
            in.readFully(data);
            String json = new String(data, StandardCharsets.UTF_8);
            Matcher mo = PAT_ONLINE.matcher(json);
            Matcher mm = PAT_MAX.matcher(json);
            if (mo.find()) onlinePlayers = Integer.parseInt(mo.group(1));
            if (mm.find()) maxPlayers = Integer.parseInt(mm.group(1));
            return 1;
        } catch (Throwable t) {
            return connected ? 2 : 3;
        }
    }

    private static void triggerPingAsync() {
        long now = System.currentTimeMillis();
        if (pinging || (now - lastPingMs) < 5000L) return;
        pinging = true;
        lastPingMs = now;
        Thread t = new Thread(() -> {
            try {
                int best = 3;
                for (String target : getPingTargets()) {
                    int res = trySlpPing(target);
                    if (res == 1) {
                        best = 1;
                        break;
                    }
                    if (res == 2) best = 2;
                }
                serverStatus = best;
            } finally {
                lastPingMs = System.currentTimeMillis();
                pinging = false;
            }
        }, "Nest-Server-Ping");
        t.setDaemon(true);
        t.start();
    }

    private static int[] findJoinButtonBounds(TitleScreen screen) {
        // 1. Exact lookup via FancyMenu ScreenCustomizationLayer (nest-title-join-button-0001)
        try {
            if (!fmLookupInit) {
                fmLookupInit = true;
                Class<?> handlerCls = Class.forName("de.keksuccino.fancymenu.customization.layer.ScreenCustomizationLayerHandler");
                fmGetLayerMethod = handlerCls.getMethod("getLayerOfScreen", Screen.class);
                Class<?> layerCls = Class.forName("de.keksuccino.fancymenu.customization.layer.ScreenCustomizationLayer");
                fmGetElementMethod = layerCls.getMethod("getElementByInstanceIdentifier", String.class);
                Class<?> elemCls = Class.forName("de.keksuccino.fancymenu.customization.element.AbstractElement");
                fmAbsXMethod = elemCls.getMethod("getAbsoluteX");
                fmAbsYMethod = elemCls.getMethod("getAbsoluteY");
                fmAbsWMethod = elemCls.getMethod("getAbsoluteWidth");
                fmAbsHMethod = elemCls.getMethod("getAbsoluteHeight");
            }
            if (fmGetLayerMethod != null && fmGetElementMethod != null) {
                Object layer = fmGetLayerMethod.invoke(null, screen);
                if (layer != null) {
                    Object elem = fmGetElementMethod.invoke(layer, "nest-title-join-button-0001");
                    if (elem != null) {
                        int x = ((Number) fmAbsXMethod.invoke(elem)).intValue();
                        int y = ((Number) fmAbsYMethod.invoke(elem)).intValue();
                        int w = ((Number) fmAbsWMethod.invoke(elem)).intValue();
                        int h = ((Number) fmAbsHMethod.invoke(elem)).intValue();
                        if (w > 20 && h > 10) return new int[]{x, y, w, h};
                    }
                }
            }
        } catch (Throwable ignored) {}

        // 2. Fallback scan across Screen widgets
        AbstractWidget bestWide = null;
        for (var r : screen.renderables) {
            if (r instanceof AbstractWidget w && w.visible) {
                if (w.getMessage().getString().contains("Join The Nest")) {
                    return new int[]{w.getX(), w.getY(), w.getWidth(), w.getHeight()};
                }
                if (w.getWidth() >= 180 && w.getHeight() >= 18 && w.getHeight() <= 30) {
                    if (bestWide == null || w.getY() < bestWide.getY()) bestWide = w;
                }
            }
        }
        if (bestWide != null) {
            return new int[]{bestWide.getX(), bestWide.getY(), bestWide.getWidth(), bestWide.getHeight()};
        }
        // 3. Layout-matched fallback matching the_nest_title_screen.txt (mid-centered x=0, y=21, w=200, h=22)
        return new int[]{screen.width / 2 - 100, screen.height / 2 + 21 - 11, 200, 22};
    }

    private static void fillCircle(GuiGraphicsExtractor g, int cx, int cy, int r, int argb) {
        double rSq = (double) r * r - (r >= 4 ? 0.8 : 0.15);
        for (int dy = -r; dy <= r; dy++) {
            double rem = rSq - (double) dy * dy;
            if (rem < 0.0) continue;
            int span = (int) Math.floor(Math.sqrt(rem));
            g.fill(cx - span, cy + dy, cx + span + 1, cy + dy + 1, argb);
        }
    }

    private static void onRenderTitleScreen(ScreenEvent.Render.Post event) {
        if (!(event.getScreen() instanceof TitleScreen screen)) return;
        triggerPingAsync();
        Minecraft mc = Minecraft.getInstance();
        int[] bounds = findJoinButtonBounds(screen);
        int jx = bounds[0], jy = bounds[1], jw = bounds[2], jh = bounds[3];

        // Position a clean small circle at the far right side inside the "Join The Nest" button
        int cx = jx + jw - 13;
        int cy = jy + jh / 2;

        int st = serverStatus;
        GuiGraphicsExtractor g = event.getGuiGraphics();

        if (st == 1) {
            // Online: smooth breathing green pulse + bright emerald core circle
            double phase = (Math.sin(System.currentTimeMillis() / 220.0) + 1.0) * 0.5;
            int pulseR = 4 + (int) Math.round(phase * 3.0);
            int pulseAlpha = (int) Math.round(95 - phase * 65);
            fillCircle(g, cx, cy, pulseR, (pulseAlpha << 24) | 0x3CE878);
            fillCircle(g, cx, cy, 4, 0xFF176632);
            fillCircle(g, cx, cy, 3, 0xFF4ADE80);
        } else if (st == 2) {
            // Starting: gentle amber pulse
            double phase = (Math.sin(System.currentTimeMillis() / 260.0) + 1.0) * 0.5;
            int pulseAlpha = (int) Math.round(45 + phase * 55);
            fillCircle(g, cx, cy, 5, (pulseAlpha << 24) | 0xE09F3E);
            fillCircle(g, cx, cy, 4, 0xFF7A4D10);
            fillCircle(g, cx, cy, 3, 0xFFE09F3E);
        } else {
            // Offline (or initial check <1s): clean small red circle (no pulse)
            int rim = st == 0 ? 0xFF4A423A : 0xFF7D1F1F;
            int core = st == 0 ? 0xFF9C8B7A : 0xFFE84848;
            fillCircle(g, cx, cy, 4, rim);
            fillCircle(g, cx, cy, 3, core);
        }

        // Optional clean hover label if cursor rests over the dot
        int mx = event.getMouseX();
        int my = event.getMouseY();
        if (Math.abs(mx - cx) <= 7 && Math.abs(my - cy) <= 7) {
            String tip = switch (st) {
                case 1 -> "Online (" + onlinePlayers + "/" + maxPlayers + ")";
                case 2 -> "Server Starting...";
                case 3 -> "Server Offline";
                default -> "Checking Server...";
            };
            int tw = mc.font.width(tip) + 10;
            int tx = Math.min(screen.width - tw - 4, cx + 8);
            int ty = Math.max(4, cy - 16);
            g.fill(tx, ty, tx + tw, ty + 14, 0xE816110D);
            g.text(mc.font, tip, tx + 5, ty + 3, 0xFFF5ECE0, false);
        }
    }

    private static void onOpenPayload(OpenTxAdminPayload payload) {
        Minecraft mc = Minecraft.getInstance();
        String csv = payload.playersCsv() != null ? payload.playersCsv() : "";
        boolean forceOpen = csv.startsWith("OPEN:");
        if (csv.startsWith("OPEN:") || csv.startsWith("SYNC:")) {
            csv = csv.substring(5);
        }
        TxAdminScreen active = TxAdminScreen.getActive();
        if (!forceOpen && active != null) {
            active.applySync(payload, csv);
        } else if (forceOpen) {
            mc.setScreenAndShow(new TxAdminScreen(payload, csv));
        }
    }
}
"""

# 7b. SkinClientManager.java
FILES["com/thenest/txadmin/client/SkinClientManager.java"] = r"""package com.thenest.txadmin.client;

import com.google.common.cache.LoadingCache;
import com.mojang.authlib.GameProfile;
import com.mojang.blaze3d.platform.NativeImage;
import com.thenest.txadmin.BroadcastSkinPayload;
import com.thenest.txadmin.NestTxAdminMod;
import com.thenest.txadmin.SkinServerManager;
import com.thenest.txadmin.UploadSkinPayload;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.function.Supplier;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.font.FontManager;
import net.minecraft.client.gui.font.PlayerGlyphProvider;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.renderer.PlayerSkinRenderCache;
import net.minecraft.client.renderer.texture.DynamicTexture;
import net.minecraft.client.renderer.texture.SkinTextureDownloader;
import net.minecraft.client.resources.SkinManager;
import net.minecraft.core.ClientAsset;
import net.minecraft.resources.Identifier;
import net.minecraft.world.entity.player.PlayerModelType;
import net.minecraft.world.entity.player.PlayerSkin;
import net.minecraft.world.item.component.ResolvableProfile;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.network.ClientPacketDistributor;
import net.neoforged.neoforge.common.NeoForge;

public final class SkinClientManager {
    public record LocalPreset(String name, String file, boolean slim) {}
    private record ClientSkinEntry(UUID playerUuid, String playerName, Identifier texId, boolean slim, byte[] pngBytes) {}

    private static final Map<String, ClientSkinEntry> CLIENT_SKINS = new ConcurrentHashMap<>();
    private static final Set<String> MOJANG_FETCH_ATTEMPTED = ConcurrentHashMap.newKeySet();
    private static final ExecutorService CLIENT_SKIN_POOL = Executors.newCachedThreadPool(r -> {
        Thread t = new Thread(r, "Nest-ClientSkinWorker");
        t.setDaemon(true);
        return t;
    });

    private static final Pattern MODE_PAT = Pattern.compile("\"mode\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern SLIM_PAT = Pattern.compile("\"slim\"\\s*:\\s*(true|false)");
    private static final Pattern B64_PAT = Pattern.compile("\"png_base64\"\\s*:\\s*\"([A-Za-z0-9+/=\\r\\n]*)\"");
    private static final Pattern PRESET_OBJ_PAT = Pattern.compile("\\{[^{}]*\\}");
    private static final Pattern NAME_PAT = Pattern.compile("\"name\"\\s*:\\s*\"([^\"]+)\"");
    private static final Pattern FILE_PAT = Pattern.compile("\"file\"\\s*:\\s*\"([^\"]+)\"");

    private static Field skinLookupField;
    private static Field onlineModeField;
    private static Field skinCacheField;
    private static Constructor<?> skinCacheKeyCtor;
    private static Field renderInfoCacheField;
    private static Field defaultSkinCacheField;
    private static Field fontManagerField;
    private static Field playerProviderField;
    private static Field anyGlyphsField;
    private static Field nonFishyGlyphsField;
    private static Field glyphWrapperCacheField;
    private static Method cachedFontInvalidateMethod;
    private static Method processLegacySkinMethod;
    private static Method chatHeadsExtractBlendedMethod;
    private static Method chatHeadsBlendedLocMethod;
    private static Set<Identifier> chatHeadsBlendedSet;

    private static int tickCount = 0;
    private static int skinSeq = 0;
    private static int lastConnectionHash = 0;
    private static long lastConfigMtime = -2L;

    static {
        try {
            for (Field f : PlayerInfo.class.getDeclaredFields()) {
                if (f.getType() == Supplier.class) {
                    f.setAccessible(true);
                    skinLookupField = f;
                    break;
                }
            }
        } catch (Throwable ignored) {}

        try {
            onlineModeField = ClientPacketListener.class.getDeclaredField("onlineMode");
            onlineModeField.setAccessible(true);
        } catch (Throwable ignored) {}

        try {
            skinCacheField = SkinManager.class.getDeclaredField("skinCache");
            skinCacheField.setAccessible(true);
            Class<?> keyCls = Class.forName("net.minecraft.client.resources.SkinManager$CacheKey");
            skinCacheKeyCtor = keyCls.getDeclaredConstructors()[0];
            skinCacheKeyCtor.setAccessible(true);
        } catch (Throwable ignored) {}

        try {
            renderInfoCacheField = PlayerSkinRenderCache.class.getDeclaredField("renderInfoCache");
            renderInfoCacheField.setAccessible(true);
            defaultSkinCacheField = PlayerSkinRenderCache.class.getDeclaredField("defaultSkinCache");
            defaultSkinCacheField.setAccessible(true);
        } catch (Throwable ignored) {}

        try {
            fontManagerField = Minecraft.class.getDeclaredField("fontManager");
            fontManagerField.setAccessible(true);
            playerProviderField = FontManager.class.getDeclaredField("playerProvider");
            playerProviderField.setAccessible(true);
            anyGlyphsField = FontManager.class.getDeclaredField("anyGlyphs");
            anyGlyphsField.setAccessible(true);
            nonFishyGlyphsField = FontManager.class.getDeclaredField("nonFishyGlyphs");
            nonFishyGlyphsField.setAccessible(true);
            glyphWrapperCacheField = PlayerGlyphProvider.class.getDeclaredField("wrapperCache");
            glyphWrapperCacheField.setAccessible(true);
            Class<?> cfpCls = Class.forName("net.minecraft.client.gui.font.FontManager$CachedFontProvider");
            cachedFontInvalidateMethod = cfpCls.getDeclaredMethod("invalidate");
            cachedFontInvalidateMethod.setAccessible(true);
        } catch (Throwable ignored) {}

        try {
            Method m = SkinTextureDownloader.class.getDeclaredMethod("processLegacySkin", NativeImage.class, String.class);
            m.setAccessible(true);
            processLegacySkinMethod = m;
        } catch (Throwable ignored) {}

        try {
            Class<?> chCls = Class.forName("dzwdz.chat_heads.ChatHeads");
            chatHeadsExtractBlendedMethod = chCls.getDeclaredMethod("extractBlendedHead", NativeImage.class);
            chatHeadsBlendedLocMethod = chCls.getDeclaredMethod("getBlendedHeadLocation", Identifier.class);
            @SuppressWarnings("unchecked")
            Set<Identifier> set = (Set<Identifier>) chCls.getDeclaredField("blendedHeadTextures").get(null);
            chatHeadsBlendedSet = set;
        } catch (Throwable ignored) {}
    }

    private SkinClientManager() {}

    public static void init() {
        BroadcastSkinPayload.setClientHandler(SkinClientManager::onReceiveSkin);
        NeoForge.EVENT_BUS.addListener(SkinClientManager::onClientTick);
    }

    private static Path getPresetsDir() {
        String localAppData = System.getenv("LOCALAPPDATA");
        if (localAppData == null || localAppData.isBlank()) {
            localAppData = System.getProperty("user.home", ".");
        }
        Path dir = Paths.get(localAppData, "TheNestVanilla", "skin_presets");
        try {
            Files.createDirectories(dir);
        } catch (Exception ignored) {}
        return dir;
    }

    public static List<LocalPreset> loadLocalPresets() {
        List<LocalPreset> out = new ArrayList<>();
        try {
            Path idx = getPresetsDir().resolve("presets.json");
            if (!Files.exists(idx)) return out;
            String raw = Files.readString(idx, StandardCharsets.UTF_8);
            Matcher mObj = PRESET_OBJ_PAT.matcher(raw);
            while (mObj.find()) {
                String block = mObj.group(0);
                Matcher mName = NAME_PAT.matcher(block);
                Matcher mFile = FILE_PAT.matcher(block);
                Matcher mSlim = SLIM_PAT.matcher(block);
                if (mName.find() && mFile.find()) {
                    boolean slim = mSlim.find() && Boolean.parseBoolean(mSlim.group(1));
                    out.add(new LocalPreset(mName.group(1), mFile.group(1), slim));
                }
            }
        } catch (Exception ignored) {}
        return out;
    }

    public static boolean equipPreset(LocalPreset preset, String targetPlayer) {
        if (preset == null) return false;
        try {
            Path pngFile = getPresetsDir().resolve(preset.file());
            if (!Files.exists(pngFile)) return false;
            byte[] bytes = Files.readAllBytes(pngFile);
            if (bytes.length < 64 || bytes.length > 65536) return false;

            Minecraft mc = Minecraft.getInstance();
            String myName = mc.player != null ? mc.player.getGameProfile().name() : "";
            boolean isSelf = targetPlayer == null || targetPlayer.isBlank() || targetPlayer.equalsIgnoreCase(myName) || "@s".equalsIgnoreCase(targetPlayer);

            if (isSelf && mc.player != null) {
                onReceiveSkin(new BroadcastSkinPayload(mc.player.getUUID(), myName, preset.slim(), bytes));
                try {
                    Path cfg = getClientConfigFile(mc);
                    Files.createDirectories(cfg.getParent());
                    String b64 = Base64.getEncoder().encodeToString(bytes);
                    String json = "{\n  \"mode\": \"custom\",\n  \"slim\": " + preset.slim() + ",\n  \"preset_name\": \"" + preset.name().replace("\"", "") + "\",\n  \"png_base64\": \"" + b64 + "\"\n}\n";
                    Files.writeString(cfg, json, StandardCharsets.UTF_8);
                    lastConfigMtime = Files.getLastModifiedTime(cfg).toMillis();
                } catch (Exception ignored) {}
            }
            ClientPacketDistributor.sendToServer(new UploadSkinPayload(isSelf ? "" : targetPlayer, "custom", preset.slim(), bytes));
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    public static boolean saveSkinAsPreset(String targetPlayerName, String presetName) {
        if (presetName == null || presetName.isBlank()) presetName = "Saved Skin";
        Minecraft mc = Minecraft.getInstance();
        String lookup = (targetPlayerName == null || targetPlayerName.isBlank() || "@s".equalsIgnoreCase(targetPlayerName) || "@a".equalsIgnoreCase(targetPlayerName))
                ? (mc.player != null ? mc.player.getGameProfile().name() : "")
                : targetPlayerName;
        ClientSkinEntry entry = CLIENT_SKINS.get(lookup.toLowerCase(Locale.ROOT));
        if (entry == null || entry.pngBytes() == null || entry.pngBytes().length < 64) {
            return false;
        }
        try {
            Path dir = getPresetsDir();
            String safeFn = presetName.trim().replaceAll("[^A-Za-z0-9_.-]+", "_") + "_" + (System.currentTimeMillis() % 100000) + ".png";
            Files.write(dir.resolve(safeFn), entry.pngBytes());

            List<LocalPreset> list = loadLocalPresets();
            String cleanName = presetName.trim().replace("\"", "");
            list.removeIf(p -> p.name().equalsIgnoreCase(cleanName));
            list.add(new LocalPreset(cleanName, safeFn, entry.slim()));

            StringBuilder sb = new StringBuilder("{\n  \"presets\": [\n");
            for (int i = 0; i < list.size(); i++) {
                LocalPreset p = list.get(i);
                sb.append("    {\"name\": \"").append(p.name()).append("\", \"file\": \"").append(p.file()).append("\", \"slim\": ").append(p.slim()).append("}");
                if (i + 1 < list.size()) sb.append(",");
                sb.append("\n");
            }
            sb.append("  ]\n}\n");
            Files.writeString(dir.resolve("presets.json"), sb.toString(), StandardCharsets.UTF_8);
            return true;
        } catch (Exception e) {
            return false;
        }
    }

    public static boolean isPlayerSlim(String playerName) {
        if (playerName == null) return false;
        ClientSkinEntry e = CLIENT_SKINS.get(playerName.toLowerCase(Locale.ROOT));
        return e != null && e.slim();
    }

    private static Path getClientConfigFile(Minecraft mc) {
        return mc.gameDirectory.toPath().resolve("config").resolve("nest_skin_client.json");
    }

    private static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player == null || mc.getConnection() == null) {
            if (lastConnectionHash != 0) {
                lastConnectionHash = 0;
                lastConfigMtime = -2L;
                MOJANG_FETCH_ATTEMPTED.clear();
            }
            return;
        }

        tickCount++;
        int connHash = System.identityHashCode(mc.getConnection());
        boolean isNewConn = (connHash != lastConnectionHash);

        if (isNewConn || tickCount % 30 == 0) {
            Path cfg = getClientConfigFile(mc);
            long mtime = -1L;
            try {
                if (Files.exists(cfg)) {
                    mtime = Files.getLastModifiedTime(cfg).toMillis();
                }
            } catch (Exception ignored) {}

            if (isNewConn || mtime != lastConfigMtime) {
                lastConnectionHash = connHash;
                lastConfigMtime = mtime;
                uploadAndApplyLocalSkinConfig(mc, cfg);
            }
        }

        if (tickCount % 15 == 0) {
            applySkinsToOnlinePlayers(mc);
            checkFallbackMojangSkins(mc);
        }
    }

    private static void uploadAndApplyLocalSkinConfig(Minecraft mc, Path cfg) {
        if (mc.player == null) return;
        String myName = mc.player.getGameProfile().name();
        UUID myUuid = mc.player.getUUID();
        try {
            if (Files.exists(cfg)) {
                String raw = Files.readString(cfg, StandardCharsets.UTF_8);
                String mode = "custom";
                boolean slim = false;
                byte[] pngBytes = new byte[0];

                Matcher mMode = MODE_PAT.matcher(raw);
                if (mMode.find()) mode = mMode.group(1).trim();

                Matcher mSlim = SLIM_PAT.matcher(raw);
                if (mSlim.find()) slim = Boolean.parseBoolean(mSlim.group(1));

                Matcher mB64 = B64_PAT.matcher(raw);
                if (mB64.find()) {
                    String b64 = mB64.group(1).replaceAll("\\s+", "");
                    if (!b64.isEmpty()) {
                        pngBytes = Base64.getDecoder().decode(b64);
                    }
                }

                if ("custom".equalsIgnoreCase(mode) && pngBytes.length > 64 && pngBytes.length <= 65536) {
                    onReceiveSkin(new BroadcastSkinPayload(myUuid, myName, slim, pngBytes));
                    try {
                        ClientPacketDistributor.sendToServer(new UploadSkinPayload("", "custom", slim, pngBytes));
                    } catch (Throwable ignored) {}
                    return;
                } else if ("mojang".equalsIgnoreCase(mode)) {
                    MOJANG_FETCH_ATTEMPTED.remove(myName.toLowerCase(Locale.ROOT));
                    try {
                        ClientPacketDistributor.sendToServer(new UploadSkinPayload("", "mojang", slim, new byte[0]));
                    } catch (Throwable ignored) {}
                }
            }
        } catch (Exception ignored) {}
    }

    private static void checkFallbackMojangSkins(Minecraft mc) {
        if (mc.getConnection() == null) return;
        for (PlayerInfo info : mc.getConnection().getOnlinePlayers()) {
            String name = info.getProfile().name();
            if (name == null || name.isBlank()) continue;
            String key = name.toLowerCase(Locale.ROOT);
            if (!CLIENT_SKINS.containsKey(key) && MOJANG_FETCH_ATTEMPTED.add(key)) {
                UUID id = info.getProfile().id();
                CLIENT_SKIN_POOL.submit(() -> {
                    SkinServerManager.SkinRecord fetched = SkinServerManager.downloadMojangSkin(id, name, name);
                    if (fetched != null) {
                        mc.execute(() -> {
                            if (!CLIENT_SKINS.containsKey(key)) {
                                onReceiveSkin(new BroadcastSkinPayload(fetched.playerUuid(), fetched.playerName(), fetched.slim(), fetched.pngBytes()));
                            }
                        });
                    }
                });
            }
        }
    }

    public static void onReceiveSkin(BroadcastSkinPayload payload) {
        if (payload.pngBytes() == null || payload.pngBytes().length < 64) return;
        Minecraft mc = Minecraft.getInstance();
        try {
            NativeImage raw = NativeImage.read(payload.pngBytes());
            NativeImage img = ensure64x64(raw);
            if (img == null) return;

            String safeName = payload.playerName().toLowerCase(Locale.ROOT).replaceAll("[^a-z0-9_.-]", "_");
            Identifier texId = Identifier.fromNamespaceAndPath(NestTxAdminMod.MODID, "skins/" + safeName + "_" + (++skinSeq));
            DynamicTexture dyn = new DynamicTexture(() -> "nest_skin_" + safeName, img);
            mc.getTextureManager().register(texId, dyn);

            // Also register blended 8x8 head texture for Chat Heads (when 3D-ness is off / 2D head mode)
            if (chatHeadsExtractBlendedMethod != null && chatHeadsBlendedLocMethod != null && chatHeadsBlendedSet != null) {
                try {
                    NativeImage headImg = (NativeImage) chatHeadsExtractBlendedMethod.invoke(null, img);
                    Identifier headLoc = (Identifier) chatHeadsBlendedLocMethod.invoke(null, texId);
                    if (headImg != null && headLoc != null) {
                        mc.getTextureManager().register(headLoc, new DynamicTexture(() -> "nest_head_" + safeName, headImg));
                        chatHeadsBlendedSet.add(texId);
                    }
                } catch (Throwable ignored) {}
            }

            ClientSkinEntry entry = new ClientSkinEntry(payload.playerUuid(), payload.playerName(), texId, payload.slim(), payload.pngBytes());
            CLIENT_SKINS.put(payload.playerName().toLowerCase(Locale.ROOT), entry);
            applySkinsToOnlinePlayers(mc);
            TxAdminScreen active = TxAdminScreen.getActive();
            if (active != null) {
                active.onCharProfilesUpdated();
            }
        } catch (Throwable ignored) {}
    }

    private static NativeImage ensure64x64(NativeImage src) {
        if (src == null) return null;
        if (processLegacySkinMethod != null && src.getWidth() == 64 && (src.getHeight() == 64 || src.getHeight() == 32)) {
            try {
                NativeImage res = (NativeImage) processLegacySkinMethod.invoke(null, src, "nest_custom_skin");
                if (res != null) return res;
            } catch (Throwable ignored) {}
        }
        if (src.getWidth() == 64 && src.getHeight() == 64) {
            return src;
        }
        if (src.getWidth() == 64 && src.getHeight() == 32) {
            NativeImage dst = new NativeImage(64, 64, true);
            dst.copyFrom(src);
            src.close();
            return dst;
        }
        return src;
    }

    private static void forceEnableTabHeads(Minecraft mc) {
        if (mc.getConnection() == null || onlineModeField == null) return;
        try {
            if (!mc.getConnection().onlineMode()) {
                onlineModeField.setBoolean(mc.getConnection(), true);
            }
        } catch (Throwable ignored) {}
    }

    @SuppressWarnings("unchecked")
    private static void updateGlobalSkinCaches(Minecraft mc, GameProfile profile, PlayerSkin customSkin) {
        if (profile == null || customSkin == null) return;
        UUID pid = profile.id();
        String pname = profile.name();

        // 1. Update Vanilla SkinManager.skinCache so SkinManager.get(profile) returns customSkin
        if (skinCacheField != null && skinCacheKeyCtor != null) {
            try {
                LoadingCache<Object, CompletableFuture<Optional<PlayerSkin>>> skinCache =
                        (LoadingCache<Object, CompletableFuture<Optional<PlayerSkin>>>) skinCacheField.get(mc.getSkinManager());
                if (skinCache != null) {
                    CompletableFuture<Optional<PlayerSkin>> done = CompletableFuture.completedFuture(Optional.of(customSkin));
                    Object keyNull = skinCacheKeyCtor.newInstance(pid, null);
                    skinCache.put(keyNull, done);
                    Object packed = mc.services().sessionService().getPackedTextures(profile);
                    if (packed != null) {
                        skinCache.put(skinCacheKeyCtor.newInstance(pid, packed), done);
                    }
                    for (Object existingKey : skinCache.asMap().keySet()) {
                        try {
                            UUID eid = (UUID) existingKey.getClass().getMethod("profileId").invoke(existingKey);
                            if (pid.equals(eid)) {
                                skinCache.put(existingKey, done);
                            }
                        } catch (Throwable ignored) {}
                    }
                }
            } catch (Throwable ignored) {}
        }

        // 2. Update PlayerSkinRenderCache (used by PlayerGlyphProvider / Chat Heads & Skulls)
        if (renderInfoCacheField != null && defaultSkinCacheField != null) {
            try {
                PlayerSkinRenderCache rc = mc.playerSkinRenderCache();
                if (rc != null) {
                    LoadingCache<ResolvableProfile, CompletableFuture<Optional<PlayerSkinRenderCache.RenderInfo>>> renderCache =
                            (LoadingCache<ResolvableProfile, CompletableFuture<Optional<PlayerSkinRenderCache.RenderInfo>>>) renderInfoCacheField.get(rc);
                    LoadingCache<ResolvableProfile, PlayerSkinRenderCache.RenderInfo> defaultCache =
                            (LoadingCache<ResolvableProfile, PlayerSkinRenderCache.RenderInfo>) defaultSkinCacheField.get(rc);

                    PlayerSkinRenderCache.RenderInfo ri = rc.new RenderInfo(profile, customSkin, PlayerSkin.Patch.EMPTY);
                    CompletableFuture<Optional<PlayerSkinRenderCache.RenderInfo>> fut = CompletableFuture.completedFuture(Optional.of(ri));

                    List<ResolvableProfile> keysToUpdate = new ArrayList<>();
                    keysToUpdate.add(ResolvableProfile.createResolved(profile));
                    keysToUpdate.add(ResolvableProfile.createUnresolved(pid));
                    if (pname != null && !pname.isBlank()) {
                        keysToUpdate.add(ResolvableProfile.createUnresolved(pname));
                    }

                    if (renderCache != null) {
                        for (ResolvableProfile k : new ArrayList<>(renderCache.asMap().keySet())) {
                            if (matchesProfile(k.partialProfile(), pid, pname)) {
                                keysToUpdate.add(k);
                            }
                        }
                        for (ResolvableProfile k : keysToUpdate) {
                            renderCache.put(k, fut);
                        }
                    }
                    if (defaultCache != null) {
                        for (ResolvableProfile k : new ArrayList<>(defaultCache.asMap().keySet())) {
                            if (matchesProfile(k.partialProfile(), pid, pname)) {
                                keysToUpdate.add(k);
                            }
                        }
                        for (ResolvableProfile k : keysToUpdate) {
                            defaultCache.put(k, ri);
                        }
                    }
                }
            } catch (Throwable ignored) {}
        }

        // 3. Invalidate PlayerGlyphProvider & FontManager caches so existing & new chat lines immediately show the new head!
        if (fontManagerField != null && playerProviderField != null && glyphWrapperCacheField != null) {
            try {
                FontManager fm = (FontManager) fontManagerField.get(mc);
                if (fm != null) {
                    PlayerGlyphProvider pgp = (PlayerGlyphProvider) playerProviderField.get(fm);
                    if (pgp != null) {
                        LoadingCache<?, ?> wc = (LoadingCache<?, ?>) glyphWrapperCacheField.get(pgp);
                        if (wc != null) {
                            wc.invalidateAll();
                        }
                    }
                    if (cachedFontInvalidateMethod != null) {
                        if (anyGlyphsField != null) {
                            Object cfp = anyGlyphsField.get(fm);
                            if (cfp != null) cachedFontInvalidateMethod.invoke(cfp);
                        }
                        if (nonFishyGlyphsField != null) {
                            Object cfp = nonFishyGlyphsField.get(fm);
                            if (cfp != null) cachedFontInvalidateMethod.invoke(cfp);
                        }
                    }
                }
            } catch (Throwable ignored) {}
        }
    }

    private static boolean matchesProfile(GameProfile gp, UUID id, String name) {
        if (gp == null) return false;
        if (id != null && id.equals(gp.id())) return true;
        return name != null && gp.name() != null && name.equalsIgnoreCase(gp.name());
    }

    private static void applySkinsToOnlinePlayers(Minecraft mc) {
        if (mc.getConnection() == null) return;
        forceEnableTabHeads(mc);
        if (skinLookupField == null || CLIENT_SKINS.isEmpty()) return;

        for (PlayerInfo info : mc.getConnection().getOnlinePlayers()) {
            String name = info.getProfile().name();
            if (name == null) continue;
            ClientSkinEntry entry = CLIENT_SKINS.get(name.toLowerCase(Locale.ROOT));
            if (entry == null) continue;

            try {
                PlayerSkin cur = info.getSkin();
                PlayerModelType wantModel = entry.slim() ? PlayerModelType.SLIM : PlayerModelType.WIDE;
                if (cur != null
                        && cur.body() != null
                        && entry.texId().equals(cur.body().texturePath())
                        && cur.model() == wantModel) {
                    continue;
                }
                ClientAsset.ResourceTexture bodyAsset = new ClientAsset.ResourceTexture(entry.texId(), entry.texId());
                PlayerSkin customSkin = new PlayerSkin(
                        bodyAsset,
                        cur != null ? cur.cape() : null,
                        cur != null ? cur.elytra() : null,
                        wantModel,
                        true
                );
                Supplier<PlayerSkin> sup = () -> customSkin;
                skinLookupField.set(info, sup);
                updateGlobalSkinCaches(mc, info.getProfile(), customSkin);
            } catch (Throwable ignored) {}
        }
    }
}
"""

# 7c. CharCustomClientManager.java
FILES["com/thenest/txadmin/client/CharCustomClientManager.java"] = r"""package com.thenest.txadmin.client;

import com.thenest.txadmin.CharCustomServerManager.CharProfile;
import com.thenest.txadmin.SyncCharProfilesPayload;
import java.lang.reflect.Field;
import java.lang.reflect.Modifier;
import java.util.Collections;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.client.renderer.entity.state.EntityRenderState;
import net.minecraft.util.TriState;
import net.minecraft.world.entity.player.Player;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RenderNameTagEvent;
import net.neoforged.neoforge.common.NeoForge;

public final class CharCustomClientManager {
    private static final Map<String, CharProfile> CLIENT_PROFILES = new ConcurrentHashMap<>();
    private static final Set<EntityRenderState> FADED_STATES = Collections.synchronizedSet(Collections.newSetFromMap(new WeakHashMap<>()));
    private static Field listedPlayersField;
    private static int tickCounter = 0;

    static {
        try {
            for (Field f : ClientPacketListener.class.getDeclaredFields()) {
                if (f.getType() == Set.class && Modifier.isFinal(f.getModifiers())) {
                    f.setAccessible(true);
                    listedPlayersField = f;
                    break;
                }
            }
        } catch (Throwable ignored) {}
    }

    private CharCustomClientManager() {}

    public static void init() {
        SyncCharProfilesPayload.setClientHandler(CharCustomClientManager::onSyncProfiles);
        NeoForge.EVENT_BUS.addListener(CharCustomClientManager::onCanRenderNameTag);
        NeoForge.EVENT_BUS.addListener(CharCustomClientManager::onDoRenderNameTag);
        NeoForge.EVENT_BUS.addListener(CharCustomClientManager::onClientTick);
    }

    public static CharProfile getProfile(String playerName) {
        if (playerName == null) return null;
        return CLIENT_PROFILES.get(playerName.toLowerCase(Locale.ROOT));
    }

    private static void onSyncProfiles(SyncCharProfilesPayload payload) {
        String raw = payload.profilesData();
        if (raw == null) return;
        for (String line : raw.split("\n")) {
            if (line.isBlank()) continue;
            String[] parts = line.split("\\|", -1);
            if (parts.length >= 8) {
                CharProfile prof = new CharProfile(
                        parts[0],
                        parts[1],
                        parts[2].isEmpty() ? "f" : parts[2],
                        "1".equals(parts[3]),
                        parseInt(parts[4], 0),
                        "1".equals(parts[5]),
                        parts[6],
                        parts[7].isEmpty() ? "6" : parts[7]
                );
                CLIENT_PROFILES.put(prof.realName().toLowerCase(Locale.ROOT), prof);
            }
        }
        applyTabListCustomizations(Minecraft.getInstance());
        TxAdminScreen active = TxAdminScreen.getActive();
        if (active != null) {
            active.onCharProfilesUpdated();
        }
    }

    private static int parseInt(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static void onCanRenderNameTag(RenderNameTagEvent.CanRender event) {
        if (!(event.getEntity() instanceof Player p)) return;
        String name = p.getGameProfile().name();
        if (name == null) return;
        CharProfile prof = CLIENT_PROFILES.get(name.toLowerCase(Locale.ROOT));
        if (prof == null) return;

        if (prof.opacityMode() == 2) {
            event.setCanRender(TriState.FALSE);
            FADED_STATES.remove(event.getEntityRenderState());
            return;
        }
        if (prof.opacityMode() == 1) {
            FADED_STATES.add(event.getEntityRenderState());
        } else {
            FADED_STATES.remove(event.getEntityRenderState());
        }
        event.setContent(prof.buildFormattedComponent());
    }

    private static void onDoRenderNameTag(RenderNameTagEvent.DoRender event) {
        EntityRenderState state = event.getEntityRenderState();
        if (state != null && FADED_STATES.contains(state)) {
            state.isDiscrete = true;
        }
    }

    private static void onClientTick(ClientTickEvent.Post event) {
        tickCounter++;
        if (tickCounter % 15 == 0) {
            applyTabListCustomizations(Minecraft.getInstance());
        }
    }

    @SuppressWarnings("unchecked")
    private static void applyTabListCustomizations(Minecraft mc) {
        if (mc.getConnection() == null || CLIENT_PROFILES.isEmpty()) return;
        Set<PlayerInfo> listedSet = null;
        if (listedPlayersField != null) {
            try {
                listedSet = (Set<PlayerInfo>) listedPlayersField.get(mc.getConnection());
            } catch (Throwable ignored) {}
        }

        for (PlayerInfo info : mc.getConnection().getOnlinePlayers()) {
            String name = info.getProfile().name();
            if (name == null) continue;
            CharProfile prof = CLIENT_PROFILES.get(name.toLowerCase(Locale.ROOT));
            if (prof == null) continue;

            info.setTabListDisplayName(prof.buildFormattedComponent());
            if (listedSet != null) {
                if (prof.tabHidden()) {
                    listedSet.remove(info);
                } else {
                    listedSet.add(info);
                }
            }
        }
    }
}
"""

# 8. TxAdminScreen.java
FILES["com/thenest/txadmin/client/TxAdminScreen.java"] = r"""package com.thenest.txadmin.client;

import com.thenest.txadmin.CharCustomServerManager.CharProfile;
import com.thenest.txadmin.OpenTxAdminPayload;
import com.thenest.txadmin.TxActionPayload;
import com.thenest.txadmin.client.SkinClientManager.LocalPreset;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.components.AbstractWidget;
import net.minecraft.client.gui.components.EditBox;
import net.minecraft.client.gui.narration.NarrationElementOutput;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.input.KeyEvent;
import net.minecraft.client.input.MouseButtonEvent;
import net.minecraft.client.multiplayer.PlayerInfo;
import net.minecraft.network.chat.Component;
import net.neoforged.neoforge.client.network.ClientPacketDistributor;

public class TxAdminScreen extends Screen {
    private static final int COL_BG = 0xEE140F0C;
    private static final int COL_SURFACE = 0xFF1D1611;
    private static final int COL_SURFACE_ALT = 0xFF2C221A;
    private static final int COL_INPUT_BG = 0xFF17120E;
    private static final int COL_ROW_BG = 0xFF211914;
    private static final int COL_DIVIDER = 0xFF2F241B;
    private static final int COL_TEXT = 0xFFF4EDE4;
    private static final int COL_MUTED = 0xFF9C8B7A;
    private static final int COL_ACCENT = 0xFFE09F3E;

    // Warm, calm pill button palette (crisp white text, shadow=false)
    private static final int COL_GOLD_BTN = 0xFF8A5816;
    private static final int COL_GOLD_HOVER = 0xFFA66B1C;
    private static final int COL_GREEN = 0xFF1E663E;
    private static final int COL_GREEN_HOVER = 0xFF277F4F;
    private static final int COL_RED = 0xFF722429;
    private static final int COL_RED_HOVER = 0xFF8F2E34;

    private static final int ROW_H = 30;
    private static final int ROW_PITCH = 34;

    private static final String[] CAT_IDS = {"self", "players", "char", "world", "gamerules", "mods", "items"};
    private static final String[] CAT_LABELS = {
            "Self",
            "Players",
            "Char & Teams",
            "World & Time",
            "Gamerules",
            "Mods & Perf",
            "Casino & Items"
    };

    private record PlayerState(String name, int gm, boolean op, boolean frozen) {}
    private record BtnSpec(String label, int style, Runnable action) {}
    private record RowSpec(String title, String subtitle, List<BtnSpec> buttons) {}
    private record HitBox(int x, int y, int w, int h, Runnable action) {}

    private boolean god;
    private boolean noclip;
    private boolean fly;
    private boolean vanish;
    private boolean nv;
    private int speed;
    private int selfGm;

    private int worldTime = 1000;
    private int worldWeather = 0; // 0=clear, 1=rain, 2=thunder
    private int worldDiff = 2; // 0=peaceful..3=hard
    private int worldTickRate = 20;
    private boolean worldFrozen = false;
    private long worldBorder = 59999968L;
    private int ruleSleepPct = 100;
    private int ruleTickSpeed = 3;
    private int ruleFireSpread = 128;
    private final boolean[] ruleBools = new boolean[16];

    private final List<String> playerNames = new ArrayList<>();
    private final Map<String, PlayerState> playerStates = new HashMap<>();
    private List<LocalPreset> localPresets = new ArrayList<>();
    private int selectedPresetIdx = 0;
    private int selectedPlayerIdx = 0;
    private int selectedCategoryIdx = 0;
    private double scrollOffset = 0.0;
    private String statusText = "Ready — Select a category on the left or click any option.";

    private int panelX, panelY, panelW, panelH;
    private int sideX, sideY, sideW, sideH;
    private int listX, listY, listW, listH;

    private EditBox inputBox;
    private final TxButton[] catButtons = new TxButton[CAT_LABELS.length];
    private final List<RowSpec> currentRows = new ArrayList<>();
    private final List<HitBox> listHits = new ArrayList<>();
    private static volatile TxAdminScreen activeInstance;

    public static TxAdminScreen getActive() {
        return activeInstance;
    }

    public TxAdminScreen(OpenTxAdminPayload payload, String csv) {
        super(Component.literal("The Nest — Admin Panel"));
        activeInstance = this;
        this.localPresets = SkinClientManager.loadLocalPresets();
        applySync(payload, csv);
    }

    public void onCharProfilesUpdated() {
        rebuildRows();
    }

    public void applySync(OpenTxAdminPayload p, String rawCsv) {
        this.god = p.god();
        this.noclip = p.noclip();
        this.fly = p.fly();
        this.vanish = p.vanish();
        this.nv = p.nv();
        this.speed = p.speed();
        this.selfGm = p.selfGm();

        String csv = rawCsv != null ? rawCsv : "";
        int wIdx = csv.indexOf(";W:");
        if (wIdx >= 0) {
            String wStr = csv.substring(wIdx + 3);
            csv = csv.substring(0, wIdx);
            String[] wp = wStr.split("\\|");
            if (wp.length >= 10) {
                this.worldTime = parseIntSafe(wp[0], this.worldTime);
                this.worldWeather = parseIntSafe(wp[1], this.worldWeather);
                this.worldDiff = parseIntSafe(wp[2], this.worldDiff);
                this.worldTickRate = parseIntSafe(wp[3], this.worldTickRate);
                this.worldFrozen = "1".equals(wp[4]);
                try { this.worldBorder = Long.parseLong(wp[5].trim()); } catch (Exception ignored) {}
                this.ruleSleepPct = parseIntSafe(wp[6], this.ruleSleepPct);
                this.ruleTickSpeed = parseIntSafe(wp[7], this.ruleTickSpeed);
                this.ruleFireSpread = parseIntSafe(wp[8], this.ruleFireSpread);
                int mask = parseIntSafe(wp[9], 0);
                for (int i = 0; i < this.ruleBools.length; i++) {
                    this.ruleBools[i] = ((mask >> i) & 1) != 0;
                }
            }
        }

        String prevTarget = getSelectedPlayer();
        this.playerNames.clear();
        this.playerStates.clear();
        if (!csv.isBlank()) {
            for (String s : csv.split(",")) {
                if (s.isBlank()) continue;
                String[] parts = s.trim().split("\\|");
                String name = parts[0].trim();
                int gm = parts.length > 1 ? parseIntSafe(parts[1], 0) : 0;
                boolean op = parts.length > 2 && "1".equals(parts[2]);
                boolean frz = parts.length > 3 && "1".equals(parts[3]);
                this.playerNames.add(name);
                this.playerStates.put(name, new PlayerState(name, gm, op, frz));
            }
        }
        if (this.playerNames.isEmpty() && Minecraft.getInstance().getConnection() != null) {
            for (PlayerInfo info : Minecraft.getInstance().getConnection().getOnlinePlayers()) {
                String n = info.getProfile().name();
                this.playerNames.add(n);
                this.playerStates.put(n, new PlayerState(n, 0, false, false));
            }
        }
        if (this.playerNames.isEmpty() && Minecraft.getInstance().player != null) {
            String n = Minecraft.getInstance().player.getGameProfile().name();
            this.playerNames.add(n);
            this.playerStates.put(n, new PlayerState(n, selfGm, true, false));
        }
        this.playerNames.add("@a");

        int idx = this.playerNames.indexOf(prevTarget);
        this.selectedPlayerIdx = Math.max(0, idx);
        rebuildRows();
    }

    private static int parseIntSafe(String s, int def) {
        try {
            return Integer.parseInt(s.trim());
        } catch (Exception e) {
            return def;
        }
    }

    private static String gmName(int gm) {
        return switch (gm) {
            case 1 -> "Creative";
            case 2 -> "Adventure";
            case 3 -> "Spectator";
            default -> "Survival";
        };
    }

    private String getSelectedPlayer() {
        if (playerNames.isEmpty()) return "@s";
        if (selectedPlayerIdx < 0 || selectedPlayerIdx >= playerNames.size()) {
            selectedPlayerIdx = 0;
        }
        return playerNames.get(selectedPlayerIdx);
    }

    private void cyclePlayer(int delta) {
        if (playerNames.isEmpty()) return;
        selectedPlayerIdx = (selectedPlayerIdx + delta + playerNames.size()) % playerNames.size();
        statusText = "Target Player set to: " + getSelectedPlayer();
        rebuildRows();
    }

    @Override
    public boolean isPauseScreen() {
        return false;
    }

    @Override
    protected void init() {
        super.init();
        this.panelW = Math.min(520, this.width - 16);
        this.panelH = Math.min(312, this.height - 16);
        this.panelX = (this.width - this.panelW) / 2;
        this.panelY = (this.height - this.panelH) / 2;

        this.sideX = this.panelX + 8;
        this.sideY = this.panelY + 38;
        this.sideW = 112;
        this.sideH = this.panelH - 62;

        this.listX = this.sideX + this.sideW + 8;
        this.listY = this.sideY + 24;
        this.listW = this.panelW - this.sideW - 24;
        this.listH = this.sideH - 24;

        int tpY = panelY + 8;
        int tpX = panelX + Math.max(132, (panelW - 144) / 2 - 20);

        this.addRenderableWidget(new TxButton(tpX, tpY, 16, 17, "<", 0, () -> cyclePlayer(-1)));
        this.addRenderableWidget(new TxButton(tpX + 106, tpY, 16, 17, ">", 0, () -> cyclePlayer(1)));
        this.addRenderableWidget(new TxButton(tpX + 125, tpY, 22, 17, "@a", 0, () -> {
            int idx = playerNames.indexOf("@a");
            if (idx >= 0) selectedPlayerIdx = idx;
            statusText = "Target set to @a (All Players)";
            rebuildRows();
        }));

        int rx = panelX + panelW - 96;
        this.addRenderableWidget(new TxButton(rx, tpY, 36, 17, "Save", 2, () -> sendCmd("save-all", "World Saved!")));
        this.addRenderableWidget(new TxButton(rx + 39, tpY, 34, 17, "Bkup", 0, () -> sendCmd("simplebackups backup start", "Backup Started!")));
        this.addRenderableWidget(new TxButton(rx + 76, tpY, 16, 17, "x", 3, this::onClose));

        String prevText = this.inputBox != null ? this.inputBox.getValue() : "";
        this.inputBox = new EditBox(this.font, this.listX, this.sideY, this.listW, 18, Component.literal("Input"));
        this.inputBox.setMaxLength(128);
        this.inputBox.setBordered(false);
        this.inputBox.setHint(Component.literal("Type nick, team, reason, or announcement..."));
        this.inputBox.setValue(prevText);
        this.addRenderableWidget(this.inputBox);

        int cy = sideY + 6;
        for (int i = 0; i < CAT_LABELS.length; i++) {
            final int catIdx = i;
            TxButton btn = new TxButton(sideX + 4, cy, sideW - 8, 22, CAT_LABELS[i], i == selectedCategoryIdx ? 1 : 0, true, () -> {
                selectedCategoryIdx = catIdx;
                scrollOffset = 0;
                if ("char".equals(CAT_IDS[catIdx])) {
                    this.localPresets = SkinClientManager.loadLocalPresets();
                }
                updateCategoryStyles();
                rebuildRows();
            });
            this.catButtons[i] = btn;
            this.addRenderableWidget(btn);
            cy += 24;
        }

        this.addRenderableWidget(new OptionListWidget(listX, listY, listW, listH));
        rebuildRows();
    }

    private void updateCategoryStyles() {
        for (int i = 0; i < catButtons.length; i++) {
            if (catButtons[i] != null) {
                catButtons[i].setStyle(i == selectedCategoryIdx ? 1 : 0);
            }
        }
    }

    private void sendSelf(String action, String feedback) {
        ClientPacketDistributor.sendToServer(new TxActionPayload("self", action, ""));
        this.statusText = feedback;
    }

    private void sendPlayer(String action, String target, String feedback) {
        ClientPacketDistributor.sendToServer(new TxActionPayload("player", action, target));
        this.statusText = feedback;
    }

    private void sendChar(String action, String target, String feedback) {
        ClientPacketDistributor.sendToServer(new TxActionPayload("char", action, target));
        this.statusText = feedback;
    }

    private void sendCmd(String rawCmd, String feedback) {
        ClientPacketDistributor.sendToServer(new TxActionPayload("cmd", rawCmd, ""));
        if (feedback != null && !feedback.isEmpty()) {
            this.statusText = feedback;
        }
    }

    private String getInputOrDefault(String fallback) {
        if (this.inputBox != null && !this.inputBox.getValue().trim().isEmpty()) {
            return this.inputBox.getValue().trim();
        }
        return fallback;
    }

    private void cyclePreset(int delta) {
        this.localPresets = SkinClientManager.loadLocalPresets();
        if (localPresets.isEmpty()) {
            this.statusText = "No saved presets yet — save one in Launcher Skin Studio or click Save Skin!";
            rebuildRows();
            return;
        }
        selectedPresetIdx = (selectedPresetIdx + delta + localPresets.size()) % localPresets.size();
        LocalPreset p = localPresets.get(selectedPresetIdx);
        this.statusText = "Selected Skin Preset: " + p.name() + " (" + (p.slim() ? "Slim 3px" : "Default 4px") + ")";
        rebuildRows();
    }

    private void rebuildRows() {
        this.currentRows.clear();
        String cat = CAT_IDS[this.selectedCategoryIdx];
        String tgt = getSelectedPlayer();
        String myName = Minecraft.getInstance().player != null ? Minecraft.getInstance().player.getGameProfile().name() : "@s";
        PlayerState tgtState = playerStates.get(tgt);
        int tgtGm = tgtState != null ? tgtState.gm() : -1;
        boolean tgtOp = tgtState != null && tgtState.op();
        boolean tgtFrozen = tgtState != null && tgtState.frozen();

        switch (cat) {
            case "self" -> {
                currentRows.add(new RowSpec("God Mode", "Blocks all damage & hunger drain", List.of(
                        new BtnSpec(god ? "GOD: ON" : "GOD: OFF", god ? 2 : 0, () -> sendSelf("god", "Toggled God Mode"))
                )));
                currentRows.add(new RowSpec("NoClip", "Switch Spectator / Survival", List.of(
                        new BtnSpec(noclip ? "NOCLIP: ON" : "NOCLIP: OFF", noclip ? 2 : 0, () -> sendSelf("noclip", "Toggled NoClip"))
                )));
                currentRows.add(new RowSpec("Survival Flight", "Allow flying in Survival mode", List.of(
                        new BtnSpec(fly ? "FLY: ON" : "FLY: OFF", fly ? 2 : 0, () -> sendSelf("fly", "Toggled Survival Flight"))
                )));
                currentRows.add(new RowSpec("Vanish", "Particle-free invisibility", List.of(
                        new BtnSpec(vanish ? "VANISH: ON" : "VANISH: OFF", vanish ? 2 : 0, () -> sendSelf("vanish", "Toggled Vanish"))
                )));
                currentRows.add(new RowSpec("Night Vision", "Infinite fullbright without particles", List.of(
                        new BtnSpec(nv ? "NV: ON" : "NV: OFF", nv ? 2 : 0, () -> sendSelf("nv", "Toggled Night Vision"))
                )));
                currentRows.add(new RowSpec("Movement Speed", "Active: " + (speed == 0 ? "1x Normal" : (1 << speed) + "x Boost"), List.of(
                        new BtnSpec("1x", speed == 0 ? 2 : 0, () -> sendSelf("speed0", "Speed: 1x (Normal)")),
                        new BtnSpec("2x", speed == 1 ? 2 : 0, () -> sendSelf("speed1", "Speed: 2x")),
                        new BtnSpec("4x", speed == 2 ? 2 : 0, () -> sendSelf("speed2", "Speed: 4x")),
                        new BtnSpec("8x", speed == 3 ? 2 : 0, () -> sendSelf("speed3", "Speed: 8x"))
                )));
                currentRows.add(new RowSpec("Health & Effects", "Restore health or clear potion FX", List.of(
                        new BtnSpec("Heal & Feed", 2, () -> sendSelf("heal", "Healed and fed self!")),
                        new BtnSpec("Clear FX", 0, () -> sendSelf("clearfx", "Cleared potion effects"))
                )));
                currentRows.add(new RowSpec("Personal Gamemode", "Mode: " + gmName(selfGm), List.of(
                        new BtnSpec("Surv", selfGm == 0 ? 2 : 0, () -> sendSelf("gms", "Personal Gamemode -> SURVIVAL")),
                        new BtnSpec("Creat", selfGm == 1 ? 2 : 0, () -> sendSelf("gmc", "Personal Gamemode -> CREATIVE")),
                        new BtnSpec("Adv", selfGm == 2 ? 2 : 0, () -> sendSelf("gma", "Personal Gamemode -> ADVENTURE")),
                        new BtnSpec("Spec", selfGm == 3 ? 2 : 0, () -> sendSelf("gmsp", "Personal Gamemode -> SPECTATOR"))
                )));
            }
            case "players" -> {
                currentRows.add(new RowSpec("Teleportation", "Target: " + tgt, List.of(
                        new BtnSpec("TP To", 1, () -> sendPlayer("tpto", getSelectedPlayer(), "Teleported to " + getSelectedPlayer())),
                        new BtnSpec("Bring", 2, () -> sendPlayer("bring", getSelectedPlayer(), "Brought " + getSelectedPlayer())),
                        new BtnSpec("Return", 0, () -> sendPlayer("back", getSelectedPlayer(), "Returned " + getSelectedPlayer()))
                )));
                currentRows.add(new RowSpec("Spectate & Freeze", "Status: " + (tgtFrozen ? "FROZEN" : "Unfrozen"), List.of(
                        new BtnSpec("Spectate", 1, () -> {
                            sendPlayer("spectate", getSelectedPlayer(), "Spectating " + getSelectedPlayer());
                            this.onClose();
                        }),
                        new BtnSpec(tgtFrozen ? "FROZEN: ON" : "Freeze", tgtFrozen ? 2 : 3, () -> sendPlayer("freeze", getSelectedPlayer(), "Toggled Freeze on " + getSelectedPlayer()))
                )));
                currentRows.add(new RowSpec("Inventory & EnderChest", "Inspect live slots of " + tgt, List.of(
                        new BtnSpec("InvSee", 1, () -> sendPlayer("invsee", getSelectedPlayer(), "Opened Inventory of " + getSelectedPlayer())),
                        new BtnSpec("EnderSee", 0, () -> sendPlayer("endersee", getSelectedPlayer(), "Opened EnderChest of " + getSelectedPlayer()))
                )));
                currentRows.add(new RowSpec("Heal, Deaths & Lootr", "Care & recovery for " + tgt, List.of(
                        new BtnSpec("Heal", 2, () -> sendPlayer("heal", getSelectedPlayer(), "Healed " + getSelectedPlayer())),
                        new BtnSpec("Deaths", 1, () -> {
                            sendCmd("deathhistory " + getSelectedPlayer(), "Opening Death History");
                            this.onClose();
                        }),
                        new BtnSpec("Reset Lootr", 0, () -> sendCmd("lootr clear " + getSelectedPlayer(), "Reset Lootr for " + getSelectedPlayer()))
                )));
                currentRows.add(new RowSpec("Target Gamemode", tgt + ": " + (tgtGm >= 0 ? gmName(tgtGm) : "All Players"), List.of(
                        new BtnSpec("Surv", tgtGm == 0 ? 2 : 0, () -> sendPlayer("gms", getSelectedPlayer(), "Set " + getSelectedPlayer() + " -> SURVIVAL")),
                        new BtnSpec("Creat", tgtGm == 1 ? 2 : 0, () -> sendPlayer("gmc", getSelectedPlayer(), "Set " + getSelectedPlayer() + " -> CREATIVE")),
                        new BtnSpec("Adv", tgtGm == 2 ? 2 : 0, () -> sendPlayer("gma", getSelectedPlayer(), "Set " + getSelectedPlayer() + " -> ADVENTURE")),
                        new BtnSpec("Spec", tgtGm == 3 ? 2 : 0, () -> sendPlayer("gmsp", getSelectedPlayer(), "Set " + getSelectedPlayer() + " -> SPECTATOR"))
                )));
                currentRows.add(new RowSpec("Voice Moderation", "Mute or unmute proximity voice", List.of(
                        new BtnSpec("Mute 15m", 3, () -> sendCmd("vcd mute " + getSelectedPlayer() + " 15m Admin_Mute", "Voice muted " + getSelectedPlayer())),
                        new BtnSpec("Unmute", 2, () -> sendCmd("vcd unmute " + getSelectedPlayer(), "Voice unmuted " + getSelectedPlayer()))
                )));
                currentRows.add(new RowSpec("Operator & Whitelist", "Role: " + (tgtOp ? "Server OP" : "Player"), List.of(
                        new BtnSpec(tgtOp ? "OP: YES" : "OP", tgtOp ? 2 : 0, () -> sendCmd("op " + getSelectedPlayer(), "Granted OP to " + getSelectedPlayer())),
                        new BtnSpec("De-OP", 0, () -> sendCmd("deop " + getSelectedPlayer(), "Removed OP from " + getSelectedPlayer())),
                        new BtnSpec("WL+", 1, () -> sendCmd("whitelist add " + getSelectedPlayer(), "Whitelisted " + getSelectedPlayer())),
                        new BtnSpec("WL-", 0, () -> sendCmd("whitelist remove " + getSelectedPlayer(), "Removed from Whitelist"))
                )));
                currentRows.add(new RowSpec("Kick & Ban", "Uses input bar reason if filled", List.of(
                        new BtnSpec("Kick", 1, () -> sendCmd("kick " + getSelectedPlayer() + " " + getInputOrDefault("Kicked by Admin"), "Kicked " + getSelectedPlayer())),
                        new BtnSpec("Ban", 3, () -> sendCmd("ban " + getSelectedPlayer() + " " + getInputOrDefault("Banned by Admin"), "Banned " + getSelectedPlayer())),
                        new BtnSpec("Unban", 2, () -> sendCmd("pardon " + getSelectedPlayer(), "Unbanned " + getSelectedPlayer()))
                )));
            }
            case "char" -> {
                if (selectedPresetIdx >= localPresets.size()) selectedPresetIdx = 0;
                LocalPreset curPre = localPresets.isEmpty() ? null : localPresets.get(selectedPresetIdx);
                String preSub = curPre != null
                        ? (selectedPresetIdx + 1) + "/" + localPresets.size() + ": " + curPre.name() + " (" + (curPre.slim() ? "Slim" : "4px") + ")"
                        : "Save presets in Launcher Skin Studio";

                currentRows.add(new RowSpec("Skin Presets", preSub, List.of(
                        new BtnSpec("<", 0, () -> cyclePreset(-1)),
                        new BtnSpec(">", 0, () -> cyclePreset(1)),
                        new BtnSpec("Me", 2, () -> {
                            if (curPre != null && SkinClientManager.equipPreset(curPre, "")) {
                                statusText = "Equipped preset '" + curPre.name() + "' on yourself!";
                            } else {
                                statusText = "No preset selected or file missing.";
                            }
                        }),
                        new BtnSpec("Target", 1, () -> {
                            if (curPre != null && SkinClientManager.equipPreset(curPre, getSelectedPlayer())) {
                                statusText = "Applied preset '" + curPre.name() + "' to " + getSelectedPlayer() + "!";
                            } else {
                                statusText = "No preset selected.";
                            }
                        }),
                        new BtnSpec("Save", 0, () -> {
                            String pName = getInputOrDefault(getSelectedPlayer() + "_Skin");
                            if (SkinClientManager.saveSkinAsPreset(getSelectedPlayer(), pName)) {
                                this.localPresets = SkinClientManager.loadLocalPresets();
                                this.selectedPresetIdx = Math.max(0, this.localPresets.size() - 1);
                                statusText = "Saved skin of " + getSelectedPlayer() + " as preset '" + pName + "'!";
                                rebuildRows();
                            } else {
                                statusText = "Could not save preset (no active custom/Mojang skin loaded).";
                            }
                        })
                )));

                boolean isSlim = SkinClientManager.isPlayerSlim(tgt);
                currentRows.add(new RowSpec("Mojang Skin & Arms", tgt + " · " + (isSlim ? "Slim 3px" : "Default 4px"), List.of(
                        new BtnSpec("Fetch", 1, () -> sendChar("fetchskin:" + getInputOrDefault(myName), getSelectedPlayer(), "Fetching Mojang skin for " + getSelectedPlayer())),
                        new BtnSpec("4px", !isSlim ? 2 : 0, () -> sendChar("arm:default", getSelectedPlayer(), "Set Default (4px) arms for " + getSelectedPlayer())),
                        new BtnSpec("Slim", isSlim ? 2 : 0, () -> sendChar("arm:slim", getSelectedPlayer(), "Set Slim (3px) arms for " + getSelectedPlayer())),
                        new BtnSpec("Reset", 0, () -> sendChar("skinreset", getSelectedPlayer(), "Reset skin for " + getSelectedPlayer()))
                )));

                CharProfile prof = CharCustomClientManager.getProfile(tgt);
                String curNick = (prof != null && !prof.customNick().isBlank()) ? prof.customNick() : tgt;
                String curCol = prof != null ? prof.colorCode() : "f";
                boolean isBold = prof != null && prof.bold();
                int opMode = prof != null ? prof.opacityMode() : 0;
                boolean tabHid = prof != null && prof.tabHidden();
                String curTeam = (prof != null && !prof.teamName().isBlank()) ? prof.teamName() : "None";

                currentRows.add(new RowSpec("Nickname", tgt + " -> " + curNick, List.of(
                        new BtnSpec("My Nick", 1, () -> sendChar("nick:" + getInputOrDefault(myName), myName, "Changed your nickname to " + getInputOrDefault(myName))),
                        new BtnSpec("Set Target", 2, () -> sendChar("nick:" + getInputOrDefault(getSelectedPlayer()), getSelectedPlayer(), "Changed " + getSelectedPlayer() + "'s nick to " + getInputOrDefault(getSelectedPlayer()))),
                        new BtnSpec("Reset", 0, () -> sendChar("nickreset", getSelectedPlayer(), "Reset nickname for " + getSelectedPlayer()))
                )));

                currentRows.add(new RowSpec("Primary Colors", tgt + " nickname palette", List.of(
                        new BtnSpec("Gold", "6".equals(curCol) ? 2 : 1, () -> sendChar("color:6", getSelectedPlayer(), "Color -> Gold")),
                        new BtnSpec("Red", "c".equals(curCol) ? 2 : 3, () -> sendChar("color:c", getSelectedPlayer(), "Color -> Red")),
                        new BtnSpec("Aqua", "b".equals(curCol) ? 2 : 0, () -> sendChar("color:b", getSelectedPlayer(), "Color -> Aqua")),
                        new BtnSpec("Green", "a".equals(curCol) ? 2 : 0, () -> sendChar("color:a", getSelectedPlayer(), "Color -> Green")),
                        new BtnSpec("Purp", "d".equals(curCol) ? 2 : 0, () -> sendChar("color:d", getSelectedPlayer(), "Color -> Light Purple")),
                        new BtnSpec("Yel", "e".equals(curCol) ? 2 : 0, () -> sendChar("color:e", getSelectedPlayer(), "Color -> Yellow")),
                        new BtnSpec("White", "f".equals(curCol) ? 2 : 0, () -> sendChar("color:f", getSelectedPlayer(), "Color -> White"))
                )));

                currentRows.add(new RowSpec("Extra Colors & Bold", "Deep shades + weight", List.of(
                        new BtnSpec("Blue", "9".equals(curCol) ? 2 : 0, () -> sendChar("color:9", getSelectedPlayer(), "Color -> Blue")),
                        new BtnSpec("DkRed", "4".equals(curCol) ? 2 : 0, () -> sendChar("color:4", getSelectedPlayer(), "Color -> Dark Red")),
                        new BtnSpec("DkPurp", "5".equals(curCol) ? 2 : 0, () -> sendChar("color:5", getSelectedPlayer(), "Color -> Dark Purple")),
                        new BtnSpec("Gray", "7".equals(curCol) ? 2 : 0, () -> sendChar("color:7", getSelectedPlayer(), "Color -> Gray")),
                        new BtnSpec("Black", "0".equals(curCol) ? 2 : 0, () -> sendChar("color:0", getSelectedPlayer(), "Color -> Black")),
                        new BtnSpec(isBold ? "BOLD: ON" : "Bold", isBold ? 2 : 0, () -> sendChar("bold:toggle", getSelectedPlayer(), "Toggled Bold Nickname"))
                )));

                currentRows.add(new RowSpec("All Players Color", "Uniform color for everyone", List.of(
                        new BtnSpec("Gold", 1, () -> sendChar("allcolor:6", "@a", "Set ALL players' nickname color to Gold!")),
                        new BtnSpec("Red", 3, () -> sendChar("allcolor:c", "@a", "Set ALL players' nickname color to Red!")),
                        new BtnSpec("Aqua", 0, () -> sendChar("allcolor:b", "@a", "Set ALL players' nickname color to Aqua!")),
                        new BtnSpec("Green", 2, () -> sendChar("allcolor:a", "@a", "Set ALL players' nickname color to Green!")),
                        new BtnSpec("White", 0, () -> sendChar("allcolor:f", "@a", "Reset ALL players' nickname color to White"))
                )));

                String opLabel = switch (opMode) {
                    case 1 -> "50% Faded";
                    case 2 -> "Hidden (0%)";
                    default -> "100% Visible";
                };
                currentRows.add(new RowSpec("Nametag Opacity", tgt + ": " + opLabel, List.of(
                        new BtnSpec("100%", opMode == 0 ? 2 : 0, () -> sendChar("opacity:0", getSelectedPlayer(), "Nametag Opacity -> 100% Full")),
                        new BtnSpec("50%", opMode == 1 ? 2 : 0, () -> sendChar("opacity:1", getSelectedPlayer(), "Nametag Opacity -> 50% Faded")),
                        new BtnSpec("0% Off", opMode == 2 ? 3 : 0, () -> sendChar("opacity:2", getSelectedPlayer(), "Nametag Opacity -> 0% Hidden"))
                )));

                CharProfile selfProf = CharCustomClientManager.getProfile(myName);
                boolean selfTabHid = selfProf != null && selfProf.tabHidden();
                currentRows.add(new RowSpec("TAB Visibility", tgt + ": " + (tabHid ? "HIDDEN" : "VISIBLE"), List.of(
                        new BtnSpec(tabHid ? "Show Tgt" : "Hide Tgt", tabHid ? 3 : 0, () -> sendChar("tab:toggle", getSelectedPlayer(), "Toggled TAB visibility for " + getSelectedPlayer())),
                        new BtnSpec(selfTabHid ? "Show Me" : "Hide Me", selfTabHid ? 3 : 0, () -> sendChar("tab:toggle", myName, "Toggled your own TAB visibility")),
                        new BtnSpec("All On", 2, () -> sendChar("tab:showall", "@a", "All players visible in TAB menu")),
                        new BtnSpec("All Off", 0, () -> sendChar("tab:hideall", "@a", "All players hidden in TAB menu"))
                )));

                currentRows.add(new RowSpec("Preset Teams", "Active: " + curTeam, List.of(
                        new BtnSpec("Red", "Red".equalsIgnoreCase(curTeam) ? 2 : 3, () -> sendChar("team:Red:c", getSelectedPlayer(), "Joined " + getSelectedPlayer() + " to Red Team")),
                        new BtnSpec("Blue", "Blue".equalsIgnoreCase(curTeam) ? 2 : 0, () -> sendChar("team:Blue:9", getSelectedPlayer(), "Joined " + getSelectedPlayer() + " to Blue Team")),
                        new BtnSpec("Gold", "Gold".equalsIgnoreCase(curTeam) ? 2 : 1, () -> sendChar("team:Gold:6", getSelectedPlayer(), "Joined " + getSelectedPlayer() + " to Gold Team")),
                        new BtnSpec("Green", "Green".equalsIgnoreCase(curTeam) ? 2 : 0, () -> sendChar("team:Green:a", getSelectedPlayer(), "Joined " + getSelectedPlayer() + " to Green Team")),
                        new BtnSpec("Purp", "Purple".equalsIgnoreCase(curTeam) ? 2 : 0, () -> sendChar("team:Purple:d", getSelectedPlayer(), "Joined " + getSelectedPlayer() + " to Purple Team")),
                        new BtnSpec("Leave", 0, () -> sendChar("teamleave", getSelectedPlayer(), "Removed " + getSelectedPlayer() + " from team"))
                )));

                currentRows.add(new RowSpec("Custom Team", "Type name above & pick color", List.of(
                        new BtnSpec("+Gold", 1, () -> sendChar("mkteam:6:" + getInputOrDefault("VIP"), getSelectedPlayer(), "Created/Joined Gold team '" + getInputOrDefault("VIP") + "'")),
                        new BtnSpec("+Red", 3, () -> sendChar("mkteam:c:" + getInputOrDefault("Red"), getSelectedPlayer(), "Created/Joined Red team '" + getInputOrDefault("Red") + "'")),
                        new BtnSpec("+Aqua", 0, () -> sendChar("mkteam:b:" + getInputOrDefault("Aqua"), getSelectedPlayer(), "Created/Joined Aqua team '" + getInputOrDefault("Aqua") + "'")),
                        new BtnSpec("+Green", 2, () -> sendChar("mkteam:a:" + getInputOrDefault("Squad"), getSelectedPlayer(), "Created/Joined Green team '" + getInputOrDefault("Squad") + "'")),
                        new BtnSpec("Clear", 0, () -> sendChar("clearteams", "@a", "Cleared all custom teams"))
                )));

                currentRows.add(new RowSpec("Team Rules", "Friendly fire & nametags", List.of(
                        new BtnSpec("PVP On", 2, () -> sendChar("teampvp:on", "@a", "Team Friendly Fire: ON")),
                        new BtnSpec("PVP Off", 3, () -> sendChar("teampvp:off", "@a", "Team Friendly Fire: OFF")),
                        new BtnSpec("Tags All", 0, () -> sendChar("teamvis:always", "@a", "Team Nametags: Always Visible")),
                        new BtnSpec("Own Only", 1, () -> sendChar("teamvis:own", "@a", "Team Nametags: Own Team Only")),
                        new BtnSpec("Tags Off", 0, () -> sendChar("teamvis:never", "@a", "Team Nametags: Hidden"))
                )));
            }
            case "world" -> {
                int tb = (worldTime >= 5000 && worldTime < 11000) ? 1
                        : (worldTime >= 11000 && worldTime < 13000) ? 2
                        : (worldTime >= 13000) ? 3 : 0;
                String tbName = switch (tb) {
                    case 1 -> "Noon";
                    case 2 -> "Sunset";
                    case 3 -> "Night";
                    default -> "Day";
                };
                currentRows.add(new RowSpec("Time of Day", "Current: " + tbName + " (" + worldTime + " ticks)", List.of(
                        new BtnSpec("Day", tb == 0 ? 1 : 0, () -> { worldTime = 1000; rebuildRows(); sendCmd("time set day", "Time: Day"); }),
                        new BtnSpec("Noon", tb == 1 ? 1 : 0, () -> { worldTime = 6000; rebuildRows(); sendCmd("time set noon", "Time: Noon"); }),
                        new BtnSpec("Sunset", tb == 2 ? 1 : 0, () -> { worldTime = 12000; rebuildRows(); sendCmd("time set 12000", "Time: Sunset"); }),
                        new BtnSpec("Night", tb == 3 ? 1 : 0, () -> { worldTime = 13000; rebuildRows(); sendCmd("time set night", "Time: Night"); }),
                        new BtnSpec("+1d", 0, () -> sendCmd("time add 24000", "Added 1 Day"))
                )));
                String wName = worldWeather == 2 ? "Thunder" : (worldWeather == 1 ? "Rain" : "Clear");
                currentRows.add(new RowSpec("Weather", "Sky: " + wName, List.of(
                        new BtnSpec("Clear", worldWeather == 0 ? 2 : 0, () -> { worldWeather = 0; rebuildRows(); sendCmd("weather clear", "Weather: Clear"); }),
                        new BtnSpec("Clear 1h", 0, () -> { worldWeather = 0; rebuildRows(); sendCmd("weather clear 3600s", "Weather: Clear 1h"); }),
                        new BtnSpec("Rain", worldWeather == 1 ? 2 : 0, () -> { worldWeather = 1; rebuildRows(); sendCmd("weather rain", "Weather: Rain"); }),
                        new BtnSpec("Thunder", worldWeather == 2 ? 2 : 0, () -> { worldWeather = 2; rebuildRows(); sendCmd("weather thunder", "Weather: Thunder"); })
                )));
                String dName = switch (worldDiff) {
                    case 0 -> "Peaceful";
                    case 1 -> "Easy";
                    case 3 -> "Hard";
                    default -> "Normal";
                };
                currentRows.add(new RowSpec("Difficulty", "Mode: " + dName, List.of(
                        new BtnSpec("Peaceful", worldDiff == 0 ? 2 : 0, () -> { worldDiff = 0; rebuildRows(); sendCmd("difficulty peaceful", "Difficulty: Peaceful"); }),
                        new BtnSpec("Easy", worldDiff == 1 ? 2 : 0, () -> { worldDiff = 1; rebuildRows(); sendCmd("difficulty easy", "Difficulty: Easy"); }),
                        new BtnSpec("Normal", worldDiff == 2 ? 2 : 0, () -> { worldDiff = 2; rebuildRows(); sendCmd("difficulty normal", "Difficulty: Normal"); }),
                        new BtnSpec("Hard", worldDiff == 3 ? 2 : 0, () -> { worldDiff = 3; rebuildRows(); sendCmd("difficulty hard", "Difficulty: Hard"); })
                )));
                currentRows.add(new RowSpec("Tick Rate", worldFrozen ? "Status: FROZEN" : ("Rate: " + worldTickRate + " TPS"), List.of(
                        new BtnSpec("20 TPS", !worldFrozen && worldTickRate == 20 ? 2 : 0, () -> { worldFrozen = false; worldTickRate = 20; rebuildRows(); sendCmd("tick unfreeze", ""); sendCmd("tick rate 20", "Tick Rate: 20 TPS"); }),
                        new BtnSpec("10 TPS", !worldFrozen && worldTickRate == 10 ? 2 : 0, () -> { worldFrozen = false; worldTickRate = 10; rebuildRows(); sendCmd("tick unfreeze", ""); sendCmd("tick rate 10", "Tick Rate: 10 TPS"); }),
                        new BtnSpec(worldFrozen ? "FROZEN" : "Freeze", worldFrozen ? 3 : 0, () -> {
                            boolean next = !worldFrozen;
                            worldFrozen = next;
                            rebuildRows();
                            sendCmd(next ? "tick freeze" : "tick unfreeze", next ? "World Frozen" : "World Unfrozen");
                        })
                )));
                String wbTxt = worldBorder >= 50000000L ? "Vanilla (60M)" : (worldBorder + "m");
                currentRows.add(new RowSpec("World Border", "Diameter: " + wbTxt, List.of(
                        new BtnSpec("2.5k", Math.abs(worldBorder - 2500L) <= 2 ? 2 : 0, () -> { worldBorder = 2500L; rebuildRows(); sendCmd("worldborder set 2500", "Border: 2500m"); }),
                        new BtnSpec("5k", Math.abs(worldBorder - 5000L) <= 2 ? 2 : 0, () -> { worldBorder = 5000L; rebuildRows(); sendCmd("worldborder set 5000", "Border: 5000m"); }),
                        new BtnSpec("10k", Math.abs(worldBorder - 10000L) <= 2 ? 2 : 0, () -> { worldBorder = 10000L; rebuildRows(); sendCmd("worldborder set 10000", "Border: 10000m"); }),
                        new BtnSpec("Center", 0, () -> sendCmd("worldborder center 0 0", "Border centered at 0,0")),
                        new BtnSpec("60M", worldBorder >= 50000000L ? 2 : 0, () -> { worldBorder = 59999968L; rebuildRows(); sendCmd("worldborder set 59999968", "Border reset"); })
                )));
                currentRows.add(new RowSpec("Announcement", "Broadcast text from bar above", List.of(
                        new BtnSpec("Title", 1, () -> {
                            String msg = getInputOrDefault("Welcome to The Nest!").replace("\"", "'");
                            sendCmd("title @a title {\"text\":\"" + msg + "\",\"color\":\"gold\",\"bold\":true}", "Sent Title Banner");
                        }),
                        new BtnSpec("Actionbar", 0, () -> {
                            String msg = getInputOrDefault("Welcome to The Nest!").replace("\"", "'");
                            sendCmd("title @a actionbar {\"text\":\"" + msg + "\",\"color\":\"yellow\"}", "Sent Actionbar");
                        }),
                        new BtnSpec("Chat", 0, () -> {
                            String msg = getInputOrDefault("Server Announcement").replace("\"", "'");
                            sendCmd("tellraw @a [{\"text\":\"[The Nest] \",\"color\":\"gold\",\"bold\":true},{\"text\":\"" + msg + "\",\"color\":\"yellow\"}]", "Sent Chat Broadcast");
                        })
                )));
            }
            case "gamerules" -> {
                currentRows.add(new RowSpec("Players Sleeping %", "Active: " + ruleSleepPct + "%", List.of(
                        new BtnSpec("1% (1P)", ruleSleepPct == 1 ? 2 : 0, () -> { ruleSleepPct = 1; rebuildRows(); sendCmd("gamerule players_sleeping_percentage 1", "1-Player Sleep ON"); }),
                        new BtnSpec("50%", ruleSleepPct == 50 ? 2 : 0, () -> { ruleSleepPct = 50; rebuildRows(); sendCmd("gamerule players_sleeping_percentage 50", "Sleep: 50%"); }),
                        new BtnSpec("100%", ruleSleepPct == 100 ? 2 : 0, () -> { ruleSleepPct = 100; rebuildRows(); sendCmd("gamerule players_sleeping_percentage 100", "Sleep: 100%"); })
                )));
                currentRows.add(new RowSpec("Random Tick Speed", "Active: " + ruleTickSpeed + " (Vanilla 3)", List.of(
                        new BtnSpec("0", ruleTickSpeed == 0 ? 2 : 0, () -> { ruleTickSpeed = 0; rebuildRows(); sendCmd("gamerule random_tick_speed 0", "Tick Speed: 0"); }),
                        new BtnSpec("3", ruleTickSpeed == 3 ? 2 : 0, () -> { ruleTickSpeed = 3; rebuildRows(); sendCmd("gamerule random_tick_speed 3", "Tick Speed: 3"); }),
                        new BtnSpec("6", ruleTickSpeed == 6 ? 2 : 0, () -> { ruleTickSpeed = 6; rebuildRows(); sendCmd("gamerule random_tick_speed 6", "Tick Speed: 6"); }),
                        new BtnSpec("12", ruleTickSpeed == 12 ? 2 : 0, () -> { ruleTickSpeed = 12; rebuildRows(); sendCmd("gamerule random_tick_speed 12", "Tick Speed: 12"); })
                )));
                boolean fireOn = ruleFireSpread > 0;
                currentRows.add(new RowSpec("Fire Spread Radius", "fire_spread_radius (" + (fireOn ? ruleFireSpread + "m" : "Off") + ")", List.of(
                        new BtnSpec("ON", fireOn ? 2 : 0, () -> { ruleFireSpread = 128; rebuildRows(); sendCmd("gamerule fire_spread_radius_around_player 128", "Fire Spread: ON (128)"); }),
                        new BtnSpec("OFF", !fireOn ? 3 : 0, () -> { ruleFireSpread = 0; rebuildRows(); sendCmd("gamerule fire_spread_radius_around_player 0", "Fire Spread: OFF"); })
                )));
                String[][] rules = {
                        {"Keep Inventory", "keep_inventory"},
                        {"Mob Griefing", "mob_griefing"},
                        {"PvP Combat", "pvp"},
                        {"Player Locator Bar", "locator_bar"},
                        {"Phantom Spawning", "spawn_phantoms"},
                        {"Daylight Cycle", "advance_time"},
                        {"Weather Cycle", "advance_weather"},
                        {"Pillager Patrols", "spawn_patrols"},
                        {"Wandering Traders", "spawn_wandering_traders"},
                        {"Warden Spawning", "spawn_wardens"},
                        {"Mob Spawning", "spawn_mobs"},
                        {"Fall Damage", "fall_damage"},
                        {"TNT Explosions", "tnt_explodes"},
                        {"Advancement Alerts", "show_advancement_messages"},
                        {"Death Messages", "show_death_messages"},
                        {"Immediate Respawn", "immediate_respawn"}
                };
                for (int i = 0; i < rules.length; i++) {
                    final int idx = i;
                    final String title = rules[i][0];
                    final String id = rules[i][1];
                    final boolean active = ruleBools[i];
                    currentRows.add(new RowSpec(title, id, List.of(
                            new BtnSpec("ON", active ? 2 : 0, () -> { ruleBools[idx] = true; rebuildRows(); sendCmd("gamerule " + id + " true", id + " = true"); }),
                            new BtnSpec("OFF", !active ? 3 : 0, () -> { ruleBools[idx] = false; rebuildRows(); sendCmd("gamerule " + id + " false", id + " = false"); })
                    )));
                }
            }
            case "mods" -> {
                currentRows.add(new RowSpec("Voxy Server Side", "Distant LOD service & backfill", List.of(
                        new BtnSpec("Status", 0, () -> sendCmd("vsslod status", "Queried VSS Status")),
                        new BtnSpec("Reload", 0, () -> sendCmd("vsslod reload", "Reloaded Voxy Server Side")),
                        new BtnSpec("Backfill", 2, () -> sendCmd("vsslod backfill start", "Started VSS Backfill")),
                        new BtnSpec("Stop", 0, () -> sendCmd("vsslod backfill stop", "Stopped VSS Backfill"))
                )));
                currentRows.add(new RowSpec("ServerCore", "Dynamic view distance & mobcaps", List.of(
                        new BtnSpec("Status", 0, () -> sendCmd("servercore status", "Queried ServerCore")),
                        new BtnSpec("Mobcaps", 0, () -> sendCmd("mobcaps", "Queried Mobcaps")),
                        new BtnSpec("Reload", 1, () -> sendCmd("servercore reload", "Reloaded ServerCore"))
                )));
                currentRows.add(new RowSpec("Chunky Pre-Gen", "Pre-generate 5000m Overworld", List.of(
                        new BtnSpec("Start 5k", 2, () -> {
                            sendCmd("chunky world minecraft:overworld", "");
                            sendCmd("chunky center 0 0", "");
                            sendCmd("chunky radius 5000", "");
                            sendCmd("chunky start", "Started Chunky 5000m Pre-Gen");
                        }),
                        new BtnSpec("Pause", 0, () -> sendCmd("chunky pause", "Paused Chunky")),
                        new BtnSpec("Cont", 0, () -> sendCmd("chunky continue", "Resumed Chunky")),
                        new BtnSpec("Stop", 0, () -> sendCmd("chunky cancel", "Cancelled Chunky"))
                )));
                currentRows.add(new RowSpec("Spark Profiler", "Inspect TPS, memory & CPU", List.of(
                        new BtnSpec("TPS", 1, () -> sendCmd("spark tps", "Queried Spark TPS")),
                        new BtnSpec("Health", 0, () -> sendCmd("spark health", "Queried Spark Health")),
                        new BtnSpec("Mem", 0, () -> sendCmd("spark memory", "Queried Spark Memory")),
                        new BtnSpec("Start", 2, () -> sendCmd("spark profiler start", "Started Spark Profiler")),
                        new BtnSpec("Stop", 0, () -> sendCmd("spark profiler stop", "Stopped Spark Profiler"))
                )));
                currentRows.add(new RowSpec("Simple Backups", "Immediate backup & flush", List.of(
                        new BtnSpec("Start Backup", 2, () -> sendCmd("simplebackups backup start", "Started World Backup")),
                        new BtnSpec("Save-All", 0, () -> sendCmd("save-all flush", "Flushed World Save"))
                )));
            }
            case "items" -> {
                currentRows.add(new RowSpec("Casino Tables", "Give 1x table to " + tgt, List.of(
                        new BtnSpec("Slots", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:slot_machine 1", "Gave Slot Machine")),
                        new BtnSpec("Roulette", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:roulette_table 1", "Gave Roulette")),
                        new BtnSpec("Blackjack", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:blackjack_table 1", "Gave Blackjack")),
                        new BtnSpec("Poker", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:poker_table 1", "Gave Poker Table"))
                )));
                currentRows.add(new RowSpec("Casino Arcade", "Fortune wheel, Plinko & Duck Derby", List.of(
                        new BtnSpec("Wheel", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:fortune_wheel 1", "Gave Fortune Wheel")),
                        new BtnSpec("Plinko", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:plinko 1", "Gave Plinko")),
                        new BtnSpec("Duck Derby", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:duck_derby 1", "Gave Duck Derby"))
                )));
                currentRows.add(new RowSpec("Croupier & Chips", "Hire croupiers or spawn chips", List.of(
                        new BtnSpec("Croupier", 1, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:croupier_hiring_card 1", "Gave Croupier Card")),
                        new BtnSpec("Chip Case", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:chip_case 1", "Gave Chip Case")),
                        new BtnSpec("Chips", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:casino_chip_pile 1", "Gave Chip Pile")),
                        new BtnSpec("Register", 0, () -> sendCmd("give " + getSelectedPlayer() + " casinodeco:cash_register 1", "Gave Cash Register"))
                )));
                currentRows.add(new RowSpec("FM Radio & Boombox", "Custom 3D audio devices", List.of(
                        new BtnSpec("FM Radio", 1, () -> sendCmd("give " + getSelectedPlayer() + " music_disc_maker:fm_radio 1", "Gave FM Radio")),
                        new BtnSpec("Boombox", 0, () -> sendCmd("give " + getSelectedPlayer() + " music_disc_maker:boombox 1", "Gave Boombox"))
                )));
                currentRows.add(new RowSpec("Builder & Security", "WorldEdit, Easy NPC & SecurityCraft", List.of(
                        new BtnSpec("WE Axe", 0, () -> sendCmd("give " + getSelectedPlayer() + " minecraft:wooden_axe 1", "Gave WorldEdit Wand")),
                        new BtnSpec("NPC Wand", 0, () -> sendCmd("give " + getSelectedPlayer() + " easy_npc:easy_npc_wand 1", "Gave Easy NPC Wand")),
                        new BtnSpec("SC Tool", 0, () -> sendCmd("give " + getSelectedPlayer() + " securitycraft:universal_block_modifier 1", "Gave SecurityCraft Tool"))
                )));
            }
        }
        clampScroll();
    }

    private void clampScroll() {
        int totalH = currentRows.size() * ROW_PITCH;
        int maxScroll = Math.max(0, totalH - this.listH + 8);
        if (this.scrollOffset < 0) this.scrollOffset = 0;
        if (this.scrollOffset > maxScroll) this.scrollOffset = maxScroll;
    }

    @Override
    public void extractBackground(GuiGraphicsExtractor g, int mouseX, int mouseY, float partialTick) {
        this.extractTransparentBackground(g);
    }

    @Override
    public void extractRenderState(GuiGraphicsExtractor g, int mouseX, int mouseY, float partialTick) {
        // Clean unified container + subtle hairline dividers
        g.fill(panelX, panelY, panelX + panelW, panelY + panelH, COL_BG);

        // Header surface + gold vertical accent mark
        g.fill(panelX, panelY, panelX + panelW, panelY + 32, COL_SURFACE);
        g.fill(panelX, panelY + 32, panelX + panelW, panelY + 33, COL_DIVIDER);
        g.fill(panelX + 8, panelY + 10, panelX + 10, panelY + 23, COL_ACCENT);
        g.text(this.font, "THE NEST", panelX + 15, panelY + 9, COL_TEXT, false);
        g.text(this.font, "Admin", panelX + 15, panelY + 18, COL_MUTED, false);

        // Target player readout pill in header center
        int tpY = panelY + 8;
        int tpX = panelX + Math.max(132, (panelW - 144) / 2 - 20);
        g.fill(tpX + 18, tpY, tpX + 104, tpY + 17, COL_INPUT_BG);
        String pName = this.font.plainSubstrByWidth(getSelectedPlayer(), 78);
        int pTx = tpX + 18 + (86 - this.font.width(pName)) / 2;
        g.text(this.font, pName, pTx, tpY + 5, COL_TEXT, false);

        // Left sidebar surface + hairline right divider
        g.fill(sideX, sideY, sideX + sideW, sideY + sideH, COL_SURFACE);
        g.fill(sideX + sideW, sideY, sideX + sideW + 1, sideY + sideH, COL_DIVIDER);

        // Input bar subtle container backdrop & bottom hairline
        g.fill(listX, sideY, listX + listW, sideY + 18, COL_INPUT_BG);
        g.fill(listX, sideY + 18, listX + listW, sideY + 19,
                (this.inputBox != null && this.inputBox.isFocused()) ? COL_ACCENT : COL_DIVIDER);

        // Footer bar
        int fy = panelY + panelH - 18;
        g.fill(panelX, fy - 1, panelX + panelW, fy, COL_DIVIDER);
        g.fill(panelX, fy, panelX + panelW, panelY + panelH, COL_SURFACE);
        g.text(this.font, this.font.plainSubstrByWidth(statusText, panelW - 18), panelX + 9, fy + 5, COL_MUTED, false);

        super.extractRenderState(g, mouseX, mouseY, partialTick);
    }

    @Override
    public boolean mouseScrolled(double mouseX, double mouseY, double scrollX, double scrollY) {
        if (mouseX >= listX && mouseX <= listX + listW && mouseY >= listY && mouseY <= listY + listH) {
            this.scrollOffset -= scrollY * 22.0;
            clampScroll();
            return true;
        }
        return super.mouseScrolled(mouseX, mouseY, scrollX, scrollY);
    }

    @Override
    public boolean keyPressed(KeyEvent event) {
        if (this.inputBox != null && this.inputBox.isFocused()) {
            if (event.key() == 256) {
                this.inputBox.setFocused(false);
                return true;
            }
            return this.inputBox.keyPressed(event);
        }
        return super.keyPressed(event);
    }

    private final class TxButton extends AbstractWidget {
        private final String label;
        private int style;
        private final boolean sidebarTab;
        private final Runnable onPress;

        TxButton(int x, int y, int w, int h, String label, int style, Runnable onPress) {
            this(x, y, w, h, label, style, false, onPress);
        }

        TxButton(int x, int y, int w, int h, String label, int style, boolean sidebarTab, Runnable onPress) {
            super(x, y, w, h, Component.literal(label));
            this.label = label;
            this.style = style;
            this.sidebarTab = sidebarTab;
            this.onPress = onPress;
        }

        void setStyle(int style) {
            this.style = style;
        }

        @Override
        public void onClick(MouseButtonEvent event, boolean doubleClick) {
            if (this.onPress != null) {
                this.onPress.run();
            }
        }

        @Override
        protected void extractWidgetRenderState(GuiGraphicsExtractor g, int mouseX, int mouseY, float partialTick) {
            int x = this.getX();
            int y = this.getY();
            int w = this.getWidth();
            int h = this.getHeight();
            boolean hov = this.isHoveredOrFocused();
            if (sidebarTab) {
                boolean active = (style == 1);
                int bg = active ? 0xFF2B2118 : (hov ? 0xFF251C15 : 0x00000000);
                if (bg != 0) {
                    g.fill(x, y, x + w, y + h, bg);
                }
                if (active) {
                    g.fill(x, y + 3, x + 2, y + h - 3, COL_ACCENT);
                }
                int fg = active ? COL_ACCENT : (hov ? COL_TEXT : COL_MUTED);
                int ty = y + (h - 8) / 2;
                g.text(TxAdminScreen.this.font, label, x + 9, ty, fg, false);
                return;
            }
            int bg;
            int fg = COL_TEXT;
            if (style == 1) {
                bg = hov ? COL_GOLD_HOVER : COL_GOLD_BTN;
            } else if (style == 2) {
                bg = hov ? COL_GREEN_HOVER : COL_GREEN;
            } else if (style == 3) {
                bg = hov ? COL_RED_HOVER : COL_RED;
            } else {
                bg = hov ? 0xFF3A2D23 : COL_SURFACE_ALT;
            }
            g.fill(x, y, x + w, y + h, bg);
            int tx = x + (w - TxAdminScreen.this.font.width(label)) / 2;
            int ty = y + (h - 8) / 2;
            g.text(TxAdminScreen.this.font, label, tx, ty, fg, false);
        }

        @Override
        protected void updateWidgetNarration(NarrationElementOutput narration) {
            this.defaultButtonNarrationText(narration);
        }
    }

    private final class OptionListWidget extends AbstractWidget {
        OptionListWidget(int x, int y, int w, int h) {
            super(x, y, w, h, Component.empty());
        }

        @Override
        public void onClick(MouseButtonEvent event, boolean doubleClick) {
            double mx = event.x();
            double my = event.y();
            for (HitBox hit : listHits) {
                if (mx >= hit.x() && mx < hit.x() + hit.w() && my >= hit.y() && my < hit.y() + hit.h()) {
                    if (TxAdminScreen.this.inputBox != null) {
                        TxAdminScreen.this.inputBox.setFocused(false);
                    }
                    hit.action().run();
                    return;
                }
            }
        }

        @Override
        protected void extractWidgetRenderState(GuiGraphicsExtractor g, int mouseX, int mouseY, float partialTick) {
            listHits.clear();
            int x = this.getX();
            int y = this.getY();
            int w = this.getWidth();
            int h = this.getHeight();

            g.fill(x, y, x + w, y + h, COL_INPUT_BG);

            g.enableScissor(x, y, x + w, y + h);
            int ry = (int) Math.round(y + 4 - scrollOffset);
            for (RowSpec row : currentRows) {
                if (ry + ROW_H >= y && ry <= y + h) {
                    boolean rowHov = mouseX >= x + 4 && mouseX < x + w - 8 && mouseY >= ry && mouseY < ry + ROW_H;
                    g.fill(x + 4, ry, x + w - 8, ry + ROW_H, rowHov ? 0xFF261D17 : COL_ROW_BG);

                    int bx = x + w - 12;
                    List<BtnSpec> btns = row.buttons();
                    for (int b = btns.size() - 1; b >= 0; b--) {
                        BtnSpec spec = btns.get(b);
                        int bw = Math.max(24, TxAdminScreen.this.font.width(spec.label()) + 10);
                        bx -= bw;
                        int by = ry + 6;
                        boolean visibleInClip = (by >= y && by + 18 <= y + h);
                        boolean hov = visibleInClip && mouseX >= bx && mouseX < bx + bw && mouseY >= by && mouseY < by + 18;
                        int bg;
                        if (spec.style() == 1) {
                            bg = hov ? COL_GOLD_HOVER : COL_GOLD_BTN;
                        } else if (spec.style() == 2) {
                            bg = hov ? COL_GREEN_HOVER : COL_GREEN;
                        } else if (spec.style() == 3) {
                            bg = hov ? COL_RED_HOVER : COL_RED;
                        } else {
                            bg = hov ? 0xFF3A2D23 : COL_SURFACE_ALT;
                        }
                        g.fill(bx, by, bx + bw, by + 18, bg);
                        int tx = bx + (bw - TxAdminScreen.this.font.width(spec.label())) / 2;
                        g.text(TxAdminScreen.this.font, spec.label(), tx, by + 5, COL_TEXT, false);
                        if (visibleInClip) {
                            listHits.add(new HitBox(bx, by, bw, 18, spec.action()));
                        }
                        bx -= 3;
                    }

                    int maxTextW = Math.max(48, bx - (x + 14));
                    String clippedTitle = TxAdminScreen.this.font.plainSubstrByWidth(row.title(), maxTextW);
                    String clippedSub = TxAdminScreen.this.font.plainSubstrByWidth(row.subtitle(), maxTextW);
                    g.text(TxAdminScreen.this.font, clippedTitle, x + 10, ry + 6, COL_TEXT, false);
                    g.text(TxAdminScreen.this.font, clippedSub, x + 10, ry + 16, COL_MUTED, false);
                }
                ry += ROW_PITCH;
            }
            g.disableScissor();

            int totalH = currentRows.size() * ROW_PITCH;
            if (totalH > h) {
                int sbX = x + w - 4;
                int thumbH = Math.max(16, (int) ((double) h * h / totalH));
                int maxScroll = totalH - h + 8;
                int thumbY = y + 3 + (int) ((scrollOffset / maxScroll) * (h - 6 - thumbH));
                g.fill(sbX, y + 3, sbX + 2, y + h - 3, 0x33000000);
                g.fill(sbX, thumbY, sbX + 2, thumbY + thumbH, COL_ACCENT);
            }
        }

        @Override
        protected void updateWidgetNarration(NarrationElementOutput narration) {
            this.defaultButtonNarrationText(narration);
        }
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

cp_jars = [MC_PATCHED, NF_UNIV]
for pattern in [
    "net/neoforged/**/*.jar",
    "com/mojang/**/*.jar",
    "io/netty/**/*.jar",
    "org/joml/**/*.jar",
    "com/google/guava/**/*.jar",
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

jar_name = "nest_txadmin-1.0.0-neoforge-26.3.jar"
out_jar = os.path.join(WORK, jar_name)
with zipfile.ZipFile(out_jar, "w", zipfile.ZIP_DEFLATED) as zf:
    for root_dir, _, files in os.walk(CLS_DIR):
        for fn in files:
            full_p = os.path.join(root_dir, fn)
            rel_p = os.path.relpath(full_p, CLS_DIR).replace(os.sep, "/")
            zf.write(full_p, rel_p)

targets = [
    os.path.join(r"C:\Users\katen\Desktop\TheNest VanillaEditon Server\mods", jar_name),
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
