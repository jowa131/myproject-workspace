package com.ibscare.android;

import android.hardware.Sensor;
import android.hardware.SensorEvent;

import com.ibscare.android.data.PersonalPatternStore;
import com.ibscare.android.session.AccelerometerSample;
import com.ibscare.android.session.FeatureSummaryBuffer;
import com.ibscare.android.session.MotionFeatures;
import com.ibscare.android.session.MotionSessionSampler;
import com.ibscare.android.session.OrientationSample;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

final class DeviceFeatureCoordinator {
    private final MotionSessionSampler sampler = new MotionSessionSampler();
    private final FeatureSummaryBuffer featureSummaryBuffer = new FeatureSummaryBuffer();
    private final PersonalPatternStore personalPatternStore;
    private final SimpleDateFormat timeFormat = new SimpleDateFormat("HH:mm", Locale.KOREA);

    DeviceFeatureCoordinator(PersonalPatternStore personalPatternStore) {
        this.personalPatternStore = personalPatternStore;
    }

    MotionFeatures idleFeatures() {
        return MotionFeatures.builder(timeFormat.format(new Date()))
                .screenActive(true)
                .build();
    }

    MotionFeatures sampleForReview(long nowMillis) {
        return sampler.sampleForReview(nowMillis);
    }

    MotionFeatures personalize(MotionFeatures features, boolean eligibleForLearning) {
        MotionFeatures personalized = features
                .withPersonalPattern(personalPatternStore.matches(features))
                .withFalsePositivePattern(personalPatternStore.matchesFalsePositive(features));
        if (eligibleForLearning) {
            featureSummaryBuffer.add(System.currentTimeMillis(), personalized);
        }
        return personalized;
    }

    void rememberPending(MotionFeatures features) {
        featureSummaryBuffer.add(System.currentTimeMillis(), personalize(features, false));
    }

    void learnFromRecentCandidate(long nowMillis) {
        MotionFeatures learned = featureSummaryBuffer.latestCandidateOrNull(nowMillis);
        if (learned != null) {
            personalPatternStore.learnPositive(learned);
        }
    }

    void learnFalsePositive(MotionFeatures features) {
        personalPatternStore.learnNegative(features);
    }

    MotionFeatures sensorFeatures(SensorEvent event, boolean screenActive) {
        long nowMillis = System.currentTimeMillis();
        if (event.sensor.getType() == Sensor.TYPE_GRAVITY) {
            return sampler.acceptGravity(
                    OrientationSample.fromGravity(event.values[0], event.values[1], event.values[2], nowMillis),
                    screenActive);
        }
        if (event.sensor.getType() == Sensor.TYPE_ACCELEROMETER) {
            return sampler.accept(
                    AccelerometerSample.fromValues(event.values, nowMillis),
                    screenActive);
        }
        return null;
    }
}
