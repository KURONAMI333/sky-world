package com.kuronami.skyworld.client;

import net.minecraft.client.renderer.DimensionSpecialEffects;
import net.minecraft.world.phys.Vec3;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.api.distmarker.OnlyIn;

/**
 * Overworld sky effects with the cloud plane lifted above the island bands.
 *
 * <p>Vanilla's {@link DimensionSpecialEffects.OverworldEffects} hardcodes {@code cloudLevel = 192},
 * which in Sky World runs straight through the gap between the middle band (116–176) and the high
 * band (212–242): the cloud sheet cuts through island rock and reads as a rendering fault. Every
 * other value here is copied verbatim from {@code OverworldEffects} so sun, moon, stars, weather
 * and fog stay vanilla — only the cloud height moves.
 *
 * <p>{@link #CLOUD_LEVEL} = 256 puts the clouds just above the highest islands, so the top band
 * sits directly under the cloud sheet instead of through it. The two alternatives, should the
 * in-game look call for them, are a single-constant edit here:
 * <ul>
 *   <li>cloud sea <em>below</em> the world (covers the void when looking down): {@code 40.0F}</li>
 *   <li>no clouds at all (what {@code EndEffects} does): {@code Float.NaN}</li>
 * </ul>
 * There is deliberately no config entry — the shipped value is the product.
 */
@OnlyIn(Dist.CLIENT)
public final class SkyWorldDimensionEffects extends DimensionSpecialEffects {

    /** Cloud plane height. Above the high band's ceiling (242) so it never intersects rock. */
    public static final float CLOUD_LEVEL = 256.0F;

    public SkyWorldDimensionEffects() {
        super(CLOUD_LEVEL, true, DimensionSpecialEffects.SkyType.NORMAL, false, false);
    }

    @Override
    public Vec3 getBrightnessDependentFogColor(Vec3 color, float daylight) {
        return color.multiply(
                daylight * 0.94F + 0.06F,
                daylight * 0.94F + 0.06F,
                daylight * 0.91F + 0.09F);
    }

    @Override
    public boolean isFoggyAt(int x, int z) {
        return false;
    }
}
