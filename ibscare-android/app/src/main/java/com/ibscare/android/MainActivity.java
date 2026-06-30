package com.ibscare.android;

import android.app.Activity;
import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.app.NotificationManager;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.location.LocationManager;
import android.os.Bundle;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;

import com.ibscare.android.alert.LikelySessionAlerter;
import com.ibscare.android.data.BowelLogRepository;
import com.ibscare.android.data.PersonalPatternStore;
import com.ibscare.android.data.PendingBowelSession;
import com.ibscare.android.data.PendingBowelSessionStore;
import com.ibscare.android.log.BowelLogFormController;
import com.ibscare.android.service.BackgroundBowelDetectionService;
import com.ibscare.android.session.BowelProposalPanelController;
import com.ibscare.android.session.BowelSessionLikelihoodResult;
import com.ibscare.android.session.BowelSessionScorer;
import com.ibscare.android.session.ForegroundMovementVerifier;
import com.ibscare.android.session.MotionFeatures;
import com.ibscare.android.session.PromptCooldownGate;
import com.ibscare.android.ui.BowelProposalActionResult;
import com.ibscare.android.ui.ClinicalUi;
import com.ibscare.android.ui.MainStaticPanels;
import com.ibscare.android.ui.UiCopy;
import com.ibscare.android.update.LocalApkUpdateController;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public final class MainActivity extends Activity implements SensorEventListener {
    public static final String ACTION_OPEN_PENDING_SESSION =
            "com.ibscare.android.action.OPEN_PENDING_BOWEL_SESSION";
    public static final String ACTION_RECORD_PENDING_SESSION =
            "com.ibscare.android.action.RECORD_PENDING_BOWEL_SESSION";
    public static final String ACTION_FALSE_POSITIVE_PENDING_SESSION =
            "com.ibscare.android.action.FALSE_POSITIVE_PENDING_BOWEL_SESSION";
    private static final int LOCATION_PERMISSION_REQUEST_CODE = 2002;
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd", Locale.KOREA);
    private LikelySessionAlerter likelySessionAlerter;
    private BowelLogRepository repository;
    private DeviceFeatureCoordinator featureCoordinator;
    private PendingBowelSessionStore pendingStore;
    private SensorManager sensorManager;
    private Sensor accelerometer;
    private Sensor gravitySensor;
    private BowelSessionLikelihoodResult currentLikelihood;
    private MotionFeatures currentFeatures;
    private BowelProposalPanelController proposalPanelController;
    private BowelLogFormController logFormController;
    private LocalApkUpdateController updateController;
    private ForegroundMovementVerifier movementVerifier;
    private final PromptCooldownGate promptCooldownGate = new PromptCooldownGate();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        repository = new BowelLogRepository(this);
        featureCoordinator = new DeviceFeatureCoordinator(new PersonalPatternStore(this));
        pendingStore = new PendingBowelSessionStore(this);
        likelySessionAlerter = new LikelySessionAlerter(this);
        sensorManager = (SensorManager) getSystemService(SENSOR_SERVICE);
        accelerometer = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_ACCELEROMETER);
        gravitySensor = sensorManager == null ? null : sensorManager.getDefaultSensor(Sensor.TYPE_GRAVITY);
        LocationManager locationManager = (LocationManager) getSystemService(LOCATION_SERVICE);
        proposalPanelController = new BowelProposalPanelController(this, this::confirmProposal, this::sampleLikelySession);
        logFormController = new BowelLogFormController(
                this,
                repository,
                this::today,
                this::learnFromManualRecordThenRecalculate);
        updateController = new LocalApkUpdateController(this);
        movementVerifier = new ForegroundMovementVerifier(this, locationManager);
        setContentView(buildContent());
        likelySessionAlerter.prepare();
        requestLocationPermissionIfNeeded();
        startBackgroundDetection();
        updateLikelihood(featureCoordinator.idleFeatures(), "감지 대기 중", false);
        logFormController.updateSavedSummary();
        updateController.handleIncomingIntent(getIntent());
        handleInitialNotificationAction(getIntent());
    }

    @Override
    protected void onResume() {
        super.onResume();
        pendingStore.setActivityVisible(true);
        applyPendingSessionIfAny();
        if (sensorManager != null && accelerometer != null) {
            sensorManager.registerListener(this, accelerometer, SensorManager.SENSOR_DELAY_NORMAL);
        }
        if (sensorManager != null && gravitySensor != null) {
            sensorManager.registerListener(this, gravitySensor, SensorManager.SENSOR_DELAY_NORMAL);
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        updateController.handleIncomingIntent(intent);
        handleNotificationAction(intent);
    }

    @Override
    protected void onPause() {
        pendingStore.setActivityVisible(false);
        if (sensorManager != null) {
            sensorManager.unregisterListener(this);
        }
        super.onPause();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == LOCATION_PERMISSION_REQUEST_CODE && hasLocationPermission()) {
            startBackgroundDetection();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (updateController.onActivityResult(requestCode, resultCode, data)) {
            return;
        }
    }

    @Override
    public void onSensorChanged(SensorEvent event) {
        MotionFeatures features = sensorFeatures(event);
        if (features == null) {
            return;
        }
        if (BowelSessionScorer.hasCandidateEvidence(features)) {
            updateLikelihood(features, "실시간 기기 센서", true);
        }
    }

    @Override
    public void onAccuracyChanged(Sensor sensor, int accuracy) {
    }

    private View buildContent() {
        ScrollView scrollView = new ScrollView(this);
        scrollView.setFillViewport(true);
        scrollView.setFitsSystemWindows(true);
        scrollView.setBackgroundColor(getColor(R.color.surface_primary));
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(ClinicalUi.dp(this, 20), ClinicalUi.dp(this, 20),
                ClinicalUi.dp(this, 20), ClinicalUi.dp(this, 28));
        scrollView.addView(root);

        MainStaticPanels staticPanels = new MainStaticPanels(this);
        staticPanels.addHeader(root, appVersionLabel());
        root.addView(proposalPanelController.buildPanel());
        root.addView(logFormController.buildPanel());
        root.addView(updateController.buildPanel());
        root.addView(staticPanels.buildSafetyPanel());
        return scrollView;
    }

    private String appVersionLabel() {
        return BuildConfig.VERSION_NAME + " (" + BuildConfig.VERSION_CODE + ")";
    }

    private void updateLikelihood(MotionFeatures features, String sourceLabel, boolean eligibleForLearning) {
        MotionFeatures personalized = featureCoordinator.personalize(features, eligibleForLearning);
        currentFeatures = personalized;
        currentLikelihood = BowelSessionScorer.evaluate(personalized);
        proposalPanelController.setProposal(
                sourceLabel + " · 가능성 " + currentLikelihood.score0To100() + "점",
                currentLikelihood.summary() + "\n" + UiCopy.PROPOSAL_DISCLAIMER);
        alertForLikelySession();
    }

    private void sampleLikelySession() {
        updateLikelihood(
                featureCoordinator.sampleForReview(System.currentTimeMillis()),
                "테스트용 후보 점수",
                false);
    }

    private void confirmProposal() {
        BowelProposalActionResult action = BowelProposalActionResult.from(currentLikelihood);
        if (action.shouldPrefill()) {
            logFormController.prefillSuggestedTime(action.suggestedTime());
        }
        proposalPanelController.setProposal(action.title(), action.body() + "\n" + UiCopy.PROPOSAL_DISCLAIMER);
    }

    private void learnFromManualRecordThenRecalculate() {
        featureCoordinator.learnFromRecentCandidate(System.currentTimeMillis());
        updateLikelihood(featureCoordinator.sampleForReview(System.currentTimeMillis()), "저장 후 재계산", false);
    }

    private void alertForLikelySession() {
        if (currentLikelihood == null || !currentLikelihood.shouldPrompt()) {
            return;
        }
        if (!promptCooldownGate.canPrompt(System.currentTimeMillis())) {
            return;
        }
        verifyMovementThenAlert();
    }

    private void verifyMovementThenAlert() {
        movementVerifier.verify(this::showLikelySessionAlert, this::showMovingExclusion);
    }

    private void showLikelySessionAlert() {
        promptCooldownGate.markPromptShown(System.currentTimeMillis());
        likelySessionAlerter.show(
                currentLikelihood,
                this::confirmProposal,
                this::recordFalsePositiveFromAlert);
    }

    private void recordFalsePositiveFromAlert() {
        if (currentFeatures == null) {
            return;
        }
        featureCoordinator.learnFalsePositive(currentFeatures);
        MotionFeatures corrected = featureCoordinator.personalize(currentFeatures, false);
        currentFeatures = corrected;
        currentLikelihood = BowelSessionScorer.evaluate(corrected);
        proposalPanelController.setProposal(
                UiCopy.FALSE_POSITIVE_RECORDED_TITLE + " · 가능성 "
                        + currentLikelihood.score0To100() + "점",
                UiCopy.FALSE_POSITIVE_RECORDED_BODY + "\n" + UiCopy.PROPOSAL_DISCLAIMER);
    }

    private void handleInitialNotificationAction(Intent intent) {
        if (intent == null || !ACTION_FALSE_POSITIVE_PENDING_SESSION.equals(intent.getAction())) {
            return;
        }
        handleNotificationAction(intent);
    }

    private void handleNotificationAction(Intent intent) {
        if (intent == null) {
            return;
        }
        String action = intent.getAction();
        if (ACTION_FALSE_POSITIVE_PENDING_SESSION.equals(action)) {
            dismissLikelySessionNotification();
            recordFalsePositiveFromNotification();
            intent.setAction(null);
            return;
        }
        if (ACTION_RECORD_PENDING_SESSION.equals(action) || ACTION_OPEN_PENDING_SESSION.equals(action)) {
            dismissLikelySessionNotification();
            applyPendingSessionIfAny();
            intent.setAction(null);
        }
    }

    private void recordFalsePositiveFromNotification() {
        PendingBowelSession pendingSession = pendingStore.load(today());
        if (pendingSession != null && pendingSession.features().isPresent()) {
            currentFeatures = pendingSession.features().get();
            recordFalsePositiveFromAlert();
            pendingStore.clear();
            return;
        }
        if (currentLikelihood != null && currentLikelihood.shouldPrompt()) {
            recordFalsePositiveFromAlert();
        }
    }

    private void dismissLikelySessionNotification() {
        NotificationManager manager = getSystemService(NotificationManager.class);
        if (manager != null) {
            manager.cancel(com.ibscare.android.alert.LikelySessionNotifier.LIKELY_NOTIFICATION_ID);
        }
    }

    private void showMovingExclusion() {
        proposalPanelController.setProposal(
                "이동 중 제외 · 가능성 0점",
                "GPS 이동 중으로 보여 배변 후보에서 제외했습니다.\n" + UiCopy.PROPOSAL_DISCLAIMER);
    }

    private void applyPendingSessionIfAny() {
        PendingBowelSession pendingSession = pendingStore.load(today());
        if (pendingSession == null) {
            return;
        }
        movementVerifier.verify(
                () -> showPendingSession(pendingSession),
                this::showPendingMovementExclusion);
    }

    private void showPendingSession(PendingBowelSession pendingSession) {
        logFormController.prefillSuggestedTime(pendingSession.suggestedTime());
        pendingSession.features().ifPresent(featureCoordinator::rememberPending);
        proposalPanelController.setProposal(
                "백그라운드 감지 · 가능성 " + pendingSession.score0To100() + "점",
                pendingSession.summary() + "\n" + UiCopy.PROPOSAL_DISCLAIMER);
        pendingStore.clear();
    }

    private void showPendingMovementExclusion() {
        proposalPanelController.setProposal(
                "백그라운드 후보 이동 중 제외 · 가능성 0점",
                "앱을 다시 열었을 때 이동 중으로 보여 배변 후보에서 제외했습니다.\n" + UiCopy.PROPOSAL_DISCLAIMER);
        pendingStore.clear();
    }

    private MotionFeatures sensorFeatures(SensorEvent event) {
        return featureCoordinator.sensorFeatures(event, true);
    }

    private void startBackgroundDetection() {
        Intent intent = new Intent(this, BackgroundBowelDetectionService.class).setAction(BackgroundBowelDetectionService.ACTION_START);
        startForegroundService(intent);
    }

    private void requestLocationPermissionIfNeeded() {
        if (hasLocationPermission()) {
            return;
        }
        requestPermissions(new String[] {Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION},
                LOCATION_PERMISSION_REQUEST_CODE);
    }

    private boolean hasLocationPermission() {
        return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                || checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)
                == PackageManager.PERMISSION_GRANTED;
    }

    private String today() {
        return dateFormat.format(new Date());
    }
}
