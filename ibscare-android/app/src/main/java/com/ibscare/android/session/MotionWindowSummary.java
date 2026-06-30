package com.ibscare.android.session;

final class MotionWindowSummary {
    private final int sampleCount;
    private final int orientationSampleCount;
    private final double averageAccelerationDelta;
    private final double averageOrientationDelta;

    MotionWindowSummary(
            int sampleCount,
            int orientationSampleCount,
            double averageAccelerationDelta,
            double averageOrientationDelta) {
        this.sampleCount = sampleCount;
        this.orientationSampleCount = orientationSampleCount;
        this.averageAccelerationDelta = averageAccelerationDelta;
        this.averageOrientationDelta = averageOrientationDelta;
    }

    int sampleCount() {
        return sampleCount;
    }

    int orientationSampleCount() {
        return orientationSampleCount;
    }

    double averageAccelerationDelta() {
        return averageAccelerationDelta;
    }

    double averageOrientationDelta() {
        return averageOrientationDelta;
    }
}
