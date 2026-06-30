package com.ibscare.android.data;

import com.ibscare.android.session.MotionFeatures;

import java.util.Optional;

public final class PendingBowelSession {
    private final String suggestedTime;
    private final int score0To100;
    private final String summary;
    private final MotionFeatures features;

    public PendingBowelSession(String suggestedTime, int score0To100, String summary) {
        this(suggestedTime, score0To100, summary, null);
    }

    public PendingBowelSession(
            String suggestedTime,
            int score0To100,
            String summary,
            MotionFeatures features) {
        this.suggestedTime = suggestedTime;
        this.score0To100 = score0To100;
        this.summary = summary;
        this.features = features;
    }

    public String suggestedTime() {
        return suggestedTime;
    }

    public int score0To100() {
        return score0To100;
    }

    public String summary() {
        return summary;
    }

    public Optional<MotionFeatures> features() {
        return Optional.ofNullable(features);
    }
}
