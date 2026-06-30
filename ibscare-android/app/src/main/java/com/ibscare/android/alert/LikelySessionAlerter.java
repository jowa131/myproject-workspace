package com.ibscare.android.alert;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.pm.PackageManager;
import android.os.Build;

import com.ibscare.android.session.BowelSessionLikelihoodResult;
import com.ibscare.android.ui.UiCopy;

public final class LikelySessionAlerter {
    private static final int PERMISSION_REQUEST_CODE = 2001;

    private final Activity activity;

    public LikelySessionAlerter(Activity activity) {
        this.activity = activity;
    }

    public void prepare() {
        LikelySessionNotifier.ensureChannels(activity);
        requestNotificationPermission();
    }

    public void show(BowelSessionLikelihoodResult likelihood, Runnable onConfirm, Runnable onFalsePositive) {
        showDialog(likelihood, onConfirm, onFalsePositive);
        LikelySessionNotifier.postLikelySession(activity, likelihood);
    }

    private void showDialog(
            BowelSessionLikelihoodResult likelihood,
            Runnable onConfirm,
            Runnable onFalsePositive) {
        if (activity.isFinishing()) {
            return;
        }
        String message = UiCopy.SESSION_ALERT_BODY + "\n\n" + likelihood.summary();
        new AlertDialog.Builder(activity)
                .setTitle(UiCopy.SESSION_ALERT_TITLE)
                .setMessage(message)
                .setPositiveButton(UiCopy.SESSION_ALERT_CONFIRM, (dialog, which) -> onConfirm.run())
                .setNegativeButton(UiCopy.SESSION_ALERT_FALSE_POSITIVE,
                        (dialog, which) -> onFalsePositive.run())
                .show();
    }

    private void requestNotificationPermission() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return;
        }
        if (activity.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED) {
            return;
        }
        activity.requestPermissions(
                new String[] {Manifest.permission.POST_NOTIFICATIONS},
                PERMISSION_REQUEST_CODE);
    }
}
