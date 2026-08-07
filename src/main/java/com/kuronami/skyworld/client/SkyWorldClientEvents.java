package com.kuronami.skyworld.client;

import com.kuronami.skyworld.SkyWorld;
import net.minecraft.world.level.dimension.BuiltinDimensionTypes;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.RegisterDimensionSpecialEffectsEvent;

/**
 * Client-only wiring. {@code value = Dist.CLIENT} keeps this class off the dedicated server's
 * class path, so {@link SkyWorldDimensionEffects} (which extends a client-only Minecraft type)
 * is never loaded there.
 *
 * <p>{@code register} overwrites the entry keyed by the effects id, so registering
 * {@link BuiltinDimensionTypes#OVERWORLD_EFFECTS} replaces vanilla's overworld sky rather than
 * adding a new one. That is what Sky World wants — it replaces the overworld. Note the
 * side effect: any other dimension whose {@code dimension_type} points at
 * {@code minecraft:overworld} effects inherits the raised cloud plane too.
 */
@EventBusSubscriber(modid = SkyWorld.MODID, value = Dist.CLIENT, bus = EventBusSubscriber.Bus.MOD)
public final class SkyWorldClientEvents {

    private SkyWorldClientEvents() {}

    @SubscribeEvent
    public static void registerDimensionEffects(RegisterDimensionSpecialEffectsEvent event) {
        event.register(BuiltinDimensionTypes.OVERWORLD_EFFECTS, new SkyWorldDimensionEffects());
    }
}
