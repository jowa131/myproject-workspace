package com.ibscare.android.session;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public final class MotionSessionSampler {
    private static final double STILL_DELTA_THRESHOLD = 0.18d;
    private static final double BODY_MOTION_DELTA_THRESHOLD = 0.45d;
    private static final double HANDHELD_VIEWING_VARIANCE_THRESHOLD = 0.35d;
    private static final long WINDOWED_POSTURE_MILLIS = 120_000L;
    private static final int WINDOWED_POSTURE_MIN_SAMPLES = 20;
    private static final double WINDOWED_POSTURE_ACCEL_THRESHOLD = 0.30d;
    private static final double WINDOWED_POSTURE_ORIENTATION_THRESHOLD = 2.5d;
    private static final long STILL_RESET_MILLIS = 30_000L;
    private static final long SIT_TRANSITION_WINDOW_MILLIS = 5 * 60_000L;

    private final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm", Locale.KOREA);
    private final MotionRollingWindow rollingWindow = new MotionRollingWindow();
    private long stillStartedAtMillis = -1L;
    private long lastMotionAtMillis = -1L;
    private double lastMagnitude = -1.0d;
    private double varianceEstimate = 1.0d;
    private double lastPitch = Double.NaN;
    private double lastRoll = Double.NaN;
    private double lastOrientationDelta;

    public MotionFeatures accept(AccelerometerSample sample, boolean screenActive) {
        long nowMillis = sample.capturedAtMillis();
        float x = sample.x();
        float y = sample.y();
        float z = sample.z();
        double magnitude = Math.sqrt((x * x) + (y * y) + (z * z));
        if (lastMagnitude < 0.0d) {
            lastMagnitude = magnitude;
            stillStartedAtMillis = nowMillis;
        }

        double delta = Math.abs(magnitude - lastMagnitude);
        varianceEstimate = (varianceEstimate * 0.85d) + (delta * 0.15d);
        if (delta > BODY_MOTION_DELTA_THRESHOLD) {
            lastMotionAtMillis = nowMillis;
        }
        rollingWindow.addAcceleration(nowMillis, delta);
        if (lastMotionAtMillis > 0L && nowMillis - lastMotionAtMillis < STILL_RESET_MILLIS) {
            stillStartedAtMillis = nowMillis;
        }
        lastMagnitude = magnitude;
        return buildFeatures(nowMillis, screenActive);
    }

    public MotionFeatures acceptGravity(OrientationSample sample, boolean screenActive) {
        long nowMillis = sample.capturedAtMillis();
        if (!Double.isNaN(lastPitch) && !Double.isNaN(lastRoll)) {
            lastOrientationDelta = Math.abs(sample.pitchDegrees() - lastPitch)
                    + Math.abs(sample.rollDegrees() - lastRoll);
            rollingWindow.addOrientation(nowMillis, lastOrientationDelta);
        }
        lastPitch = sample.pitchDegrees();
        lastRoll = sample.rollDegrees();
        if (stillStartedAtMillis < 0L) {
            stillStartedAtMillis = nowMillis;
        }
        return buildFeatures(nowMillis, screenActive);
    }

    private MotionFeatures buildFeatures(long nowMillis, boolean screenActive) {
        int stationaryMinutes = (int) Math.max(0L, (nowMillis - stillStartedAtMillis) / 60_000L);
        boolean postureStable = varianceEstimate <= STILL_DELTA_THRESHOLD;
        boolean usualWindow = isUsualWindow(nowMillis);
        MotionWindowSummary postureWindow = rollingWindow.summarize(nowMillis, WINDOWED_POSTURE_MILLIS);
        boolean sitTransitionLikely = screenActive
                && stationaryMinutes >= 1
                && lastMotionAtMillis > 0L
                && nowMillis - lastMotionAtMillis <= SIT_TRANSITION_WINDOW_MILLIS;
        boolean handheldViewingLikely = screenActive
                && stationaryMinutes >= 2
                && varianceEstimate <= HANDHELD_VIEWING_VARIANCE_THRESHOLD;
        boolean windowedPostureLikely = screenActive
                && stationaryMinutes >= 1
                && postureWindow.sampleCount() >= WINDOWED_POSTURE_MIN_SAMPLES
                && postureWindow.orientationSampleCount() >= WINDOWED_POSTURE_MIN_SAMPLES
                && postureWindow.averageAccelerationDelta() <= WINDOWED_POSTURE_ACCEL_THRESHOLD
                && postureWindow.averageOrientationDelta() <= WINDOWED_POSTURE_ORIENTATION_THRESHOLD;
        boolean seatedPostureLikely = screenActive
                && stationaryMinutes >= 2
                && (postureStable || handheldViewingLikely || windowedPostureLikely);
        return MotionFeatures.builder(timeFormat.format(new Date(nowMillis)))
                .stationaryMinutes(stationaryMinutes)
                .screenActive(screenActive)
                .postureStable(postureStable)
                .seatedPostureLikely(seatedPostureLikely)
                .sitTransitionLikely(sitTransitionLikely)
                .handheldViewingLikely(handheldViewingLikely)
                .windowedPostureLikely(windowedPostureLikely)
                .usualBowelWindow(usualWindow)
                .accelerationVariance(varianceEstimate)
                .orientationChangeRate(postureWindow.averageOrientationDelta())
                .build();
    }

    public MotionFeatures sampleForReview(long nowMillis) {
        return MotionFeatures.builder(timeFormat.format(new Date(nowMillis)))
                .stationaryMinutes(6)
                .screenActive(true)
                .postureStable(true)
                .seatedPostureLikely(true)
                .sitTransitionLikely(true)
                .handheldViewingLikely(true)
                .windowedPostureLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.04d)
                .build();
    }

    private boolean isUsualWindow(long nowMillis) {
        String hourText = new SimpleDateFormat("HH", Locale.KOREA).format(new Date(nowMillis));
        int hour = Integer.parseInt(hourText);
        return hour < 1 || hour > 7;
    }
}
