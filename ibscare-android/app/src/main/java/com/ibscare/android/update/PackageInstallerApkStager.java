package com.ibscare.android.update;

import android.app.Activity;
import android.content.IntentSender;
import android.content.pm.PackageInstaller;
import android.net.Uri;
import android.os.Build;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.function.IntFunction;

final class PackageInstallerApkStager {
    private static final int COPY_BUFFER_BYTES = 32 * 1024;

    private final Activity activity;

    PackageInstallerApkStager(Activity activity) {
        this.activity = activity;
    }

    void stage(Uri apkUri, IntFunction<IntentSender> statusSenderFactory) throws IOException {
        PackageInstaller packageInstaller = activity.getPackageManager().getPackageInstaller();
        int sessionId = -1;
        try {
            sessionId = packageInstaller.createSession(sessionParams());
            try (PackageInstaller.Session session = packageInstaller.openSession(sessionId)) {
                writeApkToSession(session, apkUri);
                session.commit(statusSenderFactory.apply(sessionId));
            }
        } catch (IOException | RuntimeException exception) {
            abandonSession(packageInstaller, sessionId);
            throw exception;
        }
    }

    private PackageInstaller.SessionParams sessionParams() {
        PackageInstaller.SessionParams params =
                new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
        params.setAppPackageName(activity.getPackageName());
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            params.setRequireUserAction(PackageInstaller.SessionParams.USER_ACTION_REQUIRED);
        }
        return params;
    }

    private void writeApkToSession(PackageInstaller.Session session, Uri apkUri) throws IOException {
        try (InputStream input = activity.getContentResolver().openInputStream(apkUri);
                OutputStream output = session.openWrite("ibs-care-update.apk", 0, -1)) {
            if (input == null) {
                throw new IOException("APK 파일을 열 수 없습니다.");
            }
            copy(input, output);
            session.fsync(output);
        }
    }

    private void copy(InputStream input, OutputStream output) throws IOException {
        byte[] buffer = new byte[COPY_BUFFER_BYTES];
        int read;
        while ((read = input.read(buffer)) != -1) {
            output.write(buffer, 0, read);
        }
    }

    private void abandonSession(PackageInstaller packageInstaller, int sessionId) {
        if (sessionId < 0) {
            return;
        }
        try {
            packageInstaller.abandonSession(sessionId);
        } catch (RuntimeException ignored) {
        }
    }
}
