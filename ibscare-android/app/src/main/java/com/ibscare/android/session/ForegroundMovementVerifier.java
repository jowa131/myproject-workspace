package com.ibscare.android.session;

import android.Manifest;
import android.annotation.TargetApi;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.location.Location;
import android.location.LocationManager;
import android.os.Build;
import android.os.CancellationSignal;
import android.os.Handler;
import android.os.Looper;

public final class ForegroundMovementVerifier {
    private static final long LOCATION_CHECK_TIMEOUT_MILLIS = 8_000L;
    private static final long LOCATION_RETRY_DELAY_MILLIS = 1_000L;
    private static final long STALE_LOCATION_TOLERANCE_MILLIS = 1_000L;

    private final Activity activity;
    private final LocationManager locationManager;
    private LocationMovementSnapshot previousLocation;
    private CancellationSignal cancellationSignal;
    private Runnable onStationary;
    private Runnable onMoving;
    private boolean checkInFlight;
    private String provider;
    private long checkStartedAtMillis;

    public ForegroundMovementVerifier(Activity activity, LocationManager locationManager) {
        this.activity = activity;
        this.locationManager = locationManager;
    }

    public void verify(Runnable onStationary, Runnable onMoving) {
        if (checkInFlight) {
            return;
        }
        this.onStationary = onStationary;
        this.onMoving = onMoving;
        if (!canCheckLocation()) {
            completeStationary();
            return;
        }
        provider = bestLocationProvider();
        if (provider == null) {
            completeStationary();
            return;
        }
        checkInFlight = true;
        checkStartedAtMillis = System.currentTimeMillis();
        cancellationSignal = new CancellationSignal();
        new Handler(Looper.getMainLooper()).postDelayed(() -> {
            if (!checkInFlight) {
                return;
            }
            cancellationSignal.cancel();
            finish(null);
        }, LOCATION_CHECK_TIMEOUT_MILLIS);
        requestLocation();
    }

    private boolean canCheckLocation() {
        return locationManager != null
                && Build.VERSION.SDK_INT >= Build.VERSION_CODES.R
                && hasLocationPermission();
    }

    private boolean hasLocationPermission() {
        return activity.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)
                == PackageManager.PERMISSION_GRANTED
                || activity.checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    @TargetApi(Build.VERSION_CODES.R)
    private void requestLocation() {
        if (!checkInFlight || provider == null) {
            return;
        }
        if (!hasLocationPermission()) {
            finish(null);
            return;
        }
        try {
            locationManager.getCurrentLocation(
                    provider,
                    cancellationSignal,
                    command -> new Handler(Looper.getMainLooper()).post(command),
                    this::finish);
        } catch (SecurityException exception) {
            finish(null);
        }
    }

    private void finish(Location location) {
        if (!checkInFlight) {
            return;
        }
        if (isStaleLocation(location)) {
            new Handler(Looper.getMainLooper()).postDelayed(
                    this::requestLocation,
                    LOCATION_RETRY_DELAY_MILLIS);
            return;
        }
        boolean moving = candidateIsMoving(location);
        checkInFlight = false;
        provider = null;
        cancellationSignal = null;
        if (moving) {
            onMoving.run();
            return;
        }
        completeStationary();
    }

    private boolean isStaleLocation(Location location) {
        if (location == null) {
            return false;
        }
        long oldestAcceptedTime = checkStartedAtMillis - STALE_LOCATION_TOLERANCE_MILLIS;
        return location.getTime() < oldestAcceptedTime;
    }

    private boolean candidateIsMoving(Location location) {
        LocationMovementSnapshot latest = LocationMovementSnapshots.from(location);
        boolean moving = CandidateMovementGate.isMoving(previousLocation, latest);
        if (latest != null) {
            previousLocation = latest;
        }
        return moving;
    }

    private String bestLocationProvider() {
        try {
            if (locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)) {
                return LocationManager.GPS_PROVIDER;
            }
            if (locationManager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) {
                return LocationManager.NETWORK_PROVIDER;
            }
        } catch (RuntimeException ignored) {
            return null;
        }
        return null;
    }

    private void completeStationary() {
        onStationary.run();
    }
}
