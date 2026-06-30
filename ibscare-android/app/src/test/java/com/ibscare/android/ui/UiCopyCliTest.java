package com.ibscare.android.ui;

public final class UiCopyCliTest {
    private UiCopyCliTest() {
    }

    public static void run() {
        assertContains(UiCopy.SAFETY_NOTICE, "의료 판단", "safety notice");
        assertContains(UiCopy.VERSION_LABEL_PREFIX, "버전", "version label prefix");
        assertContains(UiCopy.PROPOSAL_DISCLAIMER, "자동 저장이 아니며", "proposal disclaimer");
        assertContains(UiCopy.SESSION_ALERT_TITLE, "기록", "session alert title");
        assertContains(UiCopy.SESSION_ALERT_BODY, "가능성이 높은", "session alert body");
        assertContains(UiCopy.SESSION_ALERT_NOTIFICATION, "감지", "session alert notification");
        assertContains(UiCopy.SESSION_ALERT_CONFIRM, "확인", "session alert confirm");
        assertContains(UiCopy.SESSION_ALERT_RECORD_ACTION, "기록하러 가기",
                "session alert notification record action");
        assertContains(UiCopy.SESSION_ALERT_FALSE_POSITIVE, "똥싸는 중이 아님",
                "session alert false positive");
        assertNotContains(UiCopy.SESSION_ALERT_FALSE_POSITIVE, "나중에",
                "session alert false positive");
        assertContains(UiCopy.SESSION_ALERT_CHANNEL, "제안", "session alert channel");
        assertContains(UiCopy.MONITORING_TITLE, "감지", "monitoring title");
        assertContains(UiCopy.LOCATION_PERMISSION_REASON, "이동 중", "location permission reason");
        assertContains(UiCopy.MONITORING_IMPACT_MEMO, "0MB", "monitoring impact memo");
        assertContains(UiCopy.SAFETY_MEMO, "의료진 상담", "red-flag memo");
        assertContains(UiCopy.UPDATE_PANEL_TITLE, "업데이트", "update panel title");
        assertContains(UiCopy.UPDATE_PANEL_BODY, "Android 설치 확인", "update panel body");
        assertContains(UiCopy.UPDATE_PICK_BUTTON, "APK", "update pick button");
        assertContains(UiCopy.UPDATE_INSTALL_PERMISSION_BODY, "Android 설정", "update install permission body");
        BowelProposalActionResultCliTest.run();
        assertEquals(7, UiCopy.BRISTOL_LABELS.length, "bristol label count");
        assertContains(UiCopy.BRISTOL_LABELS[0], "딱딱한 알갱이", "bristol type 1");
        assertContains(UiCopy.BRISTOL_LABELS[3], "바나나 모양", "bristol type 4");
        assertContains(UiCopy.BRISTOL_LABELS[6], "물처럼 묽은", "bristol type 7");
    }

    private static void assertContains(String text, String expected, String label) {
        if (!text.contains(expected)) {
            throw new AssertionError(label + " should contain " + expected);
        }
    }

    private static void assertEquals(int expected, int actual, String label) {
        if (expected != actual) {
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        }
    }

    private static void assertNotContains(String text, String forbidden, String label) {
        if (text.contains(forbidden)) {
            throw new AssertionError(label + " should not contain " + forbidden);
        }
    }
}
