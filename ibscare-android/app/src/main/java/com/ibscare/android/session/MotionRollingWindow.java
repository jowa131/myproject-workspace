package com.ibscare.android.session;

import java.util.ArrayDeque;
import java.util.Deque;

final class MotionRollingWindow {
    private static final long RETENTION_MILLIS = 15 * 60_000L;
    private final Deque<Entry> entries = new ArrayDeque<>();

    void addAcceleration(long capturedAtMillis, double accelerationDelta) {
        entries.addLast(new Entry(capturedAtMillis, accelerationDelta, 0.0d, false));
        prune(capturedAtMillis);
    }

    void addOrientation(long capturedAtMillis, double orientationDelta) {
        entries.addLast(new Entry(capturedAtMillis, 0.0d, orientationDelta, true));
        prune(capturedAtMillis);
    }

    MotionWindowSummary summarize(long nowMillis, long windowMillis) {
        prune(nowMillis);
        int count = 0;
        int orientationCount = 0;
        double accelerationSum = 0.0d;
        double orientationSum = 0.0d;
        long earliest = nowMillis - windowMillis;
        for (Entry entry : entries) {
            if (entry.capturedAtMillis < earliest) {
                continue;
            }
            count++;
            accelerationSum += entry.accelerationDelta;
            if (entry.hasOrientation) {
                orientationCount++;
                orientationSum += entry.orientationDelta;
            }
        }
        if (count == 0) {
            return new MotionWindowSummary(0, 0, 1.0d, 0.0d);
        }
        double averageOrientation = orientationCount == 0 ? 1.0d : orientationSum / orientationCount;
        return new MotionWindowSummary(count, orientationCount, accelerationSum / count, averageOrientation);
    }

    private void prune(long nowMillis) {
        long oldest = nowMillis - RETENTION_MILLIS;
        while (!entries.isEmpty() && entries.peekFirst().capturedAtMillis < oldest) {
            entries.removeFirst();
        }
    }

    private static final class Entry {
        private final long capturedAtMillis;
        private final double accelerationDelta;
        private final double orientationDelta;
        private final boolean hasOrientation;

        private Entry(
                long capturedAtMillis,
                double accelerationDelta,
                double orientationDelta,
                boolean hasOrientation) {
            this.capturedAtMillis = capturedAtMillis;
            this.accelerationDelta = accelerationDelta;
            this.orientationDelta = orientationDelta;
            this.hasOrientation = hasOrientation;
        }
    }
}
