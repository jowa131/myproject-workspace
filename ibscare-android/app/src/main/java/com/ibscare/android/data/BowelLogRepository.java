package com.ibscare.android.data;

import android.content.Context;
import android.content.SharedPreferences;

public final class BowelLogRepository {
    private static final String PREFS = "ibs-care-android-local";
    private static final String KEY_DATE = "last_entry_date";
    private static final String KEY_TIME = "last_entry_time";
    private static final String KEY_BRISTOL = "last_entry_bristol";
    private static final String KEY_COMPLETE = "last_entry_complete";
    private static final String KEY_URGENCY = "last_entry_urgency";
    private static final String KEY_BLOOD = "last_entry_blood";
    private static final String KEY_COUNT = "today_count";

    private final SharedPreferences preferences;

    public BowelLogRepository(Context context) {
        preferences = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    public boolean hasMovementToday(String date) {
        return date.equals(preferences.getString(KEY_DATE, ""));
    }

    public int countToday(String date) {
        if (!hasMovementToday(date)) {
            return 0;
        }
        return preferences.getInt(KEY_COUNT, 0);
    }

    public void save(BowelLogEntry entry) {
        int nextCount = hasMovementToday(entry.date()) ? preferences.getInt(KEY_COUNT, 0) + 1 : 1;
        preferences.edit()
                .putString(KEY_DATE, entry.date())
                .putString(KEY_TIME, entry.time())
                .putString(KEY_BRISTOL, entry.bristolType())
                .putBoolean(KEY_COMPLETE, entry.completeSpontaneous())
                .putBoolean(KEY_URGENCY, entry.urgency())
                .putBoolean(KEY_BLOOD, entry.bloodOrBlackStool())
                .putInt(KEY_COUNT, nextCount)
                .apply();
    }

    public String lastSummary(String date) {
        if (!hasMovementToday(date)) {
            return "오늘 저장된 배변 기록이 없습니다.";
        }
        String time = preferences.getString(KEY_TIME, "");
        String bristol = preferences.getString(KEY_BRISTOL, "");
        return "오늘 " + countToday(date) + "회 저장됨 · " + time + " · Bristol " + bristol;
    }
}
