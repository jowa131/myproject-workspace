package com.ibscare.android.session;

import java.util.Calendar;
import java.util.Locale;
import java.util.TimeZone;

public final class MotionSessionSamplerCliTest {
    private static final float[] STILL_SAMPLE = new float[] {0.0f, 0.0f, 9.8f};

    private MotionSessionSamplerCliTest() {
    }

    public static void run() {
        TimeZone originalTimeZone = TimeZone.getDefault();
        TimeZone.setDefault(TimeZone.getTimeZone("Asia/Seoul"));
        try {
            allowsMidnight();
            excludesEarlyMorningStart();
            excludesSevenOClockHour();
            allowsEightOClockHour();
            detectsHandheldViewingMicroMotion();
            rejectsWindowedPostureWithoutOrientationSamples();
            detectsTiltWindowCandidate();
        } finally {
            TimeZone.setDefault(originalTimeZone);
        }
    }

    private static void allowsMidnight() {
        assertUsualWindow(0, true, "midnight should remain eligible");
    }

    private static void excludesEarlyMorningStart() {
        assertUsualWindow(1, false, "1 AM should be excluded");
    }

    private static void excludesSevenOClockHour() {
        assertUsualWindow(7, false, "7 AM hour should be excluded");
    }

    private static void allowsEightOClockHour() {
        assertUsualWindow(8, true, "8 AM should be eligible");
    }

    private static void detectsHandheldViewingMicroMotion() {
        MotionSessionSampler sampler = new MotionSessionSampler();
        long startedAt = millisAtHour(8);
        MotionFeatures features = null;
        for (int second = 0; second <= 130; second++) {
            float z = second % 2 == 0 ? 9.8f : 10.0f;
            features = sampler.accept(
                    AccelerometerSample.fromValues(new float[] {0.0f, 0.0f, z}, startedAt + (second * 1000L)),
                    true);
        }
        if (features == null || !features.handheldViewingLikely()) {
            throw new AssertionError("screen-active micro motion should look like hand-held viewing");
        }
        if (!features.seatedPostureLikely()) {
            throw new AssertionError("hand-held viewing should contribute to seated posture likelihood");
        }
    }

    private static void detectsTiltWindowCandidate() {
        MotionSessionSampler sampler = new MotionSessionSampler();
        long startedAt = millisAtHour(20);
        MotionFeatures features = null;
        for (int second = 0; second <= 75; second++) {
            long capturedAt = startedAt + (second * 1000L);
            float gravityX = second % 2 == 0 ? 2.0f : 2.15f;
            float gravityY = second % 3 == 0 ? 5.4f : 5.25f;
            features = sampler.acceptGravity(
                    OrientationSample.fromGravity(gravityX, gravityY, 7.8f, capturedAt),
                    true);
            features = sampler.accept(
                    AccelerometerSample.fromValues(new float[] {0.0f, 0.0f, 9.8f}, capturedAt),
                    true);
        }
        if (features == null || !features.windowedPostureLikely()) {
            throw new AssertionError("screen-active stable tilt windows should promote seated phone-use evidence");
        }
        if (!BowelSessionScorer.evaluate(features).shouldPrompt()) {
            throw new AssertionError("windowed posture evidence should be strong enough to prompt");
        }
    }

    private static void rejectsWindowedPostureWithoutOrientationSamples() {
        MotionSessionSampler sampler = new MotionSessionSampler();
        long startedAt = millisAtHour(20);
        MotionFeatures features = null;
        for (int second = 0; second <= 75; second++) {
            features = sampler.accept(
                    AccelerometerSample.fromValues(new float[] {0.0f, 0.0f, 9.8f}, startedAt + (second * 1000L)),
                    true);
        }
        if (features == null || features.windowedPostureLikely()) {
            throw new AssertionError("windowed posture must require real orientation samples");
        }
    }

    private static void assertUsualWindow(int hour, boolean expected, String label) {
        MotionSessionSampler sampler = new MotionSessionSampler();
        MotionFeatures features = sampler.accept(
                AccelerometerSample.fromValues(STILL_SAMPLE, millisAtHour(hour)),
                true);
        if (features.usualBowelWindow() != expected) {
            throw new AssertionError(label);
        }
    }

    private static long millisAtHour(int hour) {
        Calendar calendar = Calendar.getInstance(TimeZone.getTimeZone("Asia/Seoul"), Locale.KOREA);
        calendar.clear();
        calendar.set(2026, Calendar.JUNE, 27, hour, 0, 0);
        return calendar.getTimeInMillis();
    }
}
