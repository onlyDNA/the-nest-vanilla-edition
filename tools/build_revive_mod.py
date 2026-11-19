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

public record ReviveHoldPayload(boolean dragPressed, boolean carryPressed, boolean throwPressed, boolean giveUpHeld) implements CustomPacketPayload {

    public static final CustomPacketPayload.Type<ReviveHoldPayload> TYPE =
            new CustomPacketPayload.Type<>(Identifier.fromNamespaceAndPath(NestReviveMod.MODID, "revive_hold"));

    public static final StreamCodec<RegistryFriendlyByteBuf, ReviveHoldPayload> STREAM_CODEC =
            StreamCodec.of(ReviveHoldPayload::encode, ReviveHoldPayload::decode);

    private static void encode(RegistryFriendlyByteBuf buf, ReviveHoldPayload p) {
        buf.writeBoolean(p.dragPressed());
        buf.writeBoolean(p.carryPressed());
        buf.writeBoolean(p.throwPressed());
        buf.writeBoolean(p.giveUpHeld());
    }

    private static ReviveHoldPayload decode(RegistryFriendlyByteBuf buf) {
        return new ReviveHoldPayload(buf.readBoolean(), buf.readBoolean(), buf.readBoolean(), buf.readBoolean());
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
                ReviveServerManager.handleClientInput(sp, payload.dragPressed(), payload.carryPressed(), payload.throwPressed(), payload.giveUpHeld());
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
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ClientboundSetPassengersPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.permissions.PermissionSet;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageTypes;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.level.GameType;
import net.minecraft.world.phys.Vec3;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.entity.EntityMountEvent;
import net.neoforged.neoforge.event.entity.item.ItemTossEvent;
import net.neoforged.neoforge.event.entity.living.LivingChangeTargetEvent;
import net.neoforged.neoforge.event.entity.living.LivingDeathEvent;
import net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent;
import net.neoforged.neoforge.event.entity.living.LivingSwapItemsEvent;
import net.neoforged.neoforge.event.entity.player.AttackEntityEvent;
import net.neoforged.neoforge.event.entity.player.PlayerContainerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.entity.player.PlayerInteractEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.network.PacketDistributor;

public final class ReviveServerManager {
    public static final int MODE_NONE = 0;
    public static final int MODE_DRAG = 1;
    public static final int MODE_CARRY = 2;

    private static final Identifier NO_STEP_MOD_ID = Identifier.fromNamespaceAndPath(NestReviveMod.MODID, "no_step_up");
    private static final AttributeModifier NO_STEP_MOD = new AttributeModifier(NO_STEP_MOD_ID, -1.0, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL);
    private static final Identifier CARRY_SLOW_MOD_ID = Identifier.fromNamespaceAndPath(NestReviveMod.MODID, "carry_slow");
    private static final AttributeModifier CARRY_SLOW_MOD = new AttributeModifier(CARRY_SLOW_MOD_ID, -0.45, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL);

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
        UUID draggerId = null;
        String draggerName = "";
        int holdMode = MODE_NONE;
        double dragX = 0.0;
        double dragY = 0.0;
        double dragZ = 0.0;
        int throwSeq = 0;
        double throwVx = 0.0;
        double throwVy = 0.0;
        double throwVz = 0.0;
        int throwProtectTicks = 0;

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
    private static final Set<UUID> GIVEUP_HOLDING = ConcurrentHashMap.newKeySet();
    private static final Set<UUID> ALLOW_DISMOUNT = ConcurrentHashMap.newKeySet();

    private static volatile int cfgBleedoutTicks = 120 * 20;
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
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onEntityMount);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onSwapItems);
        NeoForge.EVENT_BUS.addListener(ReviveServerManager::onContainerOpen);
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
                        + "bleedout_seconds=120\n"
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
                cfgBleedoutTicks = Math.max(100, (int) Math.round(Double.parseDouble(props.getProperty("bleedout_seconds", "120")) * 20.0));
                cfgReviveTicks = Math.max(20, (int) Math.round(Double.parseDouble(props.getProperty("revive_seconds", "3.5")) * 20.0));
                cfgReviveRange = Math.max(1.8, Double.parseDouble(props.getProperty("revive_range", "3.2")));
                cfgGraceTicks = Math.max(10, (int) Math.round(Double.parseDouble(props.getProperty("post_down_grace_seconds", "1.5")) * 20.0));
                cfgDamagePenaltyTicks = Math.max(0, (int) Math.round(Double.parseDouble(props.getProperty("damage_bleed_penalty_seconds", "3.0")) * 20.0));
                cfgReviveHealth = Math.max(2.0F, Math.min(20.0F, Float.parseFloat(props.getProperty("revive_health", "6.0"))));
            }
        } catch (Exception ignored) {}
    }

    private static void setNoStepUp(ServerPlayer sp, boolean enabled) {
        if (sp == null) return;
        AttributeInstance attr = sp.getAttribute(Attributes.STEP_HEIGHT);
        if (attr == null) return;
        if (enabled) {
            if (!attr.hasModifier(NO_STEP_MOD_ID)) {
                attr.addTransientModifier(NO_STEP_MOD);
            }
        } else {
            attr.removeModifier(NO_STEP_MOD_ID);
        }
    }

    private static void setCarrySlow(ServerPlayer sp, boolean enabled) {
        if (sp == null) return;
        AttributeInstance attr = sp.getAttribute(Attributes.MOVEMENT_SPEED);
        if (attr == null) return;
        if (enabled) {
            if (!attr.hasModifier(CARRY_SLOW_MOD_ID)) {
                attr.addTransientModifier(CARRY_SLOW_MOD);
            }
        } else {
            attr.removeModifier(CARRY_SLOW_MOD_ID);
        }
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
        sp.setNoGravity(false);
        sp.closeContainer();
        releaseAnyDraggedBy(srv, sp.getUUID());
        setNoStepUp(sp, true);
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
        Component msg = Component.literal("§c[The Nest] §e" + displayName + " §cis wounded on the ground! Hold §6[Shift] §cto revive, §6[F] §cto drag, or §6[Shift+F] §cto carry (§e"
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

    private static void dismountCarried(ServerPlayer victim) {
        if (victim == null || !victim.isPassenger()) return;
        Entity vehicle = victim.getVehicle();
        ALLOW_DISMOUNT.add(victim.getUUID());
        try {
            victim.stopRiding();
        } finally {
            ALLOW_DISMOUNT.remove(victim.getUUID());
        }
        if (vehicle instanceof ServerPlayer dragger) {
            dragger.connection.send(new ClientboundSetPassengersPacket(dragger));
        }
    }

    private static void onEntityMount(EntityMountEvent event) {
        if (event.isDismounting() && event.getEntityMounting() instanceof ServerPlayer vic) {
            DownedEntry e = DOWNED.get(vic.getUUID());
            if (e != null && e.holdMode == MODE_CARRY && !ALLOW_DISMOUNT.contains(vic.getUUID())) {
                event.setCanceled(true);
            }
        }
    }

    private static void releaseAnyDraggedBy(MinecraftServer srv, UUID draggerId) {
        if (draggerId == null) return;
        for (DownedEntry e : DOWNED.values()) {
            if (draggerId.equals(e.draggerId)) {
                e.draggerId = null;
                e.draggerName = "";
                e.holdMode = MODE_NONE;
                if (srv != null) {
                    ServerPlayer vic = srv.getPlayerList().getPlayer(e.playerId);
                    if (vic != null) {
                        dismountCarried(vic);
                        vic.setNoGravity(false);
                    }
                }
            }
        }
        if (srv != null) {
            ServerPlayer dragger = srv.getPlayerList().getPlayer(draggerId);
            if (dragger != null) {
                setNoStepUp(dragger, false);
                setCarrySlow(dragger, false);
                dragger.removeEffect(MobEffects.SLOWNESS);
            }
        }
    }

    private static DownedEntry findHeldBy(UUID draggerId) {
        if (draggerId == null) return null;
        for (DownedEntry e : DOWNED.values()) {
            if (draggerId.equals(e.draggerId)) return e;
        }
        return null;
    }

    private static DownedEntry findNearestDowned(ServerPlayer actor, double maxRange) {
        double bestSq = maxRange * maxRange;
        DownedEntry best = null;
        for (DownedEntry e : DOWNED.values()) {
            if (e.playerId.equals(actor.getUUID())) continue;
            ServerPlayer target = actor.level().getServer().getPlayerList().getPlayer(e.playerId);
            if (target == null || target.level() != actor.level()) continue;
            double dSq = actor.distanceToSqr(target);
            if (dSq <= bestSq) {
                bestSq = dSq;
                best = e;
            }
        }
        return best;
    }

    public static void handleClientInput(ServerPlayer sp, boolean dragPressed, boolean carryPressed, boolean throwPressed, boolean giveUpHeld) {
        UUID actorId = sp.getUUID();
        if (giveUpHeld) GIVEUP_HOLDING.add(actorId);
        else GIVEUP_HOLDING.remove(actorId);

        MinecraftServer srv = sp.level().getServer();
        if (srv == null) return;
        if (DOWNED.containsKey(actorId)) return;
        if (!sp.isAlive() || sp.gameMode() == GameType.SPECTATOR) return;

        DownedEntry held = findHeldBy(actorId);
        boolean changed = false;

        if (carryPressed) {
            if (held != null && held.holdMode == MODE_CARRY) {
                // Put downed player gently on the ground in front of carrier
                ServerPlayer victim = srv.getPlayerList().getPlayer(held.playerId);
                Vec3 look = sp.getLookAngle();
                double lx = look.x, lz = look.z;
                double ll = Math.hypot(lx, lz);
                if (ll < 1e-4) { lx = 0.0; lz = 1.0; } else { lx /= ll; lz /= ll; }
                held.draggerId = null;
                held.draggerName = "";
                held.holdMode = MODE_NONE;
                setNoStepUp(sp, false);
                setCarrySlow(sp, false);
                sp.removeEffect(MobEffects.SLOWNESS);
                if (victim != null) {
                    dismountCarried(victim);
                    victim.noPhysics = false;
                    victim.setNoGravity(false);
                    double dropX = sp.getX() + lx * 1.0;
                    double dropZ = sp.getZ() + lz * 1.0;
                    BlockPos bp = BlockPos.containing(dropX, sp.getY() + 0.1, dropZ);
                    if (!sp.level().getBlockState(bp).isSolid()) {
                        victim.setPos(dropX, sp.getY(), dropZ);
                    } else {
                        victim.setPos(sp.getX(), sp.getY(), sp.getZ());
                    }
                    victim.setDeltaMovement(Vec3.ZERO);
                    victim.resetFallDistance();
                    victim.connection.resetPosition();
                }
                sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.ARMOR_EQUIP_LEATHER.value(), SoundSource.PLAYERS, 0.8F, 0.85F);
                changed = true;
            } else {
                DownedEntry targetEntry = held != null ? held : findNearestDowned(sp, cfgReviveRange + 0.8);
                if (targetEntry != null) {
                    releaseAnyDraggedBy(srv, actorId);
                    targetEntry.draggerId = actorId;
                    targetEntry.draggerName = sp.getGameProfile().name();
                    targetEntry.holdMode = MODE_CARRY;
                    targetEntry.reviveTicks = 0;
                    targetEntry.activeReviverName = "";
                    setNoStepUp(sp, false); // Carrier can climb blocks and look around!
                    setCarrySlow(sp, true);
                    sp.setSprinting(false);
                    sp.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 30, 2, true, false, false)); // Slowness III
                    ServerPlayer victim = srv.getPlayerList().getPlayer(targetEntry.playerId);
                    if (victim != null) {
                        victim.startRiding(sp, true, false);
                        sp.connection.send(new ClientboundSetPassengersPacket(sp));
                    }
                    sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.ARMOR_EQUIP_LEATHER.value(), SoundSource.PLAYERS, 0.9F, 1.15F);
                    changed = true;
                }
            }
        } else if (throwPressed && held != null && held.holdMode == MODE_CARRY) {
            ServerPlayer victim = srv.getPlayerList().getPlayer(held.playerId);
            Vec3 look = sp.getLookAngle();
            double lx = look.x, lz = look.z;
            double ll = Math.hypot(lx, lz);
            if (ll < 1e-4) { lx = 0.0; lz = 1.0; } else { lx /= ll; lz /= ll; }
            double startX = sp.getX() + lx * 0.65;
            double startY = sp.getY() + 1.35;
            double startZ = sp.getZ() + lz * 0.65;
            BlockPos launchPos = BlockPos.containing(startX, startY, startZ);
            if (sp.level().getBlockState(launchPos).isSolid()) {
                startX = sp.getX();
                startY = sp.getY() + 1.15;
                startZ = sp.getZ();
            }
            double vx = lx * 0.36;
            double vy = Math.max(0.36, Math.min(0.52, 0.40 + look.y * 0.14));
            double vz = lz * 0.36;

            held.draggerId = null;
            held.draggerName = "";
            held.holdMode = MODE_NONE;
            held.dragX = startX;
            held.dragY = startY;
            held.dragZ = startZ;
            held.throwSeq++;
            held.throwVx = vx;
            held.throwVy = vy;
            held.throwVz = vz;
            held.graceTicks = 30;
            held.throwProtectTicks = 25;

            setNoStepUp(sp, false);
            setCarrySlow(sp, false);
            sp.removeEffect(MobEffects.SLOWNESS);
            if (victim != null) {
                dismountCarried(victim);
                victim.noPhysics = false;
                victim.setNoGravity(false);
                victim.setPos(startX, startY, startZ);
                victim.setDeltaMovement(vx, vy, vz);
                victim.needsSync = true;
                victim.resetFallDistance();
                victim.connection.resetPosition();
            }
            sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.PLAYER_ATTACK_SWEEP, SoundSource.PLAYERS, 0.9F, 0.85F);
            changed = true;
        } else if (dragPressed) {
            if (held != null) {
                held.draggerId = null;
                held.draggerName = "";
                held.holdMode = MODE_NONE;
                setNoStepUp(sp, false);
                setCarrySlow(sp, false);
                sp.removeEffect(MobEffects.SLOWNESS);
                ServerPlayer victim = srv.getPlayerList().getPlayer(held.playerId);
                if (victim != null) {
                    dismountCarried(victim);
                    victim.noPhysics = false;
                    victim.setNoGravity(false);
                }
                sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.ARMOR_EQUIP_LEATHER.value(), SoundSource.PLAYERS, 0.7F, 0.8F);
                changed = true;
            } else {
                DownedEntry targetEntry = findNearestDowned(sp, cfgReviveRange + 0.8);
                if (targetEntry != null) {
                    ServerPlayer victim = srv.getPlayerList().getPlayer(targetEntry.playerId);
                    releaseAnyDraggedBy(srv, actorId);
                    targetEntry.draggerId = actorId;
                    targetEntry.draggerName = sp.getGameProfile().name();
                    targetEntry.holdMode = MODE_DRAG;
                    targetEntry.reviveTicks = 0;
                    targetEntry.activeReviverName = "";
                    if (victim != null) {
                        dismountCarried(victim);
                        victim.noPhysics = false;
                        targetEntry.dragX = victim.getX();
                        targetEntry.dragY = victim.getY();
                        targetEntry.dragZ = victim.getZ();
                    }
                    setNoStepUp(sp, true);
                    setCarrySlow(sp, false);
                    sp.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 30, 1, true, false, false)); // Heavy drag slowness
                    sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(), SoundEvents.ARMOR_EQUIP_LEATHER.value(), SoundSource.PLAYERS, 0.85F, 1.05F);
                    changed = true;
                }
            }
        }

        if (changed) {
            syncAllClients(srv);
        }
    }

    private static void onSwapItems(LivingSwapItemsEvent.Hands event) {
        if (!(event.getEntity() instanceof ServerPlayer sp)) return;
        if (DOWNED.containsKey(sp.getUUID()) || findHeldBy(sp.getUUID()) != null || findNearestDowned(sp, cfgReviveRange + 0.8) != null) {
            event.setCanceled(true);
        }
    }

    private static void onEntityInteract(PlayerInteractEvent.EntityInteract event) {
        if (DOWNED.containsKey(event.getEntity().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onContainerOpen(PlayerContainerEvent.Open event) {
        if (event.getEntity() instanceof ServerPlayer sp && DOWNED.containsKey(sp.getUUID())) {
            sp.closeContainer();
        }
    }

    private static void onItemToss(ItemTossEvent event) {
        if (DOWNED.containsKey(event.getPlayer().getUUID())) {
            event.setCanceled(true);
        }
    }

    private static void onPlayerJoin(PlayerEvent.PlayerLoggedInEvent event) {
        if (event.getEntity() instanceof ServerPlayer sp) {
            if (!DOWNED.containsKey(sp.getUUID()) && findHeldBy(sp.getUUID()) == null) {
                setNoStepUp(sp, false);
                setCarrySlow(sp, false);
                sp.noPhysics = false;
                sp.setNoGravity(false);
            }
            syncToPlayer(sp, sp.level().getServer());
        }
    }

    private static void onPlayerLogout(PlayerEvent.PlayerLoggedOutEvent event) {
        if (event.getEntity() instanceof ServerPlayer sp) {
            UUID id = sp.getUUID();
            GIVEUP_HOLDING.remove(id);
            releaseAnyDraggedBy(sp.level().getServer(), id);
            setNoStepUp(sp, false);
            setCarrySlow(sp, false);
            sp.noPhysics = false;
            sp.setNoGravity(false);
            if (DOWNED.containsKey(id)) {
                finishBleedout(sp);
            }
        }
    }

    private static void cleanupDownedState(ServerPlayer sp) {
        DownedEntry removed = DOWNED.remove(sp.getUUID());
        if (removed != null) {
            if (removed.draggerId != null && sp.level().getServer() != null) {
                ServerPlayer dragger = sp.level().getServer().getPlayerList().getPlayer(removed.draggerId);
                if (dragger != null) {
                    setNoStepUp(dragger, false);
                    setCarrySlow(dragger, false);
                    dragger.removeEffect(MobEffects.SLOWNESS);
                }
            }
            removed.draggerId = null;
            removed.draggerName = "";
            removed.holdMode = MODE_NONE;
        }
        GIVEUP_HOLDING.remove(sp.getUUID());
        dismountCarried(sp);
        setNoStepUp(sp, false);
        setCarrySlow(sp, false);
        sp.noPhysics = false;
        sp.setNoGravity(false);
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
            if (entry.throwProtectTicks > 0) {
                entry.throwProtectTicks--;
                victim.connection.resetPosition();
            }
            if (victim.getHealth() > 1.0F) victim.setHealth(1.0F);
            victim.setSprinting(false);
            victim.resetFallDistance();
            setNoStepUp(victim, true);
            if (victim.containerMenu != victim.inventoryMenu) {
                victim.closeContainer();
            }
            if (victim.getForcedPose() != Pose.SWIMMING) {
                victim.setForcedPose(Pose.SWIMMING);
            }
            if (victim.getRemainingFireTicks() > 0 && !victim.isInLava()) {
                victim.clearFire();
            }

            // Update active Drag (mode=1) or Shoulder Carry (mode=2)
            if (entry.draggerId != null) {
                ServerPlayer dragger = srv.getPlayerList().getPlayer(entry.draggerId);
                boolean validDragger = dragger != null
                        && dragger.isAlive()
                        && !DOWNED.containsKey(dragger.getUUID())
                        && dragger.gameMode() != GameType.SPECTATOR
                        && dragger.level() == victim.level()
                        && (entry.holdMode == MODE_CARRY || dragger.distanceToSqr(victim) <= 42.25);
                if (!validDragger) {
                    if (dragger != null) {
                        setNoStepUp(dragger, false);
                        setCarrySlow(dragger, false);
                        dragger.removeEffect(MobEffects.SLOWNESS);
                    }
                    dismountCarried(victim);
                    entry.draggerId = null;
                    entry.draggerName = "";
                    entry.holdMode = MODE_NONE;
                    victim.noPhysics = false;
                    victim.setNoGravity(false);
                    dirty = true;
                } else if (entry.holdMode == MODE_CARRY) {
                    // Piggyback riding: Vanilla vehicle attachment gives 0% pushing & passes cleanly through 2x1 doors
                    setNoStepUp(dragger, false);
                    setCarrySlow(dragger, true);
                    dragger.setSprinting(false);
                    dragger.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 25, 2, true, false, false));
                    if (victim.getVehicle() != dragger) {
                        victim.startRiding(dragger, true, false);
                        dragger.connection.send(new ClientboundSetPassengersPacket(dragger));
                    }
                    entry.dragX = dragger.getX();
                    entry.dragY = dragger.getY();
                    entry.dragZ = dragger.getZ();
                    victim.resetFallDistance();
                    dirty = true;
                } else {
                    // Ground drag: neither dragger nor victim can climb blocks; heavy drag slowness
                    setNoStepUp(dragger, true);
                    setCarrySlow(dragger, false);
                    dragger.setSprinting(false);
                    dragger.addEffect(new MobEffectInstance(MobEffects.SLOWNESS, 25, 1, true, false, false));
                    victim.noPhysics = false;
                    victim.setNoGravity(false);
                    double dx = victim.getX() - dragger.getX();
                    double dz = victim.getZ() - dragger.getZ();
                    double hDist = Math.hypot(dx, dz);
                    if (hDist > 1.45) {
                        double scale = 1.30 / hDist;
                        entry.dragX = dragger.getX() + dx * scale;
                        entry.dragZ = dragger.getZ() + dz * scale;
                    } else if (hDist < 0.05) {
                        Vec3 look = dragger.getLookAngle();
                        double lx = look.x;
                        double lz = look.z;
                        double ll = Math.hypot(lx, lz);
                        if (ll < 1e-4) { lx = 0.0; lz = 1.0; } else { lx /= ll; lz /= ll; }
                        entry.dragX = dragger.getX() - lx * 1.25;
                        entry.dragZ = dragger.getZ() - lz * 1.25;
                    } else {
                        entry.dragX = victim.getX();
                        entry.dragZ = victim.getZ();
                    }
                    entry.dragY = victim.getY();
                    victim.connection.resetPosition();
                    dirty = true;
                }
            }

            // Look for closest healthy reviver holding Shift within range (only when downed player is resting on ground)
            ServerPlayer reviver = null;
            if (entry.holdMode == MODE_NONE) {
                double bestDistSq = cfgReviveRange * cfgReviveRange;
                for (ServerPlayer candidate : srv.getPlayerList().getPlayers()) {
                    if (candidate.getUUID().equals(victim.getUUID())) continue;
                    if (DOWNED.containsKey(candidate.getUUID())) continue;
                    if (!candidate.isAlive() || candidate.gameMode() == GameType.SPECTATOR) continue;
                    if (candidate.level() != victim.level()) continue;
                    if (findHeldBy(candidate.getUUID()) != null) continue;
                    if (!candidate.isShiftKeyDown()) continue;

                    double dSq = candidate.distanceToSqr(victim);
                    if (dSq <= bestDistSq) {
                        bestDistSq = dSq;
                        reviver = candidate;
                    }
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
                    .append(clean(entry.activeReviverName)).append("|")
                    .append(entry.draggerId != null ? entry.draggerId.toString() : "").append("|")
                    .append(clean(entry.draggerName)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.dragX)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.dragY)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.dragZ)).append("|")
                    .append(entry.holdMode).append("|")
                    .append(entry.throwSeq).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.throwVx)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.throwVy)).append("|")
                    .append(String.format(java.util.Locale.ROOT, "%.3f", entry.throwVz));
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

import com.mojang.blaze3d.vertex.PoseStack;
import com.mojang.math.Axis;
import com.thenest.revive.ReviveHoldPayload;
import com.thenest.revive.SyncDownedPayload;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.client.Camera;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphicsExtractor;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.player.ClientInput;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Pose;
import net.minecraft.world.entity.player.Input;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.client.event.ClientPlayerNetworkEvent;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.MovementInputUpdateEvent;
import net.neoforged.neoforge.client.event.RenderFrameEvent;
import net.neoforged.neoforge.client.event.RenderGuiEvent;
import net.neoforged.neoforge.client.event.RenderPlayerEvent;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.client.network.ClientPacketDistributor;
import net.neoforged.neoforge.common.NeoForge;
import org.joml.Vector3f;

public final class ReviveClient {
    public static final int MODE_NONE = 0;
    public static final int MODE_DRAG = 1;
    public static final int MODE_CARRY = 2;

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
            String reviverName,
            String draggerUuid,
            String draggerName,
            double dragX,
            double dragY,
            double dragZ,
            int holdMode,
            int throwSeq,
            double throwVx,
            double throwVy,
            double throwVz
    ) {}

    private static volatile List<DownedView> DOWNED_LIST = List.of();
    private static volatile boolean wasSelfDowned = false;
    private static volatile boolean wasSelfCarried = false;
    private static volatile boolean lastGiveUpHeld = false;
    private static volatile int localGiveUpTicks = 0;
    private static volatile int lastThrowSeq = -1;
    private static volatile boolean dragLockActive = false;
    private static volatile float dragLockYaw = 0.0F;
    private static volatile float dragLockPitch = 0.0F;
    private static final Set<Integer> FLIPPED_RENDER_IDS = ConcurrentHashMap.newKeySet();

    private ReviveClient() {}

    public static void init() {
        SyncDownedPayload.setClientHandler(ReviveClient::onSync);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onRenderFramePre);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onRenderPlayerPre);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onRenderPlayerPost);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onClientTickPre);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onClientTick);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onScreenOpening);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onMovementInput);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onRenderGui);
        NeoForge.EVENT_BUS.addListener(ReviveClient::onLogout);
    }

    private static void onLogout(ClientPlayerNetworkEvent.LoggingOut event) {
        DOWNED_LIST = List.of();
        wasSelfDowned = false;
        wasSelfCarried = false;
        lastGiveUpHeld = false;
        localGiveUpTicks = 0;
        lastThrowSeq = -1;
        dragLockActive = false;
        FLIPPED_RENDER_IDS.clear();
    }

    private static void onSync(String encoded) {
        List<DownedView> next = new ArrayList<>();
        if (encoded != null && !encoded.isBlank()) {
            for (String line : encoded.split("\n")) {
                String[] p = line.split("\\|", -1);
                if (p.length >= 21) {
                    next.add(new DownedView(
                            p[0],
                            p[1],
                            p[2],
                            parseDouble(p[3], 0.0),
                            parseDouble(p[4], 0.0),
                            parseDouble(p[5], 0.0),
                            parseInt(p[6], 0),
                            Math.max(1, parseInt(p[7], 2400)),
                            parseInt(p[8], 0),
                            Math.max(1, parseInt(p[9], 70)),
                            p[10],
                            p[11],
                            p[12],
                            parseDouble(p[13], 0.0),
                            parseDouble(p[14], 0.0),
                            parseDouble(p[15], 0.0),
                            parseInt(p[16], 0),
                            parseInt(p[17], 0),
                            parseDouble(p[18], 0.0),
                            parseDouble(p[19], 0.0),
                            parseDouble(p[20], 0.0)
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

    private static DownedView findHeldTarget(LocalPlayer me) {
        if (me == null) return null;
        String myId = me.getUUID().toString();
        for (DownedView v : DOWNED_LIST) {
            if (myId.equals(v.draggerUuid()) && v.holdMode() != MODE_NONE) return v;
        }
        return null;
    }

    private static DownedView findNearestDowned(LocalPlayer me, double maxDist) {
        if (me == null) return null;
        String myDim = me.level().dimension().identifier().toString();
        String myId = me.getUUID().toString();
        double bestSq = maxDist * maxDist;
        DownedView best = null;
        for (DownedView v : DOWNED_LIST) {
            if (myId.equals(v.uuid()) || !myDim.equals(v.dimension())) continue;
            double dx = v.x() - me.getX();
            double dy = v.y() - me.getY();
            double dz = v.z() - me.getZ();
            double sq = dx * dx + dy * dy + dz * dz;
            if (sq <= bestSq) {
                bestSq = sq;
                best = v;
            }
        }
        return best;
    }

    private static void applyDragCameraLock(LocalPlayer me, DownedView held) {
        Minecraft mc = Minecraft.getInstance();
        if (me != null && held != null && held.holdMode() == MODE_DRAG) {
            double tx = held.x();
            double tz = held.z();
            if (mc.level != null) {
                for (Player rp : mc.level.players()) {
                    if (rp.getUUID().toString().equals(held.uuid())) {
                        tx = rp.getX();
                        tz = rp.getZ();
                        break;
                    }
                }
            }
            double dx = tx - me.getX();
            double dz = tz - me.getZ();
            if (dx * dx + dz * dz > 1e-4) {
                dragLockYaw = (float) (Math.toDegrees(Math.atan2(dz, dx)) - 90.0);
                dragLockActive = true;
            } else if (!dragLockActive) {
                dragLockYaw = me.getYRot();
                dragLockActive = true;
            }
            float diff = Mth.wrapDegrees(me.getYRot() - dragLockYaw);
            if (diff > 90.0F || diff < -90.0F) {
                float clampedYaw = dragLockYaw + Math.max(-90.0F, Math.min(90.0F, diff));
                me.setYRot(clampedYaw);
                me.yRotO = clampedYaw;
                me.yHeadRot = clampedYaw;
            }
        } else {
            dragLockActive = false;
        }
    }

    private static void onRenderFramePre(RenderFrameEvent.Pre event) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer me = mc.player;
        if (me == null) return;
        DownedView self = findSelf(me);
        if (self == null) {
            applyDragCameraLock(me, findHeldTarget(me));
        } else {
            dragLockActive = false;
        }
    }

    private static void onRenderPlayerPre(RenderPlayerEvent.Pre<?> event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.level == null || DOWNED_LIST.isEmpty()) return;
        int entityId = event.getRenderState().id;
        Entity ent = mc.level.getEntity(entityId);
        if (ent == null) return;
        String uid = ent.getUUID().toString();
        for (DownedView v : DOWNED_LIST) {
            if (!uid.equals(v.uuid())) continue;
            if (v.holdMode() == MODE_DRAG) {
                PoseStack ps = event.getPoseStack();
                ps.pushPose();
                double rad = Math.toRadians(event.getRenderState().bodyRot);
                Vector3f spineAxis = new Vector3f((float) (-Math.sin(rad)), 0.0F, (float) Math.cos(rad));
                if (spineAxis.lengthSquared() < 1e-4F) {
                    spineAxis.set(0.0F, 0.0F, 1.0F);
                } else {
                    spineAxis.normalize();
                }
                ps.translate(0.0F, 0.28F, 0.0F);
                ps.rotateDegrees(Axis.of(spineAxis), 180.0F);
                ps.translate(0.0F, -0.28F, 0.0F);
                FLIPPED_RENDER_IDS.add(entityId);
                return;
            } else if (v.holdMode() == MODE_CARRY) {
                PoseStack ps = event.getPoseStack();
                ps.pushPose();
                float backX = 0.0F;
                float backZ = 0.0F;
                for (Player p : mc.level.players()) {
                    if (p.getUUID().toString().equals(v.draggerUuid())) {
                        double rad = Math.toRadians(p.yBodyRot);
                        backX = (float) (Math.sin(rad) * 0.42);
                        backZ = (float) (-Math.cos(rad) * 0.42);
                        break;
                    }
                }
                ps.translate(backX, -0.78F, backZ);
                event.getRenderState().swimAmount = 0.0F;
                event.getRenderState().isVisuallySwimming = false;
                FLIPPED_RENDER_IDS.add(entityId);
                return;
            }
        }
    }

    private static void onRenderPlayerPost(RenderPlayerEvent.Post<?> event) {
        if (FLIPPED_RENDER_IDS.remove(event.getRenderState().id)) {
            event.getPoseStack().popPose();
        }
    }

    private static void onScreenOpening(ScreenEvent.Opening event) {
        Minecraft mc = Minecraft.getInstance();
        if (mc.player != null && findSelf(mc.player) != null) {
            Screen next = event.getNewScreen();
            if (next instanceof AbstractContainerScreen<?>) {
                event.setCanceled(true);
            }
        }
    }

    private static void onClientTickPre(ClientTickEvent.Pre event) {
        Minecraft mc = Minecraft.getInstance();
        LocalPlayer me = mc.player;
        if (me == null || mc.getConnection() == null) return;

        DownedView self = findSelf(me);
        if (self != null) {
            dragLockActive = false;
            // Block opening inventory key & close any open container while downed
            while (mc.options.keyInventory.consumeClick()) {}
            if (mc.gui.screen() instanceof AbstractContainerScreen<?>) {
                me.closeContainer();
                mc.gui.setScreen(null);
            }

            if (self.throwSeq() > 0 && self.throwSeq() != lastThrowSeq) {
                lastThrowSeq = self.throwSeq();
                wasSelfCarried = false;
                me.noPhysics = false;
                me.setNoGravity(false);
                me.setPos(self.dragX(), self.dragY(), self.dragZ());
                me.setDeltaMovement(self.throwVx(), self.throwVy(), self.throwVz());
                me.resetFallDistance();
                return;
            }
            if (lastThrowSeq == -1) {
                lastThrowSeq = self.throwSeq();
            }

            if (self.holdMode() == MODE_CARRY) {
                wasSelfCarried = true;
                me.resetFallDistance();
            } else {
                if (wasSelfCarried) {
                    wasSelfCarried = false;
                    me.noPhysics = false;
                    me.setNoGravity(false);
                }
                // Ground drag glide: flat XZ pull only (cannot go up blocks!)
                if (self.holdMode() == MODE_DRAG && !self.draggerUuid().isEmpty()) {
                    double dx = self.dragX() - me.getX();
                    double dz = self.dragZ() - me.getZ();
                    double hDist = Math.hypot(dx, dz);
                    if (hDist > 0.08) {
                        double speed = Math.min(0.40, hDist * 0.50);
                        double vx = (dx / hDist) * speed;
                        double vz = (dz / hDist) * speed;
                        me.setDeltaMovement(vx, Math.min(0.0, me.getDeltaMovement().y), vz);
                        me.resetFallDistance();
                    }
                }
            }
            return;
        }

        if (wasSelfCarried) {
            wasSelfCarried = false;
            me.noPhysics = false;
            me.setNoGravity(false);
        }

        DownedView held = findHeldTarget(me);
        applyDragCameraLock(me, held);

        boolean dragPressed = false;
        boolean carryPressed = false;
        boolean throwPressed = false;
        boolean activeWindow = mc.isWindowActive() && mc.gui.screen() == null;

        if (activeWindow && held != null && held.holdMode() == MODE_DRAG) {
            while (mc.options.keyJump.consumeClick()) {}
        }
        if (activeWindow && held != null && held.holdMode() == MODE_CARRY) {
            if (mc.options.keyJump.consumeClick()) {
                while (mc.options.keyJump.consumeClick()) {}
                throwPressed = true;
            }
        }
        DownedView nearby = (held != null) ? held : findNearestDowned(me, 4.0);
        if (activeWindow && nearby != null) {
            if (mc.options.keySwapOffhand.consumeClick()) {
                while (mc.options.keySwapOffhand.consumeClick()) {}
                if (mc.options.keyShift.isDown()) {
                    carryPressed = true;
                } else {
                    dragPressed = true;
                }
            }
        }

        if (dragPressed || carryPressed || throwPressed) {
            try {
                ClientPacketDistributor.sendToServer(new ReviveHoldPayload(dragPressed, carryPressed, throwPressed, false));
            } catch (Throwable ignored) {}
        }
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
            while (mc.options.keyInventory.consumeClick()) {}
            if (mc.gui.screen() instanceof AbstractContainerScreen<?>) {
                me.closeContainer();
                mc.gui.setScreen(null);
            }
        } else if (wasSelfDowned) {
            wasSelfDowned = false;
            wasSelfCarried = false;
            lastThrowSeq = -1;
            me.noPhysics = false;
            me.setNoGravity(false);
            me.setForcedPose(null);
        } else {
            applyDragCameraLock(me, findHeldTarget(me));
        }

        boolean giveUpDown = (self != null && mc.isWindowActive() && mc.gui.screen() == null && mc.options.keyJump.isDown());

        if (giveUpDown) {
            localGiveUpTicks = Math.min(30, localGiveUpTicks + 1);
        } else {
            localGiveUpTicks = 0;
        }

        if (giveUpDown != lastGiveUpHeld) {
            lastGiveUpHeld = giveUpDown;
            try {
                ClientPacketDistributor.sendToServer(new ReviveHoldPayload(false, false, false, giveUpDown));
            } catch (Throwable ignored) {}
        }
    }

    private static void onMovementInput(MovementInputUpdateEvent event) {
        if (!(event.getEntity() instanceof LocalPlayer me)) return;
        DownedView self = findSelf(me);
        if (self != null) {
            ClientInput ci = event.getInput();
            Input k = ci.keyPresses;
            boolean held = self.holdMode() != MODE_NONE;
            ci.keyPresses = held
                    ? new Input(false, false, false, false, false, false, false)
                    : new Input(k.forward(), k.backward(), k.left(), k.right(), false, false, false);
            me.setSprinting(false);
            return;
        }
        DownedView held = findHeldTarget(me);
        if (held != null && (held.holdMode() == MODE_DRAG || held.holdMode() == MODE_CARRY)) {
            ClientInput ci = event.getInput();
            Input k = ci.keyPresses;
            boolean allowJump = (held.holdMode() == MODE_CARRY) && k.jump();
            ci.keyPresses = new Input(k.forward(), k.backward(), k.left(), k.right(), allowJump, k.shift(), false);
            me.setSprinting(false);
        }
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
            boolean carried = !reviving && self.holdMode() == MODE_CARRY && !self.draggerUuid().isEmpty();
            boolean dragged = !reviving && !carried && self.holdMode() == MODE_DRAG && !self.draggerUuid().isEmpty();
            boolean urgent = !reviving && self.bleedTicks() <= 200; // < 10s

            int accent = reviving ? 0xFF4ADE80 : ((carried || dragged) ? 0xFF38BDF8 : (localGiveUpTicks > 0 ? 0xFFE09F3E : 0xFFE84848));
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
            } else if (carried) {
                leftTitle = "CARRIED · " + self.draggerName();
                rightStat = String.format(Locale.ROOT, "%.1fs", Math.max(0, self.bleedTicks()) / 20.0);
                ratio = Math.max(0.0, Math.min(1.0, self.bleedTicks() / (double) self.maxBleedTicks()));
            } else if (dragged) {
                leftTitle = "DRAGGED · " + self.draggerName();
                rightStat = String.format(Locale.ROOT, "%.1fs", Math.max(0, self.bleedTicks()) / 20.0);
                ratio = Math.max(0.0, Math.min(1.0, self.bleedTicks() / (double) self.maxBleedTicks()));
            } else {
                leftTitle = "WOUNDED";
                rightStat = String.format(Locale.ROOT, "%.1fs", Math.max(0, self.bleedTicks()) / 20.0);
                ratio = Math.max(0.0, Math.min(1.0, self.bleedTicks() / (double) self.maxBleedTicks()));
            }
            int statW = mc.font.width(rightStat);
            String clippedLeft = mc.font.plainSubstrByWidth(leftTitle, bw - statW - 26);
            int leftCol = reviving ? 0xFF4ADE80 : ((carried || dragged) ? 0xFF7DD3FC : (urgent ? 0xFFFF7A7A : 0xFFF5ECE0));
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

        // Healthy player HUD: active revive, carrying/dragging bar, or nearby downed action prompt
        String myName = me.getGameProfile().name();
        DownedView activeTarget = null;
        DownedView heldTarget = findHeldTarget(me);
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
        } else if (heldTarget != null) {
            boolean isCarry = heldTarget.holdMode() == MODE_CARRY;
            int bw = 236;
            int bh = 34;
            int bx = (sw - bw) / 2;
            int by = sh - 92;
            int stripe = isCarry ? 0xFFE09F3E : 0xFF38BDF8;
            int titleCol = isCarry ? 0xFFF6D37A : 0xFF7DD3FC;
            g.fill(bx, by, bx + bw, by + bh, 0xE8130E0B);
            g.fill(bx, by, bx + bw, by + 1, 0xFF3B2D21);
            g.fill(bx, by + bh - 1, bx + bw, by + bh, 0xFF3B2D21);
            g.fill(bx, by, bx + 3, by + bh, stripe);
            String title = (isCarry ? "CARRYING " : "DRAGGING ") + heldTarget.name();
            String sTxt = String.format(Locale.ROOT, "%.0fs", Math.max(0, heldTarget.bleedTicks()) / 20.0);
            g.text(mc.font, mc.font.plainSubstrByWidth(title, bw - 44), bx + 10, by + 6, titleCol, false);
            g.text(mc.font, sTxt, bx + bw - 10 - mc.font.width(sTxt), by + 6, 0xFFE09F3E, false);
            String hint = isCarry ? "[Space] Throw · [Shift+F] Put Down" : "[F] Release · [Shift+F] Carry on Back";
            g.text(mc.font, hint, bx + (bw - mc.font.width(hint)) / 2, by + 20, 0xFFA89682, false);
        } else {
            DownedView near = findNearestDowned(me, 3.6);
            if (near != null) {
                String prompt = "[Shift] Revive · [F] Drag · [Shift+F] Carry";
                int bw = mc.font.width(prompt) + 18;
                int bh = 18;
                int bx = (sw - bw) / 2;
                int by = sh - 82;
                g.fill(bx, by, bx + bw, by + bh, 0xDD130E0B);
                g.fill(bx, by, bx + 2, by + bh, 0xFFE09F3E);
                g.text(mc.font, prompt, bx + 9, by + 5, 0xFFF5ECE0, false);
            }
        }

        if (self == null) {
            float partialTick = event.getPartialTick().getGameTimeDeltaPartialTick(true);
            renderFloatingTimerCircles(mc, me, g, sw, sh, list, partialTick);
        }

        String myDim = me.level().dimension().identifier().toString();
        int ay = 10;
        for (DownedView v : list) {
            if (!myDim.equals(v.dimension())) continue;
            double dx = v.x() - me.getX();
            double dy = v.y() - me.getY();
            double dz = v.z() - me.getZ();
            int dist = (int) Math.round(Math.sqrt(dx * dx + dy * dy + dz * dz));
            String secs = formatCountdown(v.bleedTicks());
            String alert = "! " + v.name() + " DOWN · " + dist + "m · " + secs;
            int aw = mc.font.width(alert) + 14;
            int ax = sw - aw - 8;
            g.fill(ax, ay, ax + aw, ay + 16, 0xDD130E0B);
            g.fill(ax, ay, ax + 2, ay + 16, 0xFFE84848);
            g.text(mc.font, alert, ax + 7, ay + 4, 0xFFF5ECE0, false);
            ay += 19;
        }
    }

    private static String formatCountdown(int ticks) {
        int sec = Math.max(0, (int) Math.ceil(ticks / 20.0));
        if (sec >= 60) {
            return (sec / 60) + ":" + String.format(Locale.ROOT, "%02d", sec % 60);
        }
        return sec + "s";
    }

    private static void renderFloatingTimerCircles(
            Minecraft mc, LocalPlayer me, GuiGraphicsExtractor g, int sw, int sh, List<DownedView> list, float partialTick
    ) {
        if (mc.level == null) return;
        Camera cam = mc.gameRenderer.mainCamera();
        Vec3 camPos = cam.position();
        Vec3 camFwd = new Vec3(cam.forwardVector());
        String myId = me.getUUID().toString();
        String myDim = me.level().dimension().identifier().toString();
        Font font = mc.font;

        for (DownedView v : list) {
            if (myId.equals(v.uuid()) || !myDim.equals(v.dimension())) continue;

            Player rp = null;
            for (Player p : mc.level.players()) {
                if (p.getUUID().toString().equals(v.uuid())) {
                    rp = p;
                    break;
                }
            }
            Vec3 basePos = (rp != null) ? rp.getPosition(partialTick) : new Vec3(v.x(), v.y(), v.z());
            Vec3 anchor = basePos.add(0.0, 0.85, 0.0);

            Vec3 diff = anchor.subtract(camPos);
            double dist = diff.length();
            if (dist < 1.1 || dist > 64.0) continue;
            if (diff.dot(camFwd) <= 0.2) continue;

            Vec3 ndc = mc.gameRenderer.projectPointToScreen(anchor);
            if (ndc.z >= 1.0) continue;

            int cx = (int) Math.round((ndc.x * 0.5 + 0.5) * sw);
            int cy = (int) Math.round((-ndc.y * 0.5 + 0.5) * sh);
            if (cx < -24 || cx > sw + 24 || cy < -24 || cy > sh + 24) continue;

            boolean reviving = v.reviveTicks() > 0 && !v.reviverName().isEmpty();
            boolean held = !reviving && v.holdMode() != MODE_NONE;
            double ratio = reviving
                    ? (v.reviveTicks() / (double) v.maxReviveTicks())
                    : (v.bleedTicks() / (double) v.maxBleedTicks());
            ratio = Math.max(0.0, Math.min(1.0, ratio));

            float distScale = (float) Math.max(0.45, Math.min(1.0, 8.5 / Math.max(5.0, dist)));
            int accentCol = reviving ? 0xFF4ADE80 : (held ? 0xFF38BDF8 : (v.bleedTicks() <= 400 ? 0xFFFF5A5A : 0xFFE85454));
            int pct = (int) Math.round(ratio * 100.0);
            String label = formatCountdown(v.bleedTicks()) + " · " + pct + "%";

            g.pose().pushMatrix();
            g.pose().translate((float) cx, (float) cy);
            g.pose().scale(distScale, distScale);

            int tw = (int) Math.ceil(font.width(label) * 0.75F);
            int pw = Math.max(46, tw + 14);
            int ph = 15;
            int px0 = -pw / 2;
            int py0 = -ph / 2;

            // Sleek clipped-corner dark espresso pill + 1px hairline border + sharp 2px progress strip
            g.fill(px0 + 1, py0, px0 + pw - 1, py0 + ph, 0xCC110D0A);
            g.fill(px0, py0 + 1, px0 + pw, py0 + ph - 1, 0xCC110D0A);
            g.fill(px0 + 1, py0, px0 + pw - 1, py0 + 1, 0xAA3B2D21);
            g.fill(px0 + 1, py0 + ph - 1, px0 + pw - 1, py0 + ph, 0xAA3B2D21);

            int barW = pw - 4;
            int fillW = (int) Math.round(barW * ratio);
            g.fill(px0 + 2, py0 + ph - 3, px0 + 2 + barW, py0 + ph - 1, 0xFF241B15);
            if (fillW > 0) {
                g.fill(px0 + 2, py0 + ph - 3, px0 + 2 + fillW, py0 + ph - 1, accentCol);
            }

            g.pose().pushMatrix();
            g.pose().translate(0.0F, (float) (py0 + 3.0));
            g.pose().scale(0.75F, 0.75F);
            int lw = font.width(label);
            g.text(font, label, -lw / 2, 0, 0xFFF5ECE0, true);
            g.pose().popMatrix();

            g.pose().popMatrix();
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
    r"c:\Users\katen\Desktop\Minecraft Modpack\pack\mods\nest_revive-1.0.0-neoforge-26.3.jar",
    os.path.expandvars(r"%LOCALAPPDATA%\TheNestVanilla\instance\mods\nest_revive-1.0.0-neoforge-26.3.jar"),
]
for dst in targets:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        shutil.copy2(out_jar, dst)
        print("Installed:", dst, os.path.getsize(dst), "bytes")
    except PermissionError:
        print("LOCKED (in use, restart to apply):", dst)
