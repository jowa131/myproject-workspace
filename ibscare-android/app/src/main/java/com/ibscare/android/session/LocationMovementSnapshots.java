package com.ibscare.android.session;

import android.location.Location;

public final class LocationMovementSnapshots {
    private LocationMovementSnapshots() {
    }

    public static LocationMovementSnapshot from(Location location) {
        if (location == null) {
            return null;
        }
        LocationMovementSnapshot.Builder builder = LocationMovementSnapshot.builder(
                        location.getLatitude(),
                        location.getLongitude())
                .capturedAtMillis(location.getTime());
        if (location.hasAccuracy()) {
            builder.accuracyMeters(location.getAccuracy());
        }
        if (location.hasSpeed()) {
            builder.speedMetersPerSecond(location.getSpeed());
        }
        return builder.build();
    }
}
