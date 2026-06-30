package com.ibscare.android.session;

import java.util.ArrayDeque;
import java.util.Deque;

public final class FeatureSummaryBuffer {
    private static final long RETENTION_MILLIS = 15 * 60_000L;
    private final Deque<Entry> entries = new ArrayDeque<>();

    public void add(long capturedAtMillis, MotionFeatures features) {
        entries.addLast(new Entry(capturedAtMillis, features));
        prune(capturedAtMillis);
    }

    public MotionFeatures latestCandidateOrNull(long nowMillis) {
        prune(nowMillis);
        var iterator = entries.descendingIterator();
        while (iterator.hasNext()) {
            MotionFeatures features = iterator.next().features;
            if (features.windowedPostureLikely()
                    || features.handheldViewingLikely()
                    || features.seatedPostureLikely()) {
                return features;
            }
        }
        return null;
    }

    private void prune(long nowMillis) {
        long oldest = nowMillis - RETENTION_MILLIS;
        while (!entries.isEmpty() && entries.peekFirst().capturedAtMillis < oldest) {
            entries.removeFirst();
        }
    }

    private static final class Entry {
        private final long capturedAtMillis;
        private final MotionFeatures features;

        private Entry(long capturedAtMillis, MotionFeatures features) {
            this.capturedAtMillis = capturedAtMillis;
            this.features = features;
        }
    }
}
