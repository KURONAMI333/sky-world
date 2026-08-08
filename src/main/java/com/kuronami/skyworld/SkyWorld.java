package com.kuronami.skyworld;

import com.kuronami.isekaiapi.api.Isekai;
import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;

/**
 * Sky World is a datapack world with one piece of client code: the cloud plane has to sit
 * above the top island band, and cloud height is not reachable from a datapack. That lives
 * in {@link com.kuronami.skyworld.client.SkyWorldDimensionEffects}.
 */
@Mod(SkyWorld.MODID)
public final class SkyWorld {
    public static final String MODID = "sky_world";
    public static final String VERSION = "2.0.0";
    public static final Logger LOGGER = LogUtils.getLogger();

    public SkyWorld(IEventBus modBus) {
        LOGGER.info("Sky World v{} loading", VERSION);
        LOGGER.info("Sky World: Isekai API facade ready (query={}, remap={})",
                Isekai.query().getClass().getSimpleName(),
                Isekai.remap().getClass().getSimpleName());
    }
}
