package com.ibscare.android.session;

public final class MotionFeatures {
    private final int stationaryMinutes;
    private final boolean screenActive;
    private final boolean postureStable;
    private final boolean seatedPostureLikely;
    private final boolean sitTransitionLikely;
    private final boolean handheldViewingLikely;
    private final boolean windowedPostureLikely;
    private final boolean personalPatternLikely;
    private final boolean falsePositivePatternLikely;
    private final boolean usualBowelWindow;
    private final boolean movingLocation;
    private final double accelerationVariance;
    private final double orientationChangeRate;
    private final String suggestedTime;

    private MotionFeatures(Builder builder) {
        if (builder.stationaryMinutes < 0) {
            throw new IllegalArgumentException("stationaryMinutes must be positive");
        }
        if (builder.accelerationVariance < 0.0d) {
            throw new IllegalArgumentException("accelerationVariance must be positive");
        }
        if (builder.orientationChangeRate < 0.0d) {
            throw new IllegalArgumentException("orientationChangeRate must be positive");
        }
        stationaryMinutes = builder.stationaryMinutes;
        screenActive = builder.screenActive;
        postureStable = builder.postureStable;
        seatedPostureLikely = builder.seatedPostureLikely;
        sitTransitionLikely = builder.sitTransitionLikely;
        handheldViewingLikely = builder.handheldViewingLikely;
        windowedPostureLikely = builder.windowedPostureLikely;
        personalPatternLikely = builder.personalPatternLikely;
        falsePositivePatternLikely = builder.falsePositivePatternLikely;
        usualBowelWindow = builder.usualBowelWindow;
        movingLocation = builder.movingLocation;
        accelerationVariance = builder.accelerationVariance;
        orientationChangeRate = builder.orientationChangeRate;
        suggestedTime = builder.suggestedTime;
    }

    public static Builder builder(String suggestedTime) {
        return new Builder(suggestedTime);
    }

    public int stationaryMinutes() {
        return stationaryMinutes;
    }

    public boolean screenActive() {
        return screenActive;
    }

    public boolean postureStable() {
        return postureStable;
    }

    public boolean seatedPostureLikely() {
        return seatedPostureLikely;
    }

    public boolean sitTransitionLikely() {
        return sitTransitionLikely;
    }

    public boolean handheldViewingLikely() {
        return handheldViewingLikely;
    }

    public boolean windowedPostureLikely() {
        return windowedPostureLikely;
    }

    public boolean personalPatternLikely() {
        return personalPatternLikely;
    }

    public boolean falsePositivePatternLikely() {
        return falsePositivePatternLikely;
    }

    public boolean usualBowelWindow() {
        return usualBowelWindow;
    }

    public boolean movingLocation() {
        return movingLocation;
    }

    public double accelerationVariance() {
        return accelerationVariance;
    }

    public double orientationChangeRate() {
        return orientationChangeRate;
    }

    public String suggestedTime() {
        return suggestedTime;
    }

    public MotionFeatures withMovingLocation(boolean moving) {
        return MotionFeatures.builder(suggestedTime)
                .stationaryMinutes(stationaryMinutes)
                .screenActive(screenActive)
                .postureStable(postureStable)
                .seatedPostureLikely(seatedPostureLikely)
                .sitTransitionLikely(sitTransitionLikely)
                .handheldViewingLikely(handheldViewingLikely)
                .windowedPostureLikely(windowedPostureLikely)
                .personalPatternLikely(personalPatternLikely)
                .falsePositivePatternLikely(falsePositivePatternLikely)
                .usualBowelWindow(usualBowelWindow)
                .accelerationVariance(accelerationVariance)
                .orientationChangeRate(orientationChangeRate)
                .movingLocation(moving)
                .build();
    }

    public MotionFeatures withPersonalPattern(boolean likely) {
        return MotionFeatures.builder(suggestedTime)
                .stationaryMinutes(stationaryMinutes)
                .screenActive(screenActive)
                .postureStable(postureStable)
                .seatedPostureLikely(seatedPostureLikely)
                .sitTransitionLikely(sitTransitionLikely)
                .handheldViewingLikely(handheldViewingLikely)
                .windowedPostureLikely(windowedPostureLikely)
                .personalPatternLikely(likely)
                .falsePositivePatternLikely(falsePositivePatternLikely)
                .usualBowelWindow(usualBowelWindow)
                .accelerationVariance(accelerationVariance)
                .orientationChangeRate(orientationChangeRate)
                .movingLocation(movingLocation)
                .build();
    }

    public MotionFeatures withFalsePositivePattern(boolean likely) {
        return MotionFeatures.builder(suggestedTime)
                .stationaryMinutes(stationaryMinutes)
                .screenActive(screenActive)
                .postureStable(postureStable)
                .seatedPostureLikely(seatedPostureLikely)
                .sitTransitionLikely(sitTransitionLikely)
                .handheldViewingLikely(handheldViewingLikely)
                .windowedPostureLikely(windowedPostureLikely)
                .personalPatternLikely(personalPatternLikely)
                .falsePositivePatternLikely(likely)
                .usualBowelWindow(usualBowelWindow)
                .accelerationVariance(accelerationVariance)
                .orientationChangeRate(orientationChangeRate)
                .movingLocation(movingLocation)
                .build();
    }

    public static final class Builder {
        private final String suggestedTime;
        private int stationaryMinutes;
        private boolean screenActive;
        private boolean postureStable;
        private boolean seatedPostureLikely;
        private boolean sitTransitionLikely;
        private boolean handheldViewingLikely;
        private boolean windowedPostureLikely;
        private boolean personalPatternLikely;
        private boolean falsePositivePatternLikely;
        private boolean usualBowelWindow;
        private boolean movingLocation;
        private double accelerationVariance = 1.0d;
        private double orientationChangeRate;

        private Builder(String suggestedTime) {
            this.suggestedTime = suggestedTime;
        }

        public Builder stationaryMinutes(int value) {
            stationaryMinutes = value;
            return this;
        }

        public Builder screenActive(boolean value) {
            screenActive = value;
            return this;
        }

        public Builder postureStable(boolean value) {
            postureStable = value;
            return this;
        }

        public Builder seatedPostureLikely(boolean value) {
            seatedPostureLikely = value;
            return this;
        }

        public Builder sitTransitionLikely(boolean value) {
            sitTransitionLikely = value;
            return this;
        }

        public Builder handheldViewingLikely(boolean value) {
            handheldViewingLikely = value;
            return this;
        }

        public Builder windowedPostureLikely(boolean value) {
            windowedPostureLikely = value;
            return this;
        }

        public Builder personalPatternLikely(boolean value) {
            personalPatternLikely = value;
            return this;
        }

        public Builder falsePositivePatternLikely(boolean value) {
            falsePositivePatternLikely = value;
            return this;
        }

        public Builder usualBowelWindow(boolean value) {
            usualBowelWindow = value;
            return this;
        }

        public Builder movingLocation(boolean value) {
            movingLocation = value;
            return this;
        }

        public Builder accelerationVariance(double value) {
            accelerationVariance = value;
            return this;
        }

        public Builder orientationChangeRate(double value) {
            orientationChangeRate = value;
            return this;
        }

        public MotionFeatures build() {
            return new MotionFeatures(this);
        }
    }
}
