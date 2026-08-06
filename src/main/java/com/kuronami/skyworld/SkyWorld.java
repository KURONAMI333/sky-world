package com.kuronami.skyworld;

import com.kuronami.isekaiapi.api.Isekai;
import com.mojang.logging.LogUtils;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.repository.Pack;
import net.minecraft.server.packs.repository.PackSource;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.event.AddPackFindersEvent;
import org.slf4j.Logger;

@Mod(SkyWorld.MODID)
public final class SkyWorld {
    public static final String MODID = "sky_world";
    public static final String VERSION = "2.0.0";
    public static final Logger LOGGER = LogUtils.getLogger();

    public SkyWorld(IEventBus modBus) {
        LOGGER.info("Sky World v{} loading", VERSION);
        // Smoke-test the Isekai API facade is reachable at compile time.
        // declareWorldshape() lands once dimension/biome registries are wired.
        LOGGER.info("Sky World: Isekai API facade ready (query={}, remap={})",
                Isekai.query().getClass().getSimpleName(),
                Isekai.remap().getClass().getSimpleName());
        modBus.addListener(SkyWorld::addComparisonPacks);
    }

    /**
     * Wave1 sky-colour comparison scaffolding — REMOVE BEFORE RELEASE.
     *
     * <p>The shipping worldshape writes no {@code sky_color} (option A: keep vanilla's
     * per-biome sky). These two optional datapacks carry option B (one colour
     * dimension-wide) and option C (one colour per climate group) so all three can be
     * compared inside a single client launch. {@link PackSource#FEATURE} means they are
     * never enabled automatically; the player opts in with {@code /datapack enable}.
     *
     * <p>Once the colour is chosen the winning value moves into
     * {@code data/sky_world/isekai/worldshape/sky.json} and this method, together with
     * {@code src/main/resources/datapacks/}, is deleted.
     */
    private static void addComparisonPacks(AddPackFindersEvent event) {
        registerComparisonPack(event, "skycolor_b", "Sky World — sky colour B (one colour)");
        registerComparisonPack(event, "skycolor_c", "Sky World — sky colour C (per climate group)");
    }

    private static void registerComparisonPack(AddPackFindersEvent event, String name, String title) {
        event.addPackFinders(
                ResourceLocation.fromNamespaceAndPath(MODID, "datapacks/" + name),
                PackType.SERVER_DATA,
                Component.literal(title),
                PackSource.FEATURE,
                false,
                Pack.Position.TOP);
    }
}
