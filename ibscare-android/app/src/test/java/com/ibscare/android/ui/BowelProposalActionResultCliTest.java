package com.ibscare.android.ui;

import com.ibscare.android.session.BowelSessionLikelihoodResult;

public final class BowelProposalActionResultCliTest {
    private BowelProposalActionResultCliTest() {
    }

    public static void run() {
        weakCandidateShowsVisibleGuidance();
        promptCandidatePrefillsSuggestedTime();
    }

    private static void weakCandidateShowsVisibleGuidance() {
        BowelSessionLikelihoodResult weak = BowelSessionLikelihoodResult.builder("13:05")
                .score0To100(25)
                .shouldPrompt(false)
                .summary("아직 배변 가능성이 높은 세션으로 보기 어렵습니다.")
                .build();

        BowelProposalActionResult result = BowelProposalActionResult.from(weak);

        assertFalse(result.shouldPrefill(), "weak candidate should not prefill");
        assertContains(result.title(), "직접 기록", "weak candidate visible title");
        assertContains(result.body(), "기록 저장", "weak candidate guidance body");
    }

    private static void promptCandidatePrefillsSuggestedTime() {
        BowelSessionLikelihoodResult likely = BowelSessionLikelihoodResult.builder("20:42")
                .score0To100(92)
                .shouldPrompt(true)
                .summary("휴대폰 사용 자세")
                .build();

        BowelProposalActionResult result = BowelProposalActionResult.from(likely);

        assertTrue(result.shouldPrefill(), "likely candidate should prefill");
        assertContains(result.title(), "추천 시간", "likely candidate visible title");
        assertContains(result.suggestedTime(), "20:42", "likely candidate suggested time");
    }

    private static void assertContains(String text, String expected, String label) {
        if (!text.contains(expected)) {
            throw new AssertionError(label + " should contain " + expected);
        }
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
