package com.ibscare.android.ui;

import android.app.Activity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.ibscare.android.R;

public final class MainStaticPanels {
    private final Activity activity;

    public MainStaticPanels(Activity activity) {
        this.activity = activity;
    }

    public void addHeader(LinearLayout root, String versionLabel) {
        root.addView(text(UiCopy.SAFETY_NOTICE, 14, R.color.text_secondary, 0));
        root.addView(text("IBS 관리 기록", 28, R.color.text_primary, 1));
        root.addView(text(UiCopy.VERSION_LABEL_PREFIX + versionLabel, 14, R.color.accent_primary, 0));
        ClinicalUi.gap(activity, root, 16);
    }

    public View buildSafetyPanel() {
        LinearLayout panel = ClinicalUi.panel(activity, R.color.surface_secondary);
        panel.addView(text("안전 확인", 18, R.color.text_primary, 1));
        panel.addView(text(UiCopy.SAFETY_MEMO, 15, R.color.text_secondary, 0));
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(text(UiCopy.MONITORING_IMPACT_MEMO, 14, R.color.text_secondary, 0));
        return panel;
    }

    private TextView text(String value, int sizeSp, int colorRes, int style) {
        return ClinicalUi.text(activity, TextSpec.builder(value)
                .sizeSp(sizeSp)
                .colorRes(colorRes)
                .style(style)
                .build());
    }
}
