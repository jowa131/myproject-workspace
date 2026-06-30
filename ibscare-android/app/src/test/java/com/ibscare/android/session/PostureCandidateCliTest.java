package com.ibscare.android.session;

public final class PostureCandidateCliTest {
    private PostureCandidateCliTest() {
    }

    public static void run() {
        seatedStabilityCanPromoteCandidate();
        handheldViewingCandidateCanPromoteCandidate();
        movingLocationCopyPreservesPostureSignals();
        movingLocationSuppressesCandidate();
    }

    private static void seatedStabilityCanPromoteCandidate() {
        MotionFeatures features = MotionFeatures.builder("08:14")
                .stationaryMinutes(3)
                .screenActive(true)
                .postureStable(true)
                .seatedPostureLikely(true)
                .usualBowelWindow(false)
                .accelerationVariance(0.04d)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertTrue(result.shouldPrompt(), "seated stable candidate should prompt");
        assertTrue(result.summary().contains("앉은 자세"), "summary should explain seated posture signal");
    }

    private static void handheldViewingCandidateCanPromoteCandidate() {
        MotionFeatures features = MotionFeatures.builder("08:14")
                .stationaryMinutes(2)
                .screenActive(true)
                .postureStable(false)
                .seatedPostureLikely(true)
                .sitTransitionLikely(true)
                .handheldViewingLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.22d)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertTrue(result.shouldPrompt(), "hand-held viewing candidate should prompt");
        assertTrue(result.summary().contains("휴대폰 사용 자세"), "summary should explain hand-held viewing signal");
    }

    private static void movingLocationCopyPreservesPostureSignals() {
        MotionFeatures features = MotionFeatures.builder("08:14")
                .stationaryMinutes(2)
                .screenActive(true)
                .postureStable(false)
                .seatedPostureLikely(true)
                .sitTransitionLikely(true)
                .handheldViewingLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.22d)
                .build();

        MotionFeatures copied = features.withMovingLocation(false);

        assertTrue(copied.sitTransitionLikely(), "location copy should preserve sit transition evidence");
        assertTrue(copied.handheldViewingLikely(), "location copy should preserve hand-held viewing evidence");
        assertTrue(BowelSessionScorer.evaluate(copied).shouldPrompt(),
                "non-moving location copy should remain prompt eligible");
    }

    private static void movingLocationSuppressesCandidate() {
        MotionFeatures features = MotionFeatures.builder("08:14")
                .stationaryMinutes(6)
                .screenActive(true)
                .postureStable(true)
                .seatedPostureLikely(true)
                .sitTransitionLikely(true)
                .handheldViewingLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.04d)
                .movingLocation(true)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertFalse(result.shouldPrompt(), "moving location must suppress prompt");
        assertTrue(result.summary().contains("이동 중"), "summary should explain movement exclusion");
    }

    private static void assertTrue(boolean actual, String label) {
        if (!actual) {
            throw new AssertionError(label);
        }
    }

    private static void assertFalse(boolean actual, String label) {
        if (actual) {
            throw new AssertionError(label);
        }
    }
}
