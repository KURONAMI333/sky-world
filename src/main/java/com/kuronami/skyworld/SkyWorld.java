package com.kuronami.skyworld;

import com.kuronami.isekaiapi.api.Isekai;
import com.mojang.logging.LogUtils;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import org.slf4j.Logger;

@Mod(SkyWorld.MODID)
public final class SkyWorld {
    public static final String MODID = "sky_world";
    public static final String VERSION = "0.1.0";
    public static final Logger LOGGER = LogUtils.getLogger();

    public SkyWorld(IEventBus modBus) {
        LOGGER.info("Sky World v{} loading", VERSION);
        // Smoke-test the Isekai API facade is reachable at compile time.
        // declareWorldshape() lands once dimension/biome registries are wired.
        LOGGER.info("Sky World: Isekai API facade ready (query={}, remap={})",
                Isekai.query().getClass().getSimpleName(),
                Isekai.remap().getClass().getSimpleName());
    }
}
