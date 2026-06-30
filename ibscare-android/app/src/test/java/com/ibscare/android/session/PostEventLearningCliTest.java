package com.ibscare.android.session;

import com.ibscare.android.data.PersonalPatternSnapshot;

public final class PostEventLearningCliTest {
    private PostEventLearningCliTest() {
    }

    public static void run() {
        learnsFromManualRecordFeatureSummary();
        learnsFromFalsePositiveAlertChoice();
        refusesIdleFallbackForPositiveLearning();
        exposesOnlyFeatureSummaryPreferenceKeys();
    }

    private static void learnsFromFalsePositiveAlertChoice() {
        MotionFeatures mistakenPrompt = MotionFeatures.builder("21:10")
                .stationaryMinutes(3)
                .screenActive(true)
                .postureStable(true)
                .seatedPostureLikely(true)
                .handheldViewingLikely(true)
                .windowedPostureLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.07d)
                .build();
        if (!BowelSessionScorer.evaluate(mistakenPrompt).shouldPrompt()) {
            throw new AssertionError("strong mistaken candidate should prompt before correction");
        }

        PersonalPatternSnapshot learned = PersonalPatternSnapshot.empty().learnNegative(mistakenPrompt);
        MotionFeatures repeatedNonBowel = MotionFeatures.builder("21:12")
                .stationaryMinutes(3)
                .screenActive(true)
                .postureStable(true)
                .seatedPostureLikely(true)
                .handheldViewingLikely(true)
                .windowedPostureLikely(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.08d)
                .falsePositivePatternLikely(learned.matchesFalsePositive(mistakenPrompt))
                .build();
        BowelSessionLikelihoodResult corrected = BowelSessionScorer.evaluate(repeatedNonBowel);
        if (corrected.shouldPrompt()) {
            throw new AssertionError("false-positive choice should suppress repeated prompts");
        }
        if (!corrected.summary().contains("오탐 기록 패턴")) {
            throw new AssertionError("false-positive correction should be visible in score summary");
        }
    }

    private static void learnsFromManualRecordFeatureSummary() {
        PersonalPatternSnapshot snapshot = PersonalPatternSnapshot.empty();
        MotionFeatures savedWindow = MotionFeatures.builder("20:42")
                .stationaryMinutes(1)
                .screenActive(true)
                .usualBowelWindow(true)
                .windowedPostureLikely(true)
                .accelerationVariance(0.18d)
                .build();

        PersonalPatternSnapshot learned = snapshot.learnPositive(savedWindow);
        MotionFeatures futureCandidate = MotionFeatures.builder("20:44")
                .stationaryMinutes(1)
                .screenActive(true)
                .usualBowelWindow(true)
                .accelerationVariance(0.19d)
                .build();
        MotionFeatures futureWindow = MotionFeatures.builder(futureCandidate.suggestedTime())
                .stationaryMinutes(futureCandidate.stationaryMinutes())
                .screenActive(futureCandidate.screenActive())
                .usualBowelWindow(futureCandidate.usualBowelWindow())
                .accelerationVariance(futureCandidate.accelerationVariance())
                .personalPatternLikely(learned.matches(futureCandidate))
                .build();

        if (!futureWindow.personalPatternLikely()) {
            throw new AssertionError("manual record learning should mark similar future feature summaries");
        }
        if (!BowelSessionScorer.evaluate(futureWindow).shouldPrompt()) {
            throw new AssertionError("personal pattern should help similar post-event windows prompt");
        }
    }

    private static void refusesIdleFallbackForPositiveLearning() {
        FeatureSummaryBuffer buffer = new FeatureSummaryBuffer();
        buffer.add(1_000L, MotionFeatures.builder("08:00")
                .screenActive(true)
                .usualBowelWindow(true)
                .build());
        if (buffer.latestCandidateOrNull(2_000L) != null) {
            throw new AssertionError("manual learning must not use idle fallback summaries");
        }
    }

    private static void exposesOnlyFeatureSummaryPreferenceKeys() {
        for (String key : PersonalPatternSnapshot.preferenceKeys()) {
            if (!PersonalPatternSnapshot.isPreferenceKeyAllowed(key)) {
                throw new AssertionError("known feature summary key should be allowed");
            }
            if (key.toLowerCase().contains("raw") || key.toLowerCase().contains("axis")) {
                throw new AssertionError("personal pattern persistence must not expose raw sensor fields");
            }
        }
        if (PersonalPatternSnapshot.isPreferenceKeyAllowed("raw_accelerometer_x")) {
            throw new AssertionError("raw sensor key must not be part of the persistence contract");
        }
    }
}
