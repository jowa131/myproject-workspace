package com.ibscare.android.session;

public final class BowelSessionScorer {
    private static final int PROMPT_THRESHOLD = 80;
    private static final double LOW_VARIANCE_THRESHOLD = 0.08d;

    private BowelSessionScorer() {
    }

    public static BowelSessionLikelihoodResult evaluate(MotionFeatures features) {
        int score = 0;
        StringBuilder summary = new StringBuilder();

        if (features.movingLocation()) {
            return BowelSessionLikelihoodResult.builder(features.suggestedTime())
                    .score0To100(0)
                    .shouldPrompt(false)
                    .summary("GPS 이동 중으로 보여 배변 후보에서 제외했습니다.")
                    .build();
        }

        if (features.screenActive()) {
            score += 10;
        }
        if (features.stationaryMinutes() >= 3) {
            score += 35;
            summary.append(features.stationaryMinutes()).append("분 이상 정지");
        } else if (features.stationaryMinutes() > 0) {
            score += 15;
            summary.append("짧은 정지");
        }
        if (features.postureStable()) {
            score += 15;
            appendReason(summary, "자세 변화 적음");
        }
        if (features.usualBowelWindow()) {
            score += 10;
            appendReason(summary, "평소 시간대");
        }
        if (features.sitTransitionLikely()) {
            score += 10;
            appendReason(summary, "앉은 상태 전환");
        }
        if (features.seatedPostureLikely()) {
            score += 10;
            appendReason(summary, "앉은 자세처럼 안정됨");
        }
        if (features.handheldViewingLikely()) {
            score += 25;
            appendReason(summary, "휴대폰 사용 자세");
        }
        if (features.windowedPostureLikely()) {
            score += 45;
            appendReason(summary, "손에 든 자세 창");
        }
        if (features.personalPatternLikely()) {
            score += 45;
            appendReason(summary, "개인 기록 패턴");
        }
        if (features.accelerationVariance() <= LOW_VARIANCE_THRESHOLD) {
            score += 15;
            appendReason(summary, "움직임 변동 낮음");
        }
        if (features.falsePositivePatternLikely()) {
            appendReason(summary, "오탐 기록 패턴");
            return BowelSessionLikelihoodResult.builder(features.suggestedTime())
                    .score0To100(Math.max(0, score - PROMPT_THRESHOLD))
                    .shouldPrompt(false)
                    .summary(summary.toString())
                    .build();
        }

        boolean shouldPrompt = score >= PROMPT_THRESHOLD;
        String resultSummary = summary.length() == 0
                ? "아직 배변 가능성이 높은 세션으로 보기 어렵습니다."
                : summary.toString();
        return BowelSessionLikelihoodResult.builder(features.suggestedTime())
                .score0To100(score)
                .shouldPrompt(shouldPrompt)
                .summary(resultSummary)
                .build();
    }

    public static boolean hasCandidateEvidence(MotionFeatures features) {
        return features.stationaryMinutes() >= 3
                || features.handheldViewingLikely()
                || features.windowedPostureLikely()
                || features.personalPatternLikely()
                || (features.seatedPostureLikely() && features.stationaryMinutes() >= 2);
    }

    private static void appendReason(StringBuilder summary, String reason) {
        if (summary.length() > 0) {
            summary.append(", ");
        }
        summary.append(reason);
    }
}
