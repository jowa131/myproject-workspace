package com.ibscare.android.session;

public final class AccelerometerSample {
    private final float x;
    private final float y;
    private final float z;
    private final long capturedAtMillis;

    private AccelerometerSample(float[] values, long capturedAtMillis) {
        x = values[0];
        y = values[1];
        z = values[2];
        this.capturedAtMillis = capturedAtMillis;
    }

    public static AccelerometerSample fromValues(float[] values, long capturedAtMillis) {
        if (values.length < 3) {
            throw new IllegalArgumentException("accelerometer sample needs 3 axes");
        }
        return new AccelerometerSample(values, capturedAtMillis);
    }

    float x() {
        return x;
    }

    float y() {
        return y;
    }

    float z() {
        return z;
    }

    long capturedAtMillis() {
        return capturedAtMillis;
    }
}
