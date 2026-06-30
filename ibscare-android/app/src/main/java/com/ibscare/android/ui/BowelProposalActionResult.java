package com.ibscare.android.ui;

import com.ibscare.android.session.BowelSessionLikelihoodResult;

public final class BowelProposalActionResult {
    private final boolean shouldPrefill;
    private final String suggestedTime;
    private final String title;
    private final String body;

    private BowelProposalActionResult(
            boolean shouldPrefill,
            String suggestedTime,
            String title,
            String body) {
        this.shouldPrefill = shouldPrefill;
        this.suggestedTime = suggestedTime;
        this.title = title;
        this.body = body;
    }

    public static BowelProposalActionResult from(BowelSessionLikelihoodResult likelihood) {
        if (likelihood != null && likelihood.shouldPrompt()) {
            return new BowelProposalActionResult(
                    true,
                    likelihood.suggestedTime(),
                    "추천 시간을 기록 폼에 채웠습니다.",
                    "아래 오늘의 배변에서 내용을 확인한 뒤 기록 저장을 눌러야 저장됩니다.");
        }
        String summary = likelihood == null
                ? "아직 감지 후보가 계산되지 않았습니다."
                : likelihood.summary();
        return new BowelProposalActionResult(
                false,
                "",
                "직접 기록할 수 있습니다.",
                summary + "\n직접 기록하려면 아래 오늘의 배변 항목을 채우고 기록 저장을 눌러 주세요.");
    }

    public boolean shouldPrefill() {
        return shouldPrefill;
    }

    public String suggestedTime() {
        return suggestedTime;
    }

    public String title() {
        return title;
    }

    public String body() {
        return body;
    }
}
