package com.ibscare.android.ui;

public final class UiCopy {
    public static final String SAFETY_NOTICE = "의료 판단이 아닌 기록 보조입니다";
    public static final String VERSION_LABEL_PREFIX = "버전 ";
    public static final String PROPOSAL_DISCLAIMER = "자동 저장이 아니며 사용자가 직접 확인해야 합니다.";
    public static final String SESSION_ALERT_TITLE = "배변 기록을 확인할까요?";
    public static final String SESSION_ALERT_BODY = "배변 가능성이 높은 세션으로 보입니다. 지금 기록을 남길지 확인해 주세요.";
    public static final String SESSION_ALERT_NOTIFICATION = "기록 후보가 감지되었습니다.";
    public static final String SESSION_ALERT_CONFIRM = "기록 확인하기";
    public static final String SESSION_ALERT_RECORD_ACTION = "기록하러 가기";
    public static final String SESSION_ALERT_FALSE_POSITIVE = "똥싸는 중이 아님";
    public static final String FALSE_POSITIVE_RECORDED_TITLE = "똥싸는 중이 아님으로 기록됨";
    public static final String FALSE_POSITIVE_RECORDED_BODY =
            "이 패턴은 배변 중이 아닌 상황으로 저장했습니다. 다음 감지부터 비슷한 자세와 정지 패턴은 제안을 줄입니다.";
    public static final String SESSION_ALERT_CHANNEL = "배변 기록 제안";
    public static final String SESSION_ALERT_CHANNEL_DESCRIPTION = "배변 가능성이 높은 세션에서 기록 확인을 제안합니다.";
    public static final String MONITORING_CHANNEL = "백그라운드 배변 감지";
    public static final String MONITORING_CHANNEL_DESCRIPTION = "앱을 닫아도 배변 기록 후보를 감지합니다.";
    public static final String MONITORING_TITLE = "배변 기록 후보 감지 중";
    public static final String MONITORING_BODY = "앱을 닫아도 휴대폰 정지 패턴을 확인합니다.";
    public static final String MONITORING_STOP = "감지 중지";
    public static final String LOCATION_PERMISSION_REASON = "배변 후보가 잡힌 순간에만 이동 중인지 짧게 확인합니다.";
    public static final String MONITORING_IMPACT_MEMO = "평소에는 가속도 센서만 사용하고, 후보가 잡힌 순간에만 위치로 이동 중인지 짧게 확인합니다. 서버 전송 데이터는 0MB입니다. 배터리는 기기별 차이가 크며, 사용하지 않을 때는 알림에서 감지를 중지해 주세요.";
    public static final String SAFETY_MEMO = "이 앱은 배변을 확정하지 않고 가능성이 높은 세션만 제안합니다. 혈변, 검은 변, 의도치 않은 체중 감소, 야간 증상은 별도로 의료진 상담을 고려해 주세요.";
    public static final String UPDATE_PANEL_TITLE = "폰 테스트 업데이트";
    public static final String UPDATE_PANEL_BODY = "전달받은 APK 파일을 선택하면 Android 설치 확인 화면으로 이동합니다. 자동 설치는 하지 않습니다.";
    public static final String UPDATE_PICK_BUTTON = "APK 파일 선택";
    public static final String UPDATE_IDLE_STATUS = "선택된 APK가 없습니다.";
    public static final String UPDATE_INSTALL_PERMISSION_TITLE = "설치 권한 필요";
    public static final String UPDATE_INSTALL_PERMISSION_BODY = "IBS 관리 기록에서 APK 설치를 요청할 수 있도록 Android 설정에서 허용해 주세요.";
    public static final String[] BRISTOL_LABELS = {
            "1형 - 딱딱한 알갱이 변",
            "2형 - 울퉁불퉁한 소시지 모양",
            "3형 - 표면에 금이 간 소시지 모양",
            "4형 - 매끈하고 부드러운 바나나 모양",
            "5형 - 경계가 뚜렷한 부드러운 덩어리",
            "6형 - 흐물흐물하고 죽 같은 변",
            "7형 - 물처럼 묽은 변"
    };

    private UiCopy() {
    }
}
