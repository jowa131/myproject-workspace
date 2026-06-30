package com.ibscare.android.session;

public final class PromptCooldownGate {
    public static final long DEFAULT_COOLDOWN_MILLIS = 10L * 60L * 1000L;

    private final long cooldownMillis;
    private long lastPromptMillis = Long.MIN_VALUE;

    public PromptCooldownGate() {
        this(DEFAULT_COOLDOWN_MILLIS);
    }

    public PromptCooldownGate(long cooldownMillis) {
        if (cooldownMillis < 0L) {
            throw new IllegalArgumentException("cooldownMillis must be positive");
        }
        this.cooldownMillis = cooldownMillis;
    }

    public boolean canPrompt(long nowMillis) {
        return lastPromptMillis == Long.MIN_VALUE
                || nowMillis - lastPromptMillis >= cooldownMillis;
    }

    public void markPromptShown(long nowMillis) {
        lastPromptMillis = nowMillis;
    }
}
