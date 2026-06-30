package com.ibscare.android.session;

public final class LocationMovementSnapshot {
    private final double latitude;
    private final double longitude;
    private final float accuracyMeters;
    private final float speedMetersPerSecond;
    private final boolean hasSpeed;
    private final long capturedAtMillis;

    private LocationMovementSnapshot(Builder builder) {
        latitude = builder.latitude;
        longitude = builder.longitude;
        accuracyMeters = builder.accuracyMeters;
        speedMetersPerSecond = builder.speedMetersPerSecond;
        hasSpeed = builder.hasSpeed;
        capturedAtMillis = builder.capturedAtMillis;
    }

    public static Builder builder(double latitude, double longitude) {
        return new Builder(latitude, longitude);
    }

    public double latitude() {
        return latitude;
    }

    public double longitude() {
        return longitude;
    }

    public float accuracyMeters() {
        return accuracyMeters;
    }

    public boolean hasSpeed() {
        return hasSpeed;
    }

    public float speedMetersPerSecond() {
        return speedMetersPerSecond;
    }

    public long capturedAtMillis() {
        return capturedAtMillis;
    }

    public static final class Builder {
        private final double latitude;
        private final double longitude;
        private float accuracyMeters = Float.MAX_VALUE;
        private float speedMetersPerSecond;
        private boolean hasSpeed;
        private long capturedAtMillis;

        private Builder(double latitude, double longitude) {
            this.latitude = latitude;
            this.longitude = longitude;
        }

        public Builder accuracyMeters(float value) {
            accuracyMeters = value;
            return this;
        }

        public Builder speedMetersPerSecond(float value) {
            speedMetersPerSecond = value;
            hasSpeed = true;
            return this;
        }

        public Builder capturedAtMillis(long value) {
            capturedAtMillis = value;
            return this;
        }

        public LocationMovementSnapshot build() {
            return new LocationMovementSnapshot(this);
        }
    }
}
