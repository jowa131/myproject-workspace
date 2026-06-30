package com.ibscare.android.data;

import android.content.Context;
import android.content.SharedPreferences;

import com.ibscare.android.session.MotionFeatures;

public final class PersonalPatternStore {
    private static final String PREFS = "ibs-care-android-personal-pattern";

    private final SharedPreferences preferences;

    public PersonalPatternStore(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public void learnPositive(MotionFeatures features) {
        PersonalPatternSnapshot snapshot = load().learnPositive(features);
        write(snapshot);
    }

    public void learnNegative(MotionFeatures features) {
        PersonalPatternSnapshot snapshot = load().learnNegative(features);
        write(snapshot);
    }

    public boolean matches(MotionFeatures features) {
        return load().matches(features);
    }

    public boolean matchesFalsePositive(MotionFeatures features) {
        return load().matchesFalsePositive(features);
    }

    private void write(PersonalPatternSnapshot snapshot) {
        preferences.edit()
                .putInt(PersonalPatternSnapshot.KEY_COUNT, snapshot.positiveCount())
                .putInt(PersonalPatternSnapshot.KEY_MIN_STATIONARY, snapshot.minimumStationaryMinutes())
                .putFloat(PersonalPatternSnapshot.KEY_VARIANCE, (float) snapshot.learnedVariance())
                .putBoolean(PersonalPatternSnapshot.KEY_POSTURE, snapshot.learnedPosture())
                .putInt(PersonalPatternSnapshot.KEY_NEGATIVE_COUNT, snapshot.negativeCount())
                .putInt(PersonalPatternSnapshot.KEY_NEGATIVE_MIN_STATIONARY,
                        snapshot.negativeMinimumStationaryMinutes())
                .putFloat(PersonalPatternSnapshot.KEY_NEGATIVE_VARIANCE,
                        (float) snapshot.negativeVariance())
                .putBoolean(PersonalPatternSnapshot.KEY_NEGATIVE_POSTURE, snapshot.negativePosture())
                .apply();
    }

    private PersonalPatternSnapshot load() {
        return PersonalPatternSnapshot.fromStored(
                preferences.getInt(PersonalPatternSnapshot.KEY_COUNT, 0),
                preferences.getInt(PersonalPatternSnapshot.KEY_MIN_STATIONARY, 1),
                preferences.getFloat(PersonalPatternSnapshot.KEY_VARIANCE, 1.0f),
                preferences.getBoolean(PersonalPatternSnapshot.KEY_POSTURE, false),
                preferences.getInt(PersonalPatternSnapshot.KEY_NEGATIVE_COUNT, 0),
                preferences.getInt(PersonalPatternSnapshot.KEY_NEGATIVE_MIN_STATIONARY, 1),
                preferences.getFloat(PersonalPatternSnapshot.KEY_NEGATIVE_VARIANCE, 1.0f),
                preferences.getBoolean(PersonalPatternSnapshot.KEY_NEGATIVE_POSTURE, false));
    }
}
