package com.ibscare.android.session;

public final class CandidateMovementGate {
    private static final float MAX_RELIABLE_ACCURACY_METERS = 80.0f;
    private static final float MOVING_SPEED_METERS_PER_SECOND = 0.9f;
    private static final double MOVING_DISTANCE_METERS = 75.0d;
    private static final long MAX_DISTANCE_WINDOW_MILLIS = 5 * 60 * 1000L;
    private static final double EARTH_RADIUS_METERS = 6_371_000.0d;

    private CandidateMovementGate() {
    }

    public static boolean isMoving(
            LocationMovementSnapshot previous,
            LocationMovementSnapshot latest) {
        if (latest == null || !isReliable(latest)) {
            return false;
        }
        if (latest.hasSpeed() && latest.speedMetersPerSecond() >= MOVING_SPEED_METERS_PER_SECOND) {
            return true;
        }
        if (previous == null || !isReliable(previous)) {
            return false;
        }
        long elapsed = Math.abs(latest.capturedAtMillis() - previous.capturedAtMillis());
        if (elapsed > MAX_DISTANCE_WINDOW_MILLIS) {
            return false;
        }
        return distanceMeters(previous, latest) >= MOVING_DISTANCE_METERS;
    }

    private static boolean isReliable(LocationMovementSnapshot snapshot) {
        return snapshot.accuracyMeters() <= MAX_RELIABLE_ACCURACY_METERS;
    }

    private static double distanceMeters(
            LocationMovementSnapshot first,
            LocationMovementSnapshot second) {
        double lat1 = Math.toRadians(first.latitude());
        double lat2 = Math.toRadians(second.latitude());
        double deltaLat = Math.toRadians(second.latitude() - first.latitude());
        double deltaLon = Math.toRadians(second.longitude() - first.longitude());
        double a = Math.sin(deltaLat / 2.0d) * Math.sin(deltaLat / 2.0d)
                + Math.cos(lat1) * Math.cos(lat2)
                * Math.sin(deltaLon / 2.0d) * Math.sin(deltaLon / 2.0d);
        double c = 2.0d * Math.atan2(Math.sqrt(a), Math.sqrt(1.0d - a));
        return EARTH_RADIUS_METERS * c;
    }
}
