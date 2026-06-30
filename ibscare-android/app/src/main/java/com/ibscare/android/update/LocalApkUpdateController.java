package com.ibscare.android.update;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.content.pm.PackageInstaller;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import com.ibscare.android.MainActivity;
import com.ibscare.android.R;
import com.ibscare.android.ui.ClinicalUi;
import com.ibscare.android.ui.TextSpec;
import com.ibscare.android.ui.UiCopy;

import java.io.IOException;

public final class LocalApkUpdateController {
    public static final int APK_PICKER_REQUEST_CODE = 3001;
    public static final int UNKNOWN_APP_SOURCE_SETTINGS_REQUEST_CODE = 3002;
    private static final String ACTION_INSTALL_STATUS =
            "com.ibscare.android.action.INSTALL_STATUS";

    private final Activity activity;
    private final PackageInstallerApkStager stager;
    private TextView updateStatus;
    private Uri pendingUpdateApkUri;

    public LocalApkUpdateController(Activity activity) {
        this.activity = activity;
        stager = new PackageInstallerApkStager(activity);
    }

    public View buildPanel() {
        LinearLayout panel = ClinicalUi.panel(activity, R.color.surface_secondary);
        panel.addView(text(UiCopy.UPDATE_PANEL_TITLE, 18, R.color.text_primary, 1));
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(text(UiCopy.UPDATE_PANEL_BODY, 15, R.color.text_secondary, 0));
        ClinicalUi.gap(activity, panel, 12);
        Button pickApkButton = ClinicalUi.primaryButton(activity, UiCopy.UPDATE_PICK_BUTTON);
        pickApkButton.setOnClickListener(view -> openApkPicker());
        panel.addView(pickApkButton);
        ClinicalUi.gap(activity, panel, 8);
        updateStatus = text(UiCopy.UPDATE_IDLE_STATUS, 14, R.color.text_secondary, 0);
        panel.addView(updateStatus);
        return panel;
    }

    public boolean onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == APK_PICKER_REQUEST_CODE) {
            handlePickedApk(resultCode, data);
            return true;
        }
        if (requestCode == UNKNOWN_APP_SOURCE_SETTINGS_REQUEST_CODE && pendingUpdateApkUri != null) {
            handleInstallPermissionReturn();
            return true;
        }
        return false;
    }

    public void handleIncomingIntent(Intent intent) {
        if (intent == null) {
            return;
        }
        if (ACTION_INSTALL_STATUS.equals(intent.getAction())) {
            handleInstallStatus(intent);
            return;
        }
        if (Intent.ACTION_SEND.equals(intent.getAction())) {
            Uri apkUri = sharedApkUri(intent);
            if (apkUri != null) {
                requestLocalApkUpdate(apkUri);
            }
        }
    }

    private void handlePickedApk(int resultCode, Intent data) {
        if (resultCode == Activity.RESULT_OK && data != null && data.getData() != null) {
            Uri apkUri = data.getData();
            persistReadPermissionIfPossible(data, apkUri);
            requestLocalApkUpdate(apkUri);
            return;
        }
        updateUpdateStatus("APK 선택이 취소되었습니다.");
    }

    private void handleInstallPermissionReturn() {
        if (canRequestPackageInstalls()) {
            requestLocalApkUpdate(pendingUpdateApkUri);
            return;
        }
        updateUpdateStatus("아직 APK 설치 요청 권한이 허용되지 않았습니다.");
    }

    private void openApkPicker() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT)
                .addCategory(Intent.CATEGORY_OPENABLE)
                .setType("application/vnd.android.package-archive")
                .putExtra(Intent.EXTRA_MIME_TYPES, new String[] {
                        "application/vnd.android.package-archive",
                        "application/octet-stream"
                });
        try {
            activity.startActivityForResult(intent, APK_PICKER_REQUEST_CODE);
        } catch (ActivityNotFoundException exception) {
            updateUpdateStatus("APK 파일을 선택할 수 있는 앱을 찾지 못했습니다.");
        }
    }

    private Uri sharedApkUri(Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri.class);
        }
        return intent.getParcelableExtra(Intent.EXTRA_STREAM);
    }

    private void persistReadPermissionIfPossible(Intent data, Uri apkUri) {
        int takeFlags = data.getFlags() & Intent.FLAG_GRANT_READ_URI_PERMISSION;
        if (takeFlags == 0) {
            return;
        }
        try {
            activity.getContentResolver().takePersistableUriPermission(
                    apkUri,
                    Intent.FLAG_GRANT_READ_URI_PERMISSION);
        } catch (SecurityException ignored) {
        }
    }

    private void requestLocalApkUpdate(Uri apkUri) {
        pendingUpdateApkUri = apkUri;
        LocalApkUpdatePolicy.StartAction action =
                LocalApkUpdatePolicy.startAction(apkUri != null, canRequestPackageInstalls());
        if (action == LocalApkUpdatePolicy.StartAction.REQUEST_INSTALL_PERMISSION) {
            showInstallPermissionDialog();
            return;
        }
        if (action == LocalApkUpdatePolicy.StartAction.STAGE_APK) {
            installApkFromUri(apkUri);
        }
    }

    private boolean canRequestPackageInstalls() {
        return activity.getPackageManager().canRequestPackageInstalls();
    }

    private void showInstallPermissionDialog() {
        updateUpdateStatus("Android 설정에서 APK 설치 요청 권한을 허용해야 합니다.");
        new AlertDialog.Builder(activity)
                .setTitle(UiCopy.UPDATE_INSTALL_PERMISSION_TITLE)
                .setMessage(UiCopy.UPDATE_INSTALL_PERMISSION_BODY)
                .setPositiveButton("설정 열기", (dialog, which) -> openUnknownAppSourceSettings())
                .setNegativeButton("취소", null)
                .show();
    }

    private void openUnknownAppSourceSettings() {
        Intent intent = new Intent(
                Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                Uri.parse("package:" + activity.getPackageName()));
        try {
            activity.startActivityForResult(intent, UNKNOWN_APP_SOURCE_SETTINGS_REQUEST_CODE);
        } catch (ActivityNotFoundException exception) {
            updateUpdateStatus("설치 권한 설정 화면을 열지 못했습니다.");
        }
    }

    private void installApkFromUri(Uri apkUri) {
        try {
            stager.stage(apkUri, this::installStatusSender);
            updateUpdateStatus("Android 설치 확인 화면을 준비했습니다.");
        } catch (IOException | RuntimeException exception) {
            updateUpdateStatus("APK 업데이트 요청 실패: "
                    + LocalApkUpdatePolicy.exceptionMessage(exception));
        }
    }

    private android.content.IntentSender installStatusSender(int sessionId) {
        Intent intent = new Intent(activity, MainActivity.class)
                .setAction(ACTION_INSTALL_STATUS)
                .setFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            flags |= PendingIntent.FLAG_MUTABLE;
        }
        return PendingIntent.getActivity(activity, sessionId, intent, flags).getIntentSender();
    }

    private void handleInstallStatus(Intent intent) {
        LocalApkUpdatePolicy.InstallerOutcome outcome = installerOutcome(intent);
        String statusMessage = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
        if (LocalApkUpdatePolicy.shouldOpenConfirmation(outcome)) {
            openInstallConfirmation(intent);
            return;
        }
        if (LocalApkUpdatePolicy.isSuccessful(outcome)) {
            pendingUpdateApkUri = null;
            updateUpdateStatus("APK 업데이트 설치 요청이 완료되었습니다.");
            return;
        }
        updateUpdateStatus(LocalApkUpdatePolicy.failureMessage(outcome, statusMessage));
    }

    private LocalApkUpdatePolicy.InstallerOutcome installerOutcome(Intent intent) {
        int status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE);
        switch (status) {
            case PackageInstaller.STATUS_PENDING_USER_ACTION:
                return LocalApkUpdatePolicy.InstallerOutcome.PENDING_USER_ACTION;
            case PackageInstaller.STATUS_SUCCESS:
                return LocalApkUpdatePolicy.InstallerOutcome.SUCCESS;
            case PackageInstaller.STATUS_FAILURE_ABORTED:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_ABORTED;
            case PackageInstaller.STATUS_FAILURE_BLOCKED:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_BLOCKED;
            case PackageInstaller.STATUS_FAILURE_CONFLICT:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_CONFLICT;
            case PackageInstaller.STATUS_FAILURE_INCOMPATIBLE:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_INCOMPATIBLE;
            case PackageInstaller.STATUS_FAILURE_INVALID:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_INVALID;
            case PackageInstaller.STATUS_FAILURE_STORAGE:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_STORAGE;
            default:
                return LocalApkUpdatePolicy.InstallerOutcome.FAILURE_UNKNOWN;
        }
    }

    private void openInstallConfirmation(Intent intent) {
        Intent confirmationIntent = installConfirmationIntent(intent);
        if (confirmationIntent == null) {
            updateUpdateStatus("Android 설치 확인 화면을 열 수 없습니다.");
            return;
        }
        try {
            activity.startActivity(confirmationIntent);
            updateUpdateStatus("Android 설치 확인 화면을 열었습니다.");
        } catch (ActivityNotFoundException exception) {
            updateUpdateStatus("Android 설치 확인 화면을 열지 못했습니다.");
        }
    }

    private Intent installConfirmationIntent(Intent intent) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return intent.getParcelableExtra(Intent.EXTRA_INTENT, Intent.class);
        }
        return intent.getParcelableExtra(Intent.EXTRA_INTENT);
    }

    private void updateUpdateStatus(String value) {
        if (updateStatus != null) {
            updateStatus.setText(value);
        }
        Toast.makeText(activity, value, Toast.LENGTH_SHORT).show();
    }

    private TextView text(String value, int sizeSp, int colorRes, int style) {
        return ClinicalUi.text(activity, TextSpec.builder(value)
                .sizeSp(sizeSp)
                .colorRes(colorRes)
                .style(style)
                .build());
    }
}
