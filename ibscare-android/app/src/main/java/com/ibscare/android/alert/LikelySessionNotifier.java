package com.ibscare.android.alert;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.drawable.Icon;
import android.os.Build;

import com.ibscare.android.MainActivity;
import com.ibscare.android.R;
import com.ibscare.android.service.BackgroundBowelDetectionService;
import com.ibscare.android.session.BowelSessionLikelihoodResult;
import com.ibscare.android.ui.UiCopy;

public final class LikelySessionNotifier {
    public static final String LIKELY_CHANNEL_ID = "likely_bowel_session";
    public static final String MONITORING_CHANNEL_ID = "background_bowel_detection";
    public static final int LIKELY_NOTIFICATION_ID = 1001;
    public static final int MONITORING_NOTIFICATION_ID = 1002;
    private static final int OPEN_REQUEST_CODE = 2;
    private static final int RECORD_REQUEST_CODE = 3;
    private static final int FALSE_POSITIVE_REQUEST_CODE = 4;

    private LikelySessionNotifier() {
    }

    public static void ensureChannels(Context context) {
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        NotificationChannel likelyChannel = new NotificationChannel(
                LIKELY_CHANNEL_ID,
                UiCopy.SESSION_ALERT_CHANNEL,
                NotificationManager.IMPORTANCE_HIGH);
        likelyChannel.setDescription(UiCopy.SESSION_ALERT_CHANNEL_DESCRIPTION);
        manager.createNotificationChannel(likelyChannel);

        NotificationChannel monitoringChannel = new NotificationChannel(
                MONITORING_CHANNEL_ID,
                UiCopy.MONITORING_CHANNEL,
                NotificationManager.IMPORTANCE_LOW);
        monitoringChannel.setDescription(UiCopy.MONITORING_CHANNEL_DESCRIPTION);
        manager.createNotificationChannel(monitoringChannel);
    }

    public static Notification monitoringNotification(Context context) {
        PendingIntent openIntent = PendingIntent.getActivity(
                context,
                0,
                new Intent(context, MainActivity.class)
                        .setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stopIntent = PendingIntent.getService(
                context,
                1,
                new Intent(context, BackgroundBowelDetectionService.class)
                        .setAction(BackgroundBowelDetectionService.ACTION_STOP),
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        Notification.Action stopAction = new Notification.Action.Builder(
                Icon.createWithResource(context, R.drawable.ic_notification),
                UiCopy.MONITORING_STOP,
                stopIntent).build();
        return new Notification.Builder(context, MONITORING_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(UiCopy.MONITORING_TITLE)
                .setContentText(UiCopy.MONITORING_BODY)
                .setContentIntent(openIntent)
                .setOngoing(true)
                .setShowWhen(true)
                .addAction(stopAction)
                .build();
    }

    public static void postLikelySession(Context context, BowelSessionLikelihoodResult likelihood) {
        if (!canPostNotifications(context)) {
            return;
        }
        NotificationManager manager = context.getSystemService(NotificationManager.class);
        if (manager == null) {
            return;
        }
        Notification notification = new Notification.Builder(context, LIKELY_CHANNEL_ID)
                .setSmallIcon(R.drawable.ic_notification)
                .setContentTitle(UiCopy.SESSION_ALERT_TITLE)
                .setContentText(UiCopy.SESSION_ALERT_NOTIFICATION + " " + likelihood.score0To100() + "점")
                .setContentIntent(openPendingSessionIntent(context))
                .setAutoCancel(true)
                .setShowWhen(true)
                .setWhen(System.currentTimeMillis())
                .addAction(notificationAction(
                        context,
                        UiCopy.SESSION_ALERT_FALSE_POSITIVE,
                        MainActivity.ACTION_FALSE_POSITIVE_PENDING_SESSION,
                        FALSE_POSITIVE_REQUEST_CODE))
                .addAction(notificationAction(
                        context,
                        UiCopy.SESSION_ALERT_RECORD_ACTION,
                        MainActivity.ACTION_RECORD_PENDING_SESSION,
                        RECORD_REQUEST_CODE))
                .build();
        manager.notify(LIKELY_NOTIFICATION_ID, notification);
    }

    private static PendingIntent openPendingSessionIntent(Context context) {
        return pendingSessionIntent(context, MainActivity.ACTION_OPEN_PENDING_SESSION, OPEN_REQUEST_CODE);
    }

    private static Notification.Action notificationAction(
            Context context,
            String title,
            String action,
            int requestCode) {
        return new Notification.Action.Builder(
                Icon.createWithResource(context, R.drawable.ic_notification),
                title,
                pendingSessionIntent(context, action, requestCode)).build();
    }

    private static PendingIntent pendingSessionIntent(Context context, String action, int requestCode) {
        Intent intent = new Intent(context, MainActivity.class)
                .setAction(action)
                .setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return PendingIntent.getActivity(
                context,
                requestCode,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    private static boolean canPostNotifications(Context context) {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                == PackageManager.PERMISSION_GRANTED;
    }
}
