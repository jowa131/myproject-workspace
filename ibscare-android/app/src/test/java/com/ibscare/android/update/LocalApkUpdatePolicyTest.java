package com.ibscare.android.update;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class LocalApkUpdatePolicyTest {
    @Test
    public void startActionRequestsApkWhenNoUriExists() {
        assertEquals(
                LocalApkUpdatePolicy.StartAction.REQUEST_APK,
                LocalApkUpdatePolicy.startAction(false, true));
    }

    @Test
    public void startActionRequestsInstallPermissionBeforeStaging() {
        assertEquals(
                LocalApkUpdatePolicy.StartAction.REQUEST_INSTALL_PERMISSION,
                LocalApkUpdatePolicy.startAction(true, false));
    }

    @Test
    public void startActionStagesApkAfterInstallPermissionIsAllowed() {
        assertEquals(
                LocalApkUpdatePolicy.StartAction.STAGE_APK,
                LocalApkUpdatePolicy.startAction(true, true));
    }

    @Test
    public void pendingUserActionOpensAndroidConfirmation() {
        assertTrue(LocalApkUpdatePolicy.shouldOpenConfirmation(
                LocalApkUpdatePolicy.InstallerOutcome.PENDING_USER_ACTION));
        assertFalse(LocalApkUpdatePolicy.shouldOpenConfirmation(
                LocalApkUpdatePolicy.InstallerOutcome.SUCCESS));
    }

    @Test
    public void failureMessageIncludesUserSafeStatusAndInstallerDetail() {
        assertEquals(
                "APK 업데이트 요청 실패: 이 APK는 현재 기기와 호환되지 않습니다.\nminSdk mismatch",
                LocalApkUpdatePolicy.failureMessage(
                        LocalApkUpdatePolicy.InstallerOutcome.FAILURE_INCOMPATIBLE,
                        "minSdk mismatch"));
    }

    @Test
    public void securityExceptionMessageRoutesUserBackToPicker() {
        assertEquals(
                "APK 파일을 열 권한이 없습니다. APK 파일 선택 버튼으로 다시 선택해 주세요.",
                LocalApkUpdatePolicy.exceptionMessage(new SecurityException("denied")));
    }
}
