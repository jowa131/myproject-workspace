package com.ibscare.android.session;

public final class CandidateMovementGateCliTest {
    private CandidateMovementGateCliTest() {
    }

    public static void run() {
        excludesCandidateWithMovingGpsSpeed();
        excludesCandidateWithLargeLocationDelta();
        keepsCandidateWhenLocationIsStationary();
    }

    private static void excludesCandidateWithMovingGpsSpeed() {
        LocationMovementSnapshot latest = LocationMovementSnapshot.builder(37.5665d, 126.9780d)
                .accuracyMeters(15.0f)
                .speedMetersPerSecond(1.4f)
                .capturedAtMillis(1_000L)
                .build();

        assertTrue(CandidateMovementGate.isMoving(null, latest), "moving GPS speed should exclude");
    }

    private static void excludesCandidateWithLargeLocationDelta() {
        LocationMovementSnapshot previous = LocationMovementSnapshot.builder(37.5665d, 126.9780d)
                .accuracyMeters(20.0f)
                .capturedAtMillis(1_000L)
                .build();
        LocationMovementSnapshot latest = LocationMovementSnapshot.builder(37.5680d, 126.9820d)
                .accuracyMeters(20.0f)
                .capturedAtMillis(61_000L)
                .build();

        assertTrue(CandidateMovementGate.isMoving(previous, latest), "large location delta should exclude");
    }

    private static void keepsCandidateWhenLocationIsStationary() {
        LocationMovementSnapshot previous = LocationMovementSnapshot.builder(37.5665d, 126.9780d)
                .accuracyMeters(20.0f)
                .capturedAtMillis(1_000L)
                .build();
        LocationMovementSnapshot latest = LocationMovementSnapshot.builder(37.56653d, 126.97803d)
                .accuracyMeters(20.0f)
                .capturedAtMillis(61_000L)
                .build();

        assertFalse(CandidateMovementGate.isMoving(previous, latest), "stationary location should remain eligible");
    }

    private static void assertTrue(boolean actual, String label) {
        if (!actual) {
            throw new AssertionError(label);
        }
    }

    private static void assertFalse(boolean actual, String label) {
        if (actual) {
            throw new AssertionError(label);
        }
    }
}
