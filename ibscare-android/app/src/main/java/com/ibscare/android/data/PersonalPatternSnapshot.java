package com.ibscare.android.data;

import com.ibscare.android.session.MotionFeatures;

public final class PersonalPatternSnapshot {
    public static final String KEY_COUNT = "positive_count";
    public static final String KEY_MIN_STATIONARY = "min_stationary";
    public static final String KEY_VARIANCE = "variance";
    public static final String KEY_POSTURE = "posture";
    public static final String KEY_NEGATIVE_COUNT = "negative_count";
    public static final String KEY_NEGATIVE_MIN_STATIONARY = "negative_min_stationary";
    public static final String KEY_NEGATIVE_VARIANCE = "negative_variance";
    public static final String KEY_NEGATIVE_POSTURE = "negative_posture";

    private final int positiveCount;
    private final int minimumStationaryMinutes;
    private final double learnedVariance;
    private final boolean learnedPosture;
    private final int negativeCount;
    private final int negativeMinimumStationaryMinutes;
    private final double negativeVariance;
    private final boolean negativePosture;

    private PersonalPatternSnapshot(
            int positiveCount,
            int minimumStationaryMinutes,
            double learnedVariance,
            boolean learnedPosture,
            int negativeCount,
            int negativeMinimumStationaryMinutes,
            double negativeVariance,
            boolean negativePosture) {
        this.positiveCount = positiveCount;
        this.minimumStationaryMinutes = minimumStationaryMinutes;
        this.learnedVariance = learnedVariance;
        this.learnedPosture = learnedPosture;
        this.negativeCount = negativeCount;
        this.negativeMinimumStationaryMinutes = negativeMinimumStationaryMinutes;
        this.negativeVariance = negativeVariance;
        this.negativePosture = negativePosture;
    }

    public static PersonalPatternSnapshot empty() {
        return new PersonalPatternSnapshot(0, 1, 1.0d, false, 0, 1, 1.0d, false);
    }

    public static PersonalPatternSnapshot fromStored(
            int positiveCount,
            int minimumStationaryMinutes,
            double learnedVariance,
            boolean learnedPosture,
            int negativeCount,
            int negativeMinimumStationaryMinutes,
            double negativeVariance,
            boolean negativePosture) {
        return new PersonalPatternSnapshot(
                Math.max(0, positiveCount),
                Math.max(1, Math.min(3, minimumStationaryMinutes)),
                Math.max(0.0d, learnedVariance),
                learnedPosture,
                Math.max(0, negativeCount),
                Math.max(1, Math.min(3, negativeMinimumStationaryMinutes)),
                Math.max(0.0d, negativeVariance),
                negativePosture);
    }

    public PersonalPatternSnapshot learnPositive(MotionFeatures features) {
        return new PersonalPatternSnapshot(
                positiveCount + 1,
                Math.max(1, Math.min(3, features.stationaryMinutes())),
                features.accelerationVariance(),
                hasPostureEvidence(features),
                negativeCount,
                negativeMinimumStationaryMinutes,
                negativeVariance,
                negativePosture);
    }

    public PersonalPatternSnapshot learnNegative(MotionFeatures features) {
        return new PersonalPatternSnapshot(
                positiveCount,
                minimumStationaryMinutes,
                learnedVariance,
                learnedPosture,
                negativeCount + 1,
                Math.max(1, Math.min(3, features.stationaryMinutes())),
                features.accelerationVariance(),
                hasPostureEvidence(features));
    }

    public boolean matches(MotionFeatures features) {
        if (positiveCount == 0 || !features.screenActive()) {
            return false;
        }
        boolean postureMatches = learnedPosture && hasPostureEvidence(features);
        boolean varianceMatches = Math.abs(features.accelerationVariance() - learnedVariance) <= 0.20d;
        return features.stationaryMinutes() >= minimumStationaryMinutes
                && (postureMatches || varianceMatches);
    }

    public boolean matchesFalsePositive(MotionFeatures features) {
        if (negativeCount == 0 || !features.screenActive()) {
            return false;
        }
        boolean postureMatches = negativePosture && hasPostureEvidence(features);
        boolean varianceMatches = Math.abs(features.accelerationVariance() - negativeVariance) <= 0.20d;
        return features.stationaryMinutes() >= negativeMinimumStationaryMinutes
                && (postureMatches || varianceMatches);
    }

    public static String[] preferenceKeys() {
        return new String[] {
                KEY_COUNT,
                KEY_MIN_STATIONARY,
                KEY_VARIANCE,
                KEY_POSTURE,
                KEY_NEGATIVE_COUNT,
                KEY_NEGATIVE_MIN_STATIONARY,
                KEY_NEGATIVE_VARIANCE,
                KEY_NEGATIVE_POSTURE
        };
    }

    public static boolean isPreferenceKeyAllowed(String key) {
        for (String allowed : preferenceKeys()) {
            if (allowed.equals(key)) {
                return true;
            }
        }
        return false;
    }

    public int positiveCount() {
        return positiveCount;
    }

    public int minimumStationaryMinutes() {
        return minimumStationaryMinutes;
    }

    public double learnedVariance() {
        return learnedVariance;
    }

    public boolean learnedPosture() {
        return learnedPosture;
    }

    public int negativeCount() {
        return negativeCount;
    }

    public int negativeMinimumStationaryMinutes() {
        return negativeMinimumStationaryMinutes;
    }

    public double negativeVariance() {
        return negativeVariance;
    }

    public boolean negativePosture() {
        return negativePosture;
    }

    private static boolean hasPostureEvidence(MotionFeatures features) {
        return features.windowedPostureLikely()
                || features.handheldViewingLikely()
                || features.seatedPostureLikely();
    }
}
