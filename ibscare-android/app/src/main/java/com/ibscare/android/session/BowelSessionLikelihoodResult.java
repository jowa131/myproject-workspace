package com.ibscare.android.session;

public final class BowelSessionLikelihoodResult {
    private final int score0To100;
    private final boolean shouldPrompt;
    private final String suggestedTime;
    private final String summary;

    private BowelSessionLikelihoodResult(Builder builder) {
        score0To100 = Math.max(0, Math.min(100, builder.score0To100));
        shouldPrompt = builder.shouldPrompt;
        suggestedTime = builder.suggestedTime;
        summary = builder.summary;
    }

    public static Builder builder(String suggestedTime) {
        return new Builder(suggestedTime);
    }

    public int score0To100() {
        return score0To100;
    }

    public boolean shouldPrompt() {
        return shouldPrompt;
    }

    public String suggestedTime() {
        return suggestedTime;
    }

    public String summary() {
        return summary;
    }

    public static final class Builder {
        private final String suggestedTime;
        private int score0To100;
        private boolean shouldPrompt;
        private String summary = "";

        private Builder(String suggestedTime) {
            this.suggestedTime = suggestedTime;
        }

        public Builder score0To100(int value) {
            score0To100 = value;
            return this;
        }

        public Builder shouldPrompt(boolean value) {
            shouldPrompt = value;
            return this;
        }

        public Builder summary(String value) {
            summary = value;
            return this;
        }

        public BowelSessionLikelihoodResult build() {
            return new BowelSessionLikelihoodResult(this);
        }
    }
}
