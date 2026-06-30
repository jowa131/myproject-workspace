package com.ibscare.android.update;

public final class LocalApkUpdatePolicy {
    public enum StartAction {
        REQUEST_APK,
        REQUEST_INSTALL_PERMISSION,
        STAGE_APK
    }

    public enum InstallerOutcome {
        PENDING_USER_ACTION,
        SUCCESS,
        FAILURE_ABORTED,
        FAILURE_BLOCKED,
        FAILURE_CONFLICT,
        FAILURE_INCOMPATIBLE,
        FAILURE_INVALID,
        FAILURE_STORAGE,
        FAILURE_UNKNOWN
    }

    private LocalApkUpdatePolicy() {
    }

    public static StartAction startAction(boolean hasApkUri, boolean canRequestPackageInstalls) {
        if (!hasApkUri) {
            return StartAction.REQUEST_APK;
        }
        if (!canRequestPackageInstalls) {
            return StartAction.REQUEST_INSTALL_PERMISSION;
        }
        return StartAction.STAGE_APK;
    }

    public static boolean shouldOpenConfirmation(InstallerOutcome outcome) {
        return outcome == InstallerOutcome.PENDING_USER_ACTION;
    }

    public static boolean isSuccessful(InstallerOutcome outcome) {
        return outcome == InstallerOutcome.SUCCESS;
    }

    public static String installStatusLabel(InstallerOutcome outcome) {
        switch (outcome) {
            case FAILURE_ABORTED:
                return "사용자가 설치를 취소했습니다.";
            case FAILURE_BLOCKED:
                return "Android가 설치를 차단했습니다.";
            case FAILURE_CONFLICT:
                return "기존 앱과 충돌합니다.";
            case FAILURE_INCOMPATIBLE:
                return "이 APK는 현재 기기와 호환되지 않습니다.";
            case FAILURE_INVALID:
                return "APK 파일이 올바르지 않습니다.";
            case FAILURE_STORAGE:
                return "저장 공간이 부족합니다.";
            default:
                return "설치 상태를 확인할 수 없습니다.";
        }
    }

    public static String failureMessage(InstallerOutcome outcome, String statusMessage) {
        String suffix = statusMessage == null || statusMessage.isBlank()
                ? ""
                : "\n" + statusMessage;
        return "APK 업데이트 요청 실패: " + installStatusLabel(outcome) + suffix;
    }

    public static String exceptionMessage(Exception exception) {
        if (exception instanceof SecurityException) {
            return "APK 파일을 열 권한이 없습니다. APK 파일 선택 버튼으로 다시 선택해 주세요.";
        }
        String message = exception.getMessage();
        return message == null || message.isBlank()
                ? exception.getClass().getSimpleName()
                : message;
    }
}
