package com.ibscare.android.data;

import android.content.Context;
import android.content.SharedPreferences;

import com.ibscare.android.session.BowelSessionLikelihoodResult;
import com.ibscare.android.session.MotionFeatures;

public final class PendingBowelSessionStore {
    private static final String PREFS = "ibs-care-pending-session";
    private static final String KEY_DATE = "date";
    private static final String KEY_TIME = "time";
    private static final String KEY_SCORE = "score";
    private static final String KEY_SUMMARY = "summary";
    private static final String KEY_ACTIVITY_VISIBLE = "activity_visible";
    private static final String KEY_HAS_FEATURES = "has_features";
    private static final String KEY_STATIONARY = "feature_stationary";
    private static final String KEY_SCREEN_ACTIVE = "feature_screen_active";
    private static final String KEY_POSTURE_STABLE = "feature_posture_stable";
    private static final String KEY_SEATED = "feature_seated";
    private static final String KEY_SIT_TRANSITION = "feature_sit_transition";
    private static final String KEY_HANDHELD = "feature_handheld";
    private static final String KEY_WINDOWED = "feature_windowed";
    private static final String KEY_PERSONAL = "feature_personal";
    private static final String KEY_FALSE_POSITIVE = "feature_false_positive";
    private static final String KEY_USUAL = "feature_usual";
    private static final String KEY_MOVING = "feature_moving";
    private static final String KEY_VARIANCE = "feature_variance";
    private static final String KEY_ORIENTATION = "feature_orientation";

    private final SharedPreferences preferences;

    public PendingBowelSessionStore(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public void save(String date, BowelSessionLikelihoodResult result) {
        save(date, result, null);
    }

    public void save(String date, BowelSessionLikelihoodResult result, MotionFeatures features) {
        SharedPreferences.Editor editor = preferences.edit()
                .putString(KEY_DATE, date)
                .putString(KEY_TIME, result.suggestedTime())
                .putInt(KEY_SCORE, result.score0To100())
                .putString(KEY_SUMMARY, result.summary());
        writeFeatures(editor, features).apply();
    }

    public PendingBowelSession load(String date) {
        if (!date.equals(preferences.getString(KEY_DATE, ""))) {
            return null;
        }
        return new PendingBowelSession(
                preferences.getString(KEY_TIME, ""),
                preferences.getInt(KEY_SCORE, 0),
                preferences.getString(KEY_SUMMARY, ""),
                readFeatures());
    }

    public void clear() {
        preferences.edit()
                .remove(KEY_DATE)
                .remove(KEY_TIME)
                .remove(KEY_SCORE)
                .remove(KEY_SUMMARY)
                .remove(KEY_HAS_FEATURES)
                .remove(KEY_STATIONARY)
                .remove(KEY_SCREEN_ACTIVE)
                .remove(KEY_POSTURE_STABLE)
                .remove(KEY_SEATED)
                .remove(KEY_SIT_TRANSITION)
                .remove(KEY_HANDHELD)
                .remove(KEY_WINDOWED)
                .remove(KEY_PERSONAL)
                .remove(KEY_FALSE_POSITIVE)
                .remove(KEY_USUAL)
                .remove(KEY_MOVING)
                .remove(KEY_VARIANCE)
                .remove(KEY_ORIENTATION)
                .apply();
    }

    public void setActivityVisible(boolean visible) {
        preferences.edit().putBoolean(KEY_ACTIVITY_VISIBLE, visible).apply();
    }

    public boolean isActivityVisible() {
        return preferences.getBoolean(KEY_ACTIVITY_VISIBLE, false);
    }

    private SharedPreferences.Editor writeFeatures(SharedPreferences.Editor editor, MotionFeatures features) {
        if (features == null) {
            return editor.putBoolean(KEY_HAS_FEATURES, false);
        }
        return editor.putBoolean(KEY_HAS_FEATURES, true)
                .putInt(KEY_STATIONARY, features.stationaryMinutes())
                .putBoolean(KEY_SCREEN_ACTIVE, features.screenActive())
                .putBoolean(KEY_POSTURE_STABLE, features.postureStable())
                .putBoolean(KEY_SEATED, features.seatedPostureLikely())
                .putBoolean(KEY_SIT_TRANSITION, features.sitTransitionLikely())
                .putBoolean(KEY_HANDHELD, features.handheldViewingLikely())
                .putBoolean(KEY_WINDOWED, features.windowedPostureLikely())
                .putBoolean(KEY_PERSONAL, features.personalPatternLikely())
                .putBoolean(KEY_FALSE_POSITIVE, features.falsePositivePatternLikely())
                .putBoolean(KEY_USUAL, features.usualBowelWindow())
                .putBoolean(KEY_MOVING, features.movingLocation())
                .putFloat(KEY_VARIANCE, (float) features.accelerationVariance())
                .putFloat(KEY_ORIENTATION, (float) features.orientationChangeRate());
    }

    private MotionFeatures readFeatures() {
        if (!preferences.getBoolean(KEY_HAS_FEATURES, false)) {
            return null;
        }
        return MotionFeatures.builder(preferences.getString(KEY_TIME, ""))
                .stationaryMinutes(preferences.getInt(KEY_STATIONARY, 0))
                .screenActive(preferences.getBoolean(KEY_SCREEN_ACTIVE, false))
                .postureStable(preferences.getBoolean(KEY_POSTURE_STABLE, false))
                .seatedPostureLikely(preferences.getBoolean(KEY_SEATED, false))
                .sitTransitionLikely(preferences.getBoolean(KEY_SIT_TRANSITION, false))
                .handheldViewingLikely(preferences.getBoolean(KEY_HANDHELD, false))
                .windowedPostureLikely(preferences.getBoolean(KEY_WINDOWED, false))
                .personalPatternLikely(preferences.getBoolean(KEY_PERSONAL, false))
                .falsePositivePatternLikely(preferences.getBoolean(KEY_FALSE_POSITIVE, false))
                .usualBowelWindow(preferences.getBoolean(KEY_USUAL, false))
                .movingLocation(preferences.getBoolean(KEY_MOVING, false))
                .accelerationVariance(preferences.getFloat(KEY_VARIANCE, 1.0f))
                .orientationChangeRate(preferences.getFloat(KEY_ORIENTATION, 0.0f))
                .build();
    }
}
