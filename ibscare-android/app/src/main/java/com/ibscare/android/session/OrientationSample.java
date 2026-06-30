package com.ibscare.android.session;

public final class OrientationSample {
    private final double pitchDegrees;
    private final double rollDegrees;
    private final long capturedAtMillis;

    private OrientationSample(double pitchDegrees, double rollDegrees, long capturedAtMillis) {
        this.pitchDegrees = pitchDegrees;
        this.rollDegrees = rollDegrees;
        this.capturedAtMillis = capturedAtMillis;
    }

    public static OrientationSample fromGravity(float x, float y, float z, long capturedAtMillis) {
        double pitch = Math.toDegrees(Math.atan2(-x, Math.sqrt((y * y) + (z * z))));
        double roll = Math.toDegrees(Math.atan2(y, z));
        return new OrientationSample(pitch, roll, capturedAtMillis);
    }

    double pitchDegrees() {
        return pitchDegrees;
    }

    double rollDegrees() {
        return rollDegrees;
    }

    long capturedAtMillis() {
        return capturedAtMillis;
    }
}
