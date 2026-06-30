package com.ibscare.android.service;

import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;

import com.ibscare.android.alert.LikelySessionNotifier;
import com.ibscare.android.data.PersonalPatternStore;
import com.ibscare.android.data.PendingBowelSessionStore;
import com.ibscare.android.session.AccelerometerSample;
import com.ibscare.android.session.BowelSessionLikelihoodResult;
import com.ibscare.android.session.BowelSessionScorer;
import com.ibscare.android.session.MotionFeatures;
import com.ibscare.android.session.MotionSessionSampler;
import com.ibscare.android.session.OrientationSample;
import com.ibscare.android.session.PromptCooldownGate;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public final class BackgroundBowelDetectionService extends Service implements SensorEventListener {
    public static final String ACTION_START = "com.ibscare.android.action.START_BACKGROUND_DETECTION";
    public static final String ACTION_STOP = "com.ibscare.android.action.STOP_BACKGROUND_DETECTION";

    private final MotionSessionSampler sampler = new MotionSessionSampler();
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.KOREA);
    private PersonalPatternStore personalPatternStore;
    private PendingBowelSessionStore pendingStore;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Sensor gravitySensor;
    private final PromptCooldownGate promptCooldownGate = new PromptCooldownGate();

    @Override
    public void onCreate() {
        super.onCreate();
        personalPatternStore = new PersonalPatternStore(this);
        pendingStore = new PendingBowelSessionStore(this);
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        accelerometer = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        gravitySensor = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_GRAVITY);
        LikelySessionNotifier.ensureChannels(this);
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopMonitoring();
            return START_NOT_STICKY;
        }
        startInForeground();
        registerSensor();
        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        unregisterSensor();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        MotionFeatures features = sensorFeatures(event);
        if (features == null) {
            return;
        }
        if (!BowelSessionScorer.hasCandidateEvidence(features) || pendingStore.isActivityVisible()) {
            return;
        }
        BowelSessionLikelihoodResult likelihood = BowelSessionScorer.evaluate(features);
        if (!likelihood.shouldPrompt() || !promptCooldownGate.canPrompt(System.currentTimeMillis())) {
            return;
        }
        promptIfEligible(features);
    }

    private void promptIfEligible(MotionFeatures features) {
        BowelSessionLikelihoodResult likelihood = BowelSessionScorer.evaluate(features);
        if (!likelihood.shouldPrompt() || !promptCooldownGate.canPrompt(System.currentTimeMillis())) {
            return;
        }
        promptCooldownGate.markPromptShown(System.currentTimeMillis());
        pendingStore.save(today(), likelihood, features);
        LikelySessionNotifier.postLikelySession(this, likelihood);
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    private void startInForeground() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(
                    LikelySessionNotifier.MONITORING_NOTIFICATION_ID,
                    LikelySessionNotifier.monitoringNotification(this),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
            return;
        }
        startForeground(
                LikelySessionNotifier.MONITORING_NOTIFICATION_ID,
                LikelySessionNotifier.monitoringNotification(this));
    }

    private void registerSensor() {
        if (sensorManager != null && accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_NORMAL);
        }
        if (sensorManager != null && gravitySensor != null) {
            sensorManager.registerListener(this, gravitySensor, SensorManager.SENSOR_DELAY_NORMAL);
        }
    }

    private void unregisterSensor() {
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
    }

    private boolean isScreenInteractive() {
        PowerManager powerManager = getSystemService(PowerManager.class);
        return powerManager != null && powerManager.isInteractive();
    }

    private MotionFeatures sensorFeatures(SensorEvent event) {
        long nowMillis = System.currentTimeMillis();
        MotionFeatures features;
        if (event.sensor.getType() == Sensor.TYPE_GRAVITY) {
            features = sampler.acceptGravity(
                    OrientationSample.fromGravity(event.values[0], event.values[1], event.values[2], nowMillis),
                    isScreenInteractive());
        } else if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            features = sampler.accept(
                    AccelerometerSample.fromValues(event.values, nowMillis),
                    isScreenInteractive());
        } else {
            return null;
        }
        return features
                .withPersonalPattern(personalPatternStore.matches(features))
                .withFalsePositivePattern(personalPatternStore.matchesFalsePositive(features));
    }

    private void stopMonitoring() {
        unregisterSensor();
        stopForeground(STOP_FOREGROUND_REMOVE);
        stopSelf();
    }

    private String today() {
        return dateFormat.format(new Date());
    }
}
