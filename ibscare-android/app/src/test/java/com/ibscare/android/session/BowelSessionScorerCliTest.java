package com.ibscare.android.session;

import com.ibscare.android.ui.UiCopyCliTest;

public final class BowelSessionScorerCliTest {
    private BowelSessionScorerCliTest() {
    }

    public static void main(String[] args) {
        promptsForStationaryScreenSession();
        promptsAfterEarlierSameDayRecord();
        throttlesRepeatedPromptOnlyDuringCooldown();
        rejectsWeakMotionSession();
        MotionSessionSamplerCliTest.run();
        PostEventLearningCliTest.run();
        CandidateMovementGateCliTest.run();
        PostureCandidateCliTest.run();
        UiCopyCliTest.run();
    }

    private static void promptsForStationaryScreenSession() {
        MotionFeatures features = MotionFeatures.builder("08:14")
                .stationaryMinutes(6)
                .screenActive(true)
                .postureStable(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.04d)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertTrue(result.shouldPrompt(), "high-likelihood session should prompt");
        assertEquals(85, result.score0To100(), "high-likelihood score");
        assertEquals("08:14", result.suggestedTime(), "suggested time");
        assertTrue(result.summary().contains("정지"), "summary should explain stationary evidence");
    }

    private static void promptsAfterEarlierSameDayRecord() {
        MotionFeatures features = MotionFeatures.builder("09:20")
                .stationaryMinutes(8)
                .screenActive(true)
                .postureStable(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.03d)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertTrue(result.shouldPrompt(), "IBS users can have multiple bowel movements per day");
        assertFalse(result.summary().contains("이미"), "summary must not suppress later same-day records");
    }

    private static void throttlesRepeatedPromptOnlyDuringCooldown() {
        PromptCooldownGate gate = new PromptCooldownGate(600_000L);

        assertTrue(gate.canPrompt(1_000L), "first prompt should be allowed");
        gate.markPromptShown(1_000L);
        assertFalse(gate.canPrompt(600_999L), "same-session repeat should be throttled");
        assertTrue(gate.canPrompt(601_000L), "later same-day prompt should be allowed");
    }

    private static void rejectsWeakMotionSession() {
        MotionFeatures features = MotionFeatures.builder("13:05")
                .stationaryMinutes(1)
                .screenActive(true)
                .postureStable(false)
                .usualBowelWindow(false)
                .accelerationVariance(0.6d)
                .build();
        BowelSessionLikelihoodResult result = BowelSessionScorer.evaluate(features);

        assertFalse(result.shouldPrompt(), "weak session must not prompt");
        assertEquals(25, result.score0To100(), "weak session score");
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

    private static void assertEquals(int expected, int actual, String label) {
        if (expected != actual) {
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        }
    }

    private static void assertEquals(String expected, String actual, String label) {
        if (!expected.equals(actual)) {
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        }
    }
}
