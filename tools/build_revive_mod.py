import glob
import os
import shutil
import subprocess
import zipfile

ROOT = r"c:\Users\katen\Desktop\Minecraft Modpack"
WORK = os.path.join(ROOT, "scratch", "revive_build")
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

MODS_TOML = """modLoader = "javafml"
loaderVersion = "[1,)"
license = "All Rights Reserved"

[[mods]]
modId = "nest_revive"
version = "1.0.0"
displayName = "The Nest Revive"
authors = "The Nest"
description = '''Players enter a wounded bleedout state on the ground before dying, allowing teammates to revive them in danger before the Corpse mod spawns their corpse.'''

[[dependencies.nest_revive]]
modId = "neoforge"
type = "required"
versionRange = "[26.3,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.nest_revive]]
modId = "minecraft"
type = "required"
versionRange = "[26.3]"
ordering = "NONE"
side = "BOTH"
"""

FILES["com/thenest/revive/NestReviveMod.java"] = r"""package com.thenest.revive;

import com.thenest.revive.client.ReviveClient;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLEnvironment;
import net.neoforged.neoforge.network.event.RegisterPayloadHandlersEvent;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

@Mod(NestReviveMod.MODID)
public class NestReviveMod {
    public static final String MODID = "nest_revive";

    public NestReviveMod(IEventBus modBus) {
        modBus.addListener(this::onRegisterPayloads);
        ReviveServerManager.registerEvents();
        if (FMLEnvironment.getDist() == Dist.CLIENT) {
            ReviveClient.init();
        }
    }

    private void onRegisterPayloads(RegisterPayloadHandlersEvent event) {
        PayloadRegistrar reg = event.registrar("1");
        SyncDownedPayload.registerInto(reg);
        ReviveHoldPayload.registerInto(reg);
    }
}
"""

FILES["com/thenest/revive/SyncDownedPayload.java"] = r"""package com.thenest.revive;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record SyncDownedPayload(String encoded) implements CustomPacketPayload {

    public interface ClientHandler {
        void handleSync(String encoded);
    }

    private static volatile ClientHandler clientHandler;

    public static void setClientHandler(ClientHandler handler) {
        clientHandler = handler;
    }

    public static final CustomPacketPayload.Type<SyncDownedPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestReviveMod.MODID, "sync_downed"));

    public static final StreamCodec<RegistryFriendlyByteBuf, SyncDownedPayload> STREAM_CODEC =
            StreamCodec.of(SyncDownedPayload::encode, SyncDownedPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, SyncDownedPayload p) {
        buf.writeUtf(p.encoded() != null ? p.encoded() : "", 16384);
    }

    private static SyncDownedPayload decode(RegistryFriendlyByteBuf buf) {
        return new SyncDownedPayload(buf.readUtf(16384));
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToClient(TYPE, STREAM_CODEC, SyncDownedPayload::handleClient);
    }

    private static void handleClient(SyncDownedPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            ClientHandler h = clientHandler;
            if (h != null) {
                h.handleSync(payload.encoded());
            }
        });
    }
}
"""

FILES["com/thenest/revive/ReviveHoldPayload.java"] = r"""package com.thenest.revive;

import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerPlayer;
import net.neoforged.neoforge.network.handling.IPayloadContext;
import net.neoforged.neoforge.network.registration.PayloadRegistrar;

public record ReviveHoldPayload(boolean useHeld, boolean giveUpHeld) implements CustomPacketPayload {

    public static final CustomPacketPayload.Type<ReviveHoldPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestReviveMod.MODID, "revive_hold"));

    public static final StreamCodec<RegistryFriendlyByteBuf, ReviveHoldPayload> STREAM_CODEC =
            StreamCodec.of(ReviveHoldPayload::encode, ReviveHoldPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, ReviveHoldPayload p) {
        buf.writeBoolean(p.useHeld());
        buf.writeBoolean(p.giveUpHeld());
    }

    private static ReviveHoldPayload decode(RegistryFriendlyByteBuf buf) {
        return new ReviveHoldPayload(buf.readBoolean(), buf.readBoolean());
    }

    @Override
    public CustomPacketPayload.Type<? extends CustomPacketPayload> type() {
        return TYPE;
    }

    public static void registerInto(PayloadRegistrar reg) {
        reg.playToServer(TYPE, STREAM_CODEC, ReviveHoldPayload::handleServer);
    }

    private static void handleServer(ReviveHoldPayload payload, IPayloadContext ctx) {
        ctx.enqueueWork(() -> {
            if (ctx.player() instanceof ServerPlayer sp) {
                ReviveServerManager.setHoldFlags(sp.getUUID(), payload.useHeld(), payload.giveUpHeld());
            }
        });
    }
}
"""

FILES["com/thenest/revive/ReviveServerManager.java"] = r"""package com.thenest.revive;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.level.GameType;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.item.ItemTossEvent;
import net.neoforged.neoforge.event.entity.living.LivingChangeTargetEvent;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent;
import net.neoforged.neoforge.event.entity.player.AttackEntityEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;

public final class ReviveServerManager {
    private static final class DownedEntry {
        final UUID playerId;
        final String playerName;
        final DamageSource fatalSource;
        int bleedoutTicks;
        final int maxBleedoutTicks;
        int reviveTicks;
        final int maxReviveTicks;
        int graceTicks;
        int giveUpTicks;
        String activeReviverName = "";

        DownedEntry(UUID playerId, String playerName, DamageSource fatalSource, int maxBleedoutTicks, int maxReviveTicks, int graceTicks) {
            this.playerId = playerId;
            this.playerName = playerName;
            this.fatalSource = fatalSource;
            this.bleedoutTicks = maxBleedoutTicks;
            this.maxBleedoutTicks = maxBleedoutTicks;
            this.reviveTicks = 0;
            this.maxReviveTicks = maxReviveTicks;
            this.graceTicks = graceTicks;
            this.giveUpTicks = 0;
        }
    }

    private static final Map<UUID, DownedEntry> DOWNED = new ConcurrentHashMap<>();
    private static final Set<UUID> BYPASS_DEATH = ConcurrentHashMap.newKeySet();
    private static final Set<UUID> USE_HOLDING = ConcurrentHashMap.newKeySet();
    private static final Set<UUID> GIVEUP_HOLDING = ConcurrentHashMap.newKeySet();

    private static volatile int cfgBleedoutTicks = 45 * 20;
    private static volatile int cfgReviveTicks = 70;
    private static volatile double cfgReviveRange = 3.2;
    private static volatile int cfgGraceTicks = 30;
    private static volatile int cfgDamagePenaltyTicks = 60;
    private static volatile float cfgReviveHealth = 6.0F;
    private static volatile int tickCounter = 0;
    private static volatile boolean configLoaded = false;

    private ReviveServerManager() {}

    public static void registerEvents() {
        ensureConfigLoaded();
        NeoForge.EVENT_BUS.addListener(EventPriority.HIGH, ReviveServerManager::onLivingDeath);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onIncomingDamage);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onMobChangeTarget);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onAttackEntity);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onLeftClickBlock);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onRightClickBlock);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onRightClickItem);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onEntityInteract);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onItemToss);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onPlayerJoin);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onPlayerLogout);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onServerTick);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onRegisterCommands);
    }

    private static synchronized void ensureConfigLoaded() {
        if (configLoaded) return;
        configLoaded = true;
        Path p = Paths.get("config", "nest_revive.properties");
        try {
            if (!Files.exists(p)) {
                Files.createDirectories(p.getParent());
                String def = "# The Nest Revive Configuration\n"
                        + "bleedout_seconds=45\n"
                        + "revive_seconds=3.5\n"
                        + "revive_range=3.2\n"
                        + "post_down_grace_seconds=1.5\n"
                        + "damage_bleed_penalty_seconds=3.0\n"
                        + "revive_health=6.0\n";
                Files.writeString(p, def, StandardCharsets.UTF_8);
            } else {
                Properties props = new Properties();
                try (var in = Files.newInputStream(p)) {
                    props.load(in);
                }
                cfgBleedoutTicks = Math.max(100, (int) Math.round(Double.parseDouble(props.getProperty("bleedout_seconds", "45")) * 20.0));
                cfgReviveTicks = Math.max(20, (int) Math.round(Double.parseDouble(props.getProperty("revive_seconds", "3.5")) * 20.0));
                cfgReviveRange = Math.max(1.8, Double.parseDouble(props.getProperty("revive_range", "3.2")));
                cfgGraceTicks = Math.max(10, (int) Math.round(Double.parseDouble(props.getProperty("post_down_grace_seconds", "1.5")) * 20.0));
                cfgDamagePenaltyTicks = Math.max(0, (int) Math.round(Double.parseDouble(props.getProperty("damage_bleed_penalty_seconds", "3.0")) * 20.0));
                cfgReviveHealth = Math.max(2.0F, Math.min(20.0F, Float.parseFloat(props.getProperty("revive_health", "6.0"))));
            }
        } catch (Exception ignored) {}
    }

    public static void setHoldFlags(UUID uuid, boolean useHeld, boolean giveUpHeld) {
        if (useHeld) USE_HOLDING.add(uuid);
        else USE_HOLDING.remove(uuid);
        if (giveUpHeld) GIVEUP_HOLDING.add(uuid);
        else GIVEUP_HOLDING.remove(uuid);
    }

    public static boolean isDowned(UUID uuid) {
        return DOWNED.containsKey(uuid);
    }

    private static void onLivingDeath(LivingDeathEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer sp)) return;
        UUID id = sp.getUUID();
        if (BYPASS_DEATH.remove(id)) {
            return; // Real death allowed -> Corpse mod receives LivingDeathEvent cleanly
        }
        GameType gm = sp.gameMode();
        if (gm == GameType.CREATIVE || gm == GameType.SPECTATOR) {
            return;
        }
        DamageSource src = event.getSource();
        if (src.is(DamageTypes.GENERIC_KILL)) {
            cleanupDownedState(sp);
            return;
        }
        if (src.is(DamageTypes.FELL_OUT_OF_WORLD) && sp.getY() < sp.level().getMinY() - 8) {
            cleanupDownedState(sp);
            return;
        }
        if (DOWNED.containsKey(id)) {
            event.setCanceled(true);
            sp.setHealth(1.0F);
            return;
        }

        // Intercept lethal hit -> put player into Wounded/Downed state before Corpse spawns
        event.setCanceled(true);
        enterDownedState(sp, src);
    }

    private static void enterDownedState(ServerPlayer sp, DamageSource src) {
        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return;
        ensureConfigLoaded();

        sp.setHealth(1.0F);
        sp.clearFire();
        sp.setAirSupply(sp.getMaxAirSupply());
        sp.stopRiding();
        sp.setSprinting(false);
        sp.setForcedPose(Pose.SWIMMING);
        sp.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, cfgBleedoutTicks + 200, 3, true, false, false));
        sp.addEffect(new MobEffectInstance(MobEffects.MINING_FATIGUE, cfgBleedoutTicks + 200, 4, true, false, false));

        // Drop mob aggro so a lone survivor can fight & rescue them
        try {
            for (Mob mob : sp.level().getEntitiesOfClass(Mob.class, sp.getBoundingBox().inflate(32.0))) {
                if (mob.getTarget() == sp) {
                    mob.setTarget(null);
                }
            }
        } catch (Throwable ignored) {}

        DownedEntry entry = new DownedEntry(
                sp.getUUID(),
                sp.getGameProfile().name(),
                src,
                cfgBleedoutTicks,
                cfgReviveTicks,
                cfgGraceTicks
        );
        DOWNED.put(sp.getUUID(), entry);

        sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 1.0F, 0.85F);
        if (sp.level() instanceof ServerLevel sl) {
            sl.sendParticles(ParticleTypes.CRIMSON_SPORE, sp.getX(), sp.getY() + 0.3, sp.getZ(), 18, 0.4, 0.2, 0.4, 0.02);
        }

        String displayName = sp.getDisplayName().getString();
        Component msg = Component.literal("§c[The Nest] §e" + displayName + " §cis wounded on the ground! Hold §6[Shift] §cor §6[Right-Click] §cnearby to revive (§e"
                + (cfgBleedoutTicks / 20) + "s§c)!");
        for (ServerPlayer other : srv.getPlayerList().getPlayers()) {
            other.sendSystemMessage(msg);
        }
        syncAllClients(srv);
    }

    private static void onIncomingDamage(LivingIncomingDamageEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer sp)) return;
        UUID id = sp.getUUID();
        if (BYPASS_DEATH.contains(id)) return;
        DownedEntry entry = DOWNED.get(id);
        if (entry == null) return;

        if (event.getSource().is(DamageTypes.GENERIC_KILL)) return;

        event.setCanceled(true);
        if (entry.graceTicks > 0 || event.getAmount() <= 0.0F) {
            return;
        }
        entry.graceTicks = 10; // 0.5s i-frames while wounded
        entry.bleedoutTicks -= cfgDamagePenaltyTicks;
        sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 0.7F, 1.3F);
        if (entry.bleedoutTicks <= 0) {
            finishBleedout(sp);
        } else {
            syncAllClients(sp.level().getServer());
        }
    }

    private static void onMobChangeTarget(LivingChangeTargetEvent event) {
        if (event.getNewAboutToBeSetTarget() instanceof ServerPlayer sp && DOWNED.containsKey(sp.getUUID())) {
            event.setNewAboutToBeSetTarget(null);
            event.setCanceled(true);
        }
    }

    private static void onAttackEntity(AttackEntityEvent event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onLeftClickBlock(PlayerInteractEvent.LeftClickBlock event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onRightClickBlock(PlayerInteractEvent.RightClickBlock event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onRightClickItem(PlayerInteractEvent.RightClickItem event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onEntityInteract(PlayerInteractEvent.EntityInteract event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
            return;
        }
        if (event.getEntity() instanceof ServerPlayer reviver && event.getTarget() instanceof ServerPlayer target) {
            if (DOWNED.containsKey(target.getUUID())) {
                USE_HOLDING.add(reviver.getUUID());
            }
        }
    }

    private static void onItemToss(ItemTossEvent event) {
        if (DOWNED.containsKey(event.getPlayer().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onPlayerJoin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer sp) {
            syncToPlayer(sp, sp.level().getServer());
        }
    }

    private static void onPlayerLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer sp) {
            UUID id = sp.getUUID();
            USE_HOLDING.remove(id);
            GIVEUP_HOLDING.remove(id);
            if (DOWNED.containsKey(id)) {
                finishBleedout(sp);
            }
        }
    }

    private static void cleanupDownedState(ServerPlayer sp) {
        DOWNED.remove(sp.getUUID());
        GIVEUP_HOLDING.remove(sp.getUUID());
        sp.setForcedPose(null);
        sp.removeEffect(MobEffects.SLOWNESS);
        sp.removeEffect(MobEffects.MINING_FATIGUE);
    }

    private static void completeRevive(MinecraftServer srv, ServerPlayer sp, ServerPlayer reviver) {
        cleanupDownedState(sp);
        sp.clearFire();
        sp.setHealth(Math.min(sp.getMaxHealth(), cfgReviveHealth));
        sp.addEffect(new MobEffectInstance(MobEffects.REGENERATION, 80, 1, false, true, true));
        sp.addEffect(new MobEffectInstance(MobEffects.ABSORPTION, 160, 0, false, true, true));
        sp.addEffect(new MobEffectInstance(MobEffects.RESISTANCE, 60, 1, false, true, true));
        sp.addEffect(new MobEffectInstance(MobEffects.FIRE_RESISTANCE, 100, 0, false, false, true));

        sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.TOTEM_USE, SoundSource.PLAYERS, 0.85F, 1.15F);
        if (sp.level() instanceof ServerLevel sl) {
            sl.sendParticles(ParticleTypes.HEART, sp.getX(), sp.getY() + 1.0, sp.getZ(), 14, 0.45, 0.45, 0.45, 0.05);
            sl.sendParticles(ParticleTypes.TOTEM_OF_UNDYING, sp.getX(), sp.getY() + 0.9, sp.getZ(), 18, 0.4, 0.5, 0.4, 0.12);
        }

        String revName = reviver != null ? reviver.getDisplayName().getString() : "Admin";
        String vicName = sp.getDisplayName().getString();
        Component msg = Component.literal("§a[The Nest] §e" + revName + " §arevived §e" + vicName + "§a!");
        for (ServerPlayer other : srv.getPlayerList().getPlayers()) {
            other.sendSystemMessage(msg);
        }
        syncAllClients(srv);
    }

    private static void finishBleedout(ServerPlayer sp) {
        MinecraftServer srv = sp.level().getServer();
        DownedEntry entry = DOWNED.remove(sp.getUUID());
        cleanupDownedState(sp);
        if (entry == null) return;

        BYPASS_DEATH.add(sp.getUUID());
        try {
            DamageSource src = entry.fatalSource != null ? entry.fatalSource : sp.damageSources().generic();
            if (sp.level() instanceof ServerLevel sl) {
                sp.hurtServer(sl, src, Float.MAX_VALUE);
            } else {
                sp.setHealth(0.0F);
                sp.die(src);
            }
        } catch (Throwable t) {
            BYPASS_DEATH.remove(sp.getUUID());
            sp.setHealth(0.0F);
        }
        if (srv != null) {
            syncAllClients(srv);
        }
    }

    private static void onServerTick(ServerTickEvent.Post event) {
        MinecraftServer srv = event.getServer();
        tickCounter++;
        if (DOWNED.isEmpty()) return;

        boolean dirty = false;
        List<ServerPlayer> bleedoutDeaths = new ArrayList<>();
        List<ServerPlayer[]> revivals = new ArrayList<>();

        for (DownedEntry entry : DOWNED.values()) {
            ServerPlayer victim = srv.getPlayerList().getPlayer(entry.playerId);
            if (victim == null) continue;

            if (entry.graceTicks > 0) entry.graceTicks--;
            if (victim.getHealth() > 1.0F) victim.setHealth(1.0F);
            victim.setSprinting(false);
            if (victim.getForcedPose() != Pose.SWIMMING) {
                victim.setForcedPose(Pose.SWIMMING);
            }
            if (victim.getRemainingFireTicks() > 0 && !victim.isInLava()) {
                victim.clearFire();
            }

            // Look for closest healthy reviver holding Shift OR Right-Click within range
            ServerPlayer reviver = null;
            double bestDistSq = cfgReviveRange * cfgReviveRange;
            for (ServerPlayer candidate : srv.getPlayerList().getPlayers()) {
                if (candidate.getUUID().equals(victim.getUUID())) continue;
                if (DOWNED.containsKey(candidate.getUUID())) continue;
                if (!candidate.isAlive() || candidate.gameMode() == GameType.SPECTATOR) continue;
                if (candidate.level() != victim.level()) continue;

                boolean holdingAction = candidate.isShiftKeyDown() || USE_HOLDING.contains(candidate.getUUID());
                if (!holdingAction) continue;

                double dSq = candidate.distanceToSqr(victim);
                if (dSq <= bestDistSq) {
                    bestDistSq = dSq;
                    reviver = candidate;
                }
            }

            if (reviver != null) {
                entry.activeReviverName = reviver.getGameProfile().name();
                entry.reviveTicks++;
                entry.giveUpTicks = 0;
                if (tickCounter % 10 == 0) {
                    victim.level().playSound(null, victim.getX(), victim.getY(), victim.getZ(),
                            SoundEvents.WARDEN_HEARTBEAT, SoundSource.PLAYERS, 0.55F, 1.0F + (entry.reviveTicks / (float) entry.maxReviveTicks) * 0.45F);
                    if (victim.level() instanceof ServerLevel sl) {
                        sl.sendParticles(ParticleTypes.HEART, victim.getX(), victim.getY() + 0.65, victim.getZ(), 2, 0.25, 0.2, 0.25, 0.01);
                    }
                }
                if (entry.reviveTicks >= entry.maxReviveTicks) {
                    revivals.add(new ServerPlayer[] {victim, reviver});
                }
                dirty = true;
            } else {
                if (!entry.activeReviverName.isEmpty()) {
                    entry.activeReviverName = "";
                    dirty = true;
                }
                if (entry.reviveTicks > 0) {
                    entry.reviveTicks = Math.max(0, entry.reviveTicks - 2);
                    dirty = true;
                }

                // Check Give Up hold (Jump / Spacebar for 1.5s)
                if (GIVEUP_HOLDING.contains(victim.getUUID())) {
                    entry.giveUpTicks++;
                    if (entry.giveUpTicks >= 30) {
                        bleedoutDeaths.add(victim);
                        continue;
                    }
                } else {
                    entry.giveUpTicks = 0;
                }

                entry.bleedoutTicks--;
                if (tickCounter % 20 == 0) {
                    if (victim.level() instanceof ServerLevel sl) {
                        sl.sendParticles(ParticleTypes.CRIMSON_SPORE, victim.getX(), victim.getY() + 0.25, victim.getZ(), 4, 0.25, 0.1, 0.25, 0.01);
                    }
                    dirty = true;
                }
                if (entry.bleedoutTicks <= 0) {
                    bleedoutDeaths.add(victim);
                }
            }
        }

        for (ServerPlayer[] pair : revivals) {
            completeRevive(srv, pair[0], pair[1]);
            dirty = false;
        }
        for (ServerPlayer dead : bleedoutDeaths) {
            finishBleedout(dead);
            dirty = false;
        }
        if (dirty || (tickCounter % 4 == 0 && !DOWNED.isEmpty())) {
            syncAllClients(srv);
        }
    }

    private static String encodeAll(MinecraftServer srv) {
        if (DOWNED.isEmpty()) return "";
        StringBuilder sb = new StringBuilder();
        for (DownedEntry entry : DOWNED.values()) {
            ServerPlayer sp = srv.getPlayerList().getPlayer(entry.playerId);
            if (sp == null) continue;
            if (sb.length() > 0) sb.append("\n");
            String dim = sp.level().dimension().identifier().toString();
            sb.append(entry.playerId.toString()).append("|")
                    .append(clean(entry.playerName)).append("|")
                    .append(clean(dim)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.2f", sp.getX())).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.2f", sp.getY())).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.2f", sp.getZ())).append("|")
                    .append(entry.bleedoutTicks).append("|")
                    .append(entry.maxBleedoutTicks).append("|")
                    .append(entry.reviveTicks).append("|")
                    .append(entry.maxReviveTicks).append("|")
                    .append(clean(entry.activeReviverName));
        }
        return sb.toString();
    }

    private static String clean(String s) {
        return s == null ? "" : s.replace("|", "").replace("\n", "").replace("\r", "");
    }

    public static void syncAllClients(MinecraftServer srv) {
        if (srv == null) return;
        SyncDownedPayload pkt = new SyncDownedPayload(encodeAll(srv));
        for (ServerPlayer sp : srv.getPlayerList().getPlayers()) {
            try {
                PacketDistributor.sendToPlayer(sp, pkt);
            } catch (Throwable ignored) {}
        }
    }

    public static void syncToPlayer(ServerPlayer sp, MinecraftServer srv) {
        if (sp == null || srv == null) return;
        try {
            PacketDistributor.sendToPlayer(sp, new SyncDownedPayload(encodeAll(srv)));
        } catch (Throwable ignored) {}
    }

    private static void onRegisterCommands(RegisterCommandsEvent event) {
        CommandDispatcher<CommandSourceStack> d = event.getDispatcher();
        d.register(Commands.literal("revive")
                .requires(src -> src.permissions() == PermissionSet.ALL_PERMISSIONS
                        || (src.getPlayer() != null && src.getServer().getPlayerList().isOp(src.getPlayer().nameAndId()))
                        || (src.getPlayer() != null && src.getPlayer().canUseGameMasterBlocks()))
                .executes(ctx -> {
                    ServerPlayer sp = ctx.getSource().getPlayerOrException();
                    if (!DOWNED.containsKey(sp.getUUID())) {
                        ctx.getSource().sendSuccess(() -> Component.literal("§e[The Nest] You are not wounded."), false);
                        return 0;
                    }
                    completeRevive(ctx.getSource().getServer(), sp, sp);
                    return 1;
                })
                .then(Commands.argument("target", StringArgumentType.word())
                        .executes(ctx -> {
                            String tgt = StringArgumentType.getString(ctx, "target");
                            MinecraftServer srv = ctx.getSource().getServer();
                            ServerPlayer tp = srv.getPlayerList().getPlayerByName(tgt);
                            if (tp == null || !DOWNED.containsKey(tp.getUUID())) {
                                ctx.getSource().sendFailure(Component.literal("§c[The Nest] Player '" + tgt + "' is not currently wounded."));
                                return 0;
                            }
                            completeRevive(srv, tp, ctx.getSource().getPlayer());
                            return 1;
                        })));
    }
}
"""

FILES["com/thenest/revive/client/ReviveClient.java"] = r"""package com.thenest.revive.client;

import com.thenest.revive.ReviveHoldPayload;
import com.thenest.revive.SyncDownedPayload;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.player.ClientInput;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.player.Input;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.MovementInputUpdateEvent;
import net.neoforged.neoforge.client.event.RenderGuiEvent;
import net.neoforged.neoforge.client.network.ClientPacketDistributor;
import net.neoforged.neoforge.common.NeoForge;

public final class ReviveClient {
    public record DownedView(
            String uuid,
            String name,
            String dimension,
            double x,
            double y,
            double z,
            int bleedTicks,
            int maxBleedTicks,
            int reviveTicks,
            int maxReviveTicks,
            String reviverName
    ) {}

    private static volatile List<DownedView> DOWNED_LIST = List.of();
    private static volatile boolean wasSelfDowned = false;
    private static volatile boolean lastUseHeld = false;
    private static volatile boolean lastGiveUpHeld = false;
    private static volatile int localGiveUpTicks = 0;

    private ReviveClient() {}

    public static void init() {
        SyncDownedPayload.setClientHandler(ReviveClient::onSync);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onClientTick);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onMovementInput);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onRenderGui);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onLogout);
    }

    private static void onLogout(ClientPlayerNetworkEvent.LoggingOut event) {
        DOWNED_LIST = List.of();
        wasSelfDowned = false;
        lastUseHeld = false;
        lastGiveUpHeld = false;
        localGiveUpTicks = 0;
    }

    private static void onSync(String encoded) {
        List<DownedView> next = new ArrayList<>();
        if (encoded != null && !encoded.isBlank()) {
            for (String line : encoded.split("\n")) {
                String[] p = line.split("\\|", -1);
                if (p.length >= 11) {
                    next.add(new DownedView(
                            p[0],
                            p[1],
                            p[2],
                            parseDouble(p[3], 0.0),
                            parseDouble(p[4], 0.0),
                            parseDouble(p[5], 0.0),
                            parseInt(p[6], 0),
                            Math.max(1, parseInt(p[7], 900)),
                            parseInt(p[8], 0),
                            Math.max(1, parseInt(p[9], 70)),
                            p[10]
                    ));
                }
            }
        }
        DOWNED_LIST = next;
    }

    private static int parseInt(String s, int def) {
        try { return Integer.parseInt(s.trim()); } catch (Exception e) { return def; }
    }

    private static double parseDouble(String s, double def) {
        try { return Double.parseDouble(s.trim()); } catch (Exception e) { return def; }
    }

    private static DownedView findSelf(LocalPlayer me) {
        if (me == null) return null;
        String myId = me.getUUID().toString();
        for (DownedView v : DOWNED_LIST) {
            if (myId.equals(v.uuid())) return v;
        }
        return null;
    }

    private static void onClientTick(ClientTickEvent.Post event) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer me = mc.player;
        if (me == null || mc.getConnection() == null) return;

        DownedView self = findSelf(me);
        if (self != null) {
            wasSelfDowned = true;
            me.setForcedPose(Pose.SWIMMING);
            me.setSprinting(false);
        } else if (wasSelfDowned) {
            wasSelfDowned = false;
            me.setForcedPose(null);
        }

        boolean useDown = (self == null && !DOWNED_LIST.isEmpty() && mc.isWindowActive() && mc.options.keyUse.isDown());
        boolean giveUpDown = (self != null && mc.isWindowActive() && mc.options.keyJump.isDown());

        if (giveUpDown) {
            localGiveUpTicks = Math.min(30, localGiveUpTicks + 1);
        } else {
            localGiveUpTicks = 0;
        }

        if (useDown != lastUseHeld || giveUpDown != lastGiveUpHeld) {
            lastUseHeld = useDown;
            lastGiveUpHeld = giveUpDown;
            try {
                ClientPacketDistributor.sendToServer(new ReviveHoldPayload(useDown, giveUpDown));
            } catch (Throwable ignored) {}
        }
    }

    private static void onMovementInput(MovementInputUpdateEvent event) {
        if (!(event.getEntity() instanceof LocalPlayer me)) return;
        if (findSelf(me) == null) return;
        ClientInput ci = event.getInput();
        Input k = ci.keyPresses;
        ci.keyPresses = new Input(k.forward(), k.backward(), k.left(), k.right(), false, false, false);
        me.setSprinting(false);
    }

    private static void onRenderGui(RenderGuiEvent.Post event) {
        List<DownedView> list = DOWNED_LIST;
        if (list.isEmpty()) return;

        Minecraft mc = Minecraft.getInstance();
        LocalPlayer me = mc.player;
        if (me == null) return;

        GuiGraphicsExtractor g = event.getGuiGraphics();
        int sw = mc.getWindow().getGuiScaledWidth();
        int sh = mc.getWindow().getGuiScaledHeight();
        DownedView self = findSelf(me);

        if (self != null) {
            int bw = 216;
            int bh = 44;
            int bx = (sw - bw) / 2;
            int by = sh - 98;
            boolean reviving = self.reviveTicks() > 0 && !self.reviverName().isEmpty();
            boolean urgent = !reviving && self.bleedTicks() <= 200; // < 10s

            int accent = reviving ? 0xFF4ADE80 : (localGiveUpTicks > 0 ? 0xFFE09F3E : 0xFFE84848);
            int border = 0xFF3B2D21;

            // Sleek warm espresso card + 1px hairline border + 3px left status bar
            g.fill(bx, by, bx + bw, by + bh, 0xE8130E0B);
            g.fill(bx, by, bx + bw, by + 1, border);
            g.fill(bx, by + bh - 1, bx + bw, by + bh, border);
            g.fill(bx, by, bx + 1, by + bh, border);
            g.fill(bx + bw - 1, by, bx + bw, by + bh, border);
            g.fill(bx, by, bx + 3, by + bh, accent);

            String leftTitle;
            String rightStat;
            double ratio;
            if (reviving) {
                int pct = Math.min(100, (self.reviveTicks() * 100) / self.maxReviveTicks());
                leftTitle = "REVIVING · " + self.reviverName();
                rightStat = pct + "%";
                ratio = Math.min(1.0, self.reviveTicks() / (double) self.maxReviveTicks());
            } else {
                leftTitle = "WOUNDED";
                rightStat = String.format(Locale.ROOT, "%.1fs", Math.max(0, self.bleedTicks()) / 20.0);
                ratio = Math.max(0.0, Math.min(1.0, self.bleedTicks() / (double) self.maxBleedTicks()));
            }
            int statW = mc.font.width(rightStat);
            String clippedLeft = mc.font.plainSubstrByWidth(leftTitle, bw - statW - 26);
            int leftCol = reviving ? 0xFF4ADE80 : (urgent ? 0xFFFF7A7A : 0xFFF5ECE0);
            int statCol = reviving ? 0xFF6BC482 : (urgent ? 0xFFFF6464 : 0xFFE09F3E);
            g.text(mc.font, clippedLeft, bx + 10, by + 6, leftCol, false);
            g.text(mc.font, rightStat, bx + bw - 10 - statW, by + 6, statCol, false);

            // Layered bleedout / revive progress bar
            int barX = bx + 10;
            int barY = by + 18;
            int barW = bw - 20;
            g.fill(barX, barY, barX + barW, barY + 5, 0xFF241B15);
            int fillW = (int) Math.round(barW * ratio);
            if (fillW > 0) {
                int barCol = reviving ? 0xFF4ADE80 : 0xFFE05252;
                g.fill(barX, barY, barX + fillW, barY + 5, barCol);
                g.fill(barX + fillW - 1, barY, barX + fillW, barY + 5, 0x99FFFFFF);
            }

            // Clean Give Up row only
            if (localGiveUpTicks > 0) {
                int gp = Math.min(100, (localGiveUpTicks * 100) / 30);
                String gTxt = "Giving Up... " + gp + "%";
                g.text(mc.font, gTxt, bx + (bw - mc.font.width(gTxt)) / 2, by + 29, 0xFFE09F3E, false);
                int gFill = (int) Math.round((bw - 3) * (localGiveUpTicks / 30.0));
                if (gFill > 0) {
                    g.fill(bx + 3, by + bh - 3, bx + 3 + gFill, by + bh, 0xFFE09F3E);
                }
            } else {
                String gTxt = "Hold [SPACE] to Give Up";
                g.text(mc.font, gTxt, bx + (bw - mc.font.width(gTxt)) / 2, by + 29, 0xFFA89682, false);
            }
            return;
        }

        // Healthy player HUD: active revive bar OR compact downed alert
        String myName = me.getGameProfile().name();
        DownedView activeTarget = null;
        for (DownedView v : list) {
            if (myName.equalsIgnoreCase(v.reviverName())) {
                activeTarget = v;
                break;
            }
        }
        if (activeTarget != null) {
            int bw = 196;
            int bh = 32;
            int bx = (sw - bw) / 2;
            int by = sh - 90;
            int pct = Math.min(100, (activeTarget.reviveTicks() * 100) / activeTarget.maxReviveTicks());
            g.fill(bx, by, bx + bw, by + bh, 0xE8130E0B);
            g.fill(bx, by, bx + bw, by + 1, 0xFF3B2D21);
            g.fill(bx, by + bh - 1, bx + bw, by + bh, 0xFF3B2D21);
            g.fill(bx, by, bx + 3, by + bh, 0xFF4ADE80);
            String title = "REVIVING " + activeTarget.name();
            String pTxt = pct + "%";
            g.text(mc.font, mc.font.plainSubstrByWidth(title, bw - 44), bx + 10, by + 6, 0xFFF5ECE0, false);
            g.text(mc.font, pTxt, bx + bw - 10 - mc.font.width(pTxt), by + 6, 0xFF4ADE80, false);
            int barW = bw - 20;
            int fillW = (int) Math.round(barW * Math.min(1.0, activeTarget.reviveTicks() / (double) activeTarget.maxReviveTicks()));
            g.fill(bx + 10, by + 19, bx + 10 + barW, by + 24, 0xFF241B15);
            if (fillW > 0) g.fill(bx + 10, by + 19, bx + 10 + fillW, by + 24, 0xFF4ADE80);
        }

        String myDim = me.level().dimension().identifier().toString();
        int ay = 10;
        for (DownedView v : list) {
            if (!myDim.equals(v.dimension())) continue;
            double dx = v.x() - me.getX();
            double dy = v.y() - me.getY();
            double dz = v.z() - me.getZ();
            int dist = (int) Math.round(Math.sqrt(dx * dx + dy * dy + dz * dz));
            String secs = String.format(Locale.ROOT, "%.0fs", Math.max(0, v.bleedTicks()) / 20.0);
            String alert = "! " + v.name() + " DOWN · " + dist + "m · " + secs;
            int aw = mc.font.width(alert) + 14;
            int ax = sw - aw - 8;
            g.fill(ax, ay, ax + aw, ay + 16, 0xDD130E0B);
            g.fill(ax, ay, ax + 2, ay + 16, 0xFFE84848);
            g.text(mc.font, alert, ax + 7, ay + 4, 0xFFF5ECE0, false);
            ay += 19;
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
    print("JAVAC FAILED:\n", res.stdout, res.stderr)
    raise SystemExit(res.returncode)
print("JAVAC SUCCEEDED!")

out_jar = os.path.join(WORK, "nest_revive-1.0.0-neoforge-26.3.jar")
with zipfile.ZipFile(out_jar, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("META-INF/neoforge.mods.toml", MODS_TOML)
    for root_dir, _dirs, filenames in os.walk(CLS_DIR):
        for fn in filenames:
            full = os.path.join(root_dir, fn)
            rel = os.path.relpath(full, CLS_DIR).replace("\\", "/")
            zf.write(full, rel)

targets = [
    r"C:\Users\katen\Desktop\TheNest VanillaEditon Server\mods\nest_revive-1.0.0-neoforge-26.3.jar",
    r"C:\Users\katen\curseforge\minecraft\Instances\The Nest Vanilla Edition\mods\nest_revive-1.0.0-neoforge-26.3.jar",
    r"c:\Users\katen\Desktop\Minecraft Modpack\overrides\mods\nest_revive-1.0.0-neoforge-26.3.jar",
    os.path.expandvars(r"%LOCALAPPDATA%\TheNestVanilla\instance\mods\nest_revive-1.0.0-neoforge-26.3.jar"),
]
for dst in targets:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(out_jar, dst)
    print("Installed:", dst, os.path.getsize(dst), "bytes")
