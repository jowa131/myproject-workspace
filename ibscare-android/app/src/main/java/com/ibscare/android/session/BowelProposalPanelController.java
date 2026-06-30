package com.ibscare.android.session;

import android.app.Activity;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.ibscare.android.R;
import com.ibscare.android.ui.ClinicalUi;
import com.ibscare.android.ui.TextSpec;

public final class BowelProposalPanelController {
    private final Activity activity;
    private final Runnable onConfirm;
    private final Runnable onSample;
    private TextView title;
    private TextView body;

    public BowelProposalPanelController(Activity activity, Runnable onConfirm, Runnable onSample) {
        this.activity = activity;
        this.onConfirm = onConfirm;
        this.onSample = onSample;
    }

    public View buildPanel() {
        LinearLayout panel = ClinicalUi.panel(activity, R.color.surface_elevated);
        title = text("배변 가능성 세션 확인 중", 18, R.color.text_primary, 1);
        body = text("가속도 센서의 정지 패턴을 보고 기록 제안 여부를 계산합니다.", 15, R.color.text_secondary, 0);
        Button confirmButton = ClinicalUi.primaryButton(activity, "배변 기록 확인하기");
        confirmButton.setOnClickListener(view -> onConfirm.run());
        Button sampleButton = ClinicalUi.primaryButton(activity, "테스트용 후보 점수 계산");
        sampleButton.setOnClickListener(view -> onSample.run());
        panel.addView(text("기록 놓침 방지", 12, R.color.accent_primary, 1));
        panel.addView(title);
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(body);
        ClinicalUi.gap(activity, panel, 12);
        panel.addView(confirmButton);
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(sampleButton);
        return panel;
    }

    public void setProposal(String titleText, String bodyText) {
        title.setText(titleText);
        body.setText(bodyText);
    }

    private TextView text(String value, int sizeSp, int colorRes, int style) {
        return ClinicalUi.text(activity, TextSpec.builder(value)
                .sizeSp(sizeSp)
                .colorRes(colorRes)
                .style(style)
                .build());
    }
}
