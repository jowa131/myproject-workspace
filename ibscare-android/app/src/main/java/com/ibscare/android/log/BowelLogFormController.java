package com.ibscare.android.log;

import android.app.Activity;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.Spinner;
import android.widget.TextView;

import com.ibscare.android.R;
import com.ibscare.android.data.BowelLogEntry;
import com.ibscare.android.data.BowelLogRepository;
import com.ibscare.android.ui.ClinicalUi;
import com.ibscare.android.ui.TextSpec;
import com.ibscare.android.ui.UiCopy;

import java.util.function.Supplier;

public final class BowelLogFormController {
    private final Activity activity;
    private final BowelLogRepository repository;
    private final Supplier<String> todayProvider;
    private final Runnable onSaved;
    private EditText timeInput;
    private Spinner bristolInput;
    private CheckBox completeInput;
    private CheckBox urgencyInput;
    private CheckBox bloodInput;
    private TextView savedSummary;

    public BowelLogFormController(
            Activity activity,
            BowelLogRepository repository,
            Supplier<String> todayProvider,
            Runnable onSaved) {
        this.activity = activity;
        this.repository = repository;
        this.todayProvider = todayProvider;
        this.onSaved = onSaved;
    }

    public View buildPanel() {
        LinearLayout panel = ClinicalUi.panel(activity, R.color.surface_secondary);
        panel.addView(text("오늘의 배변", 22, R.color.text_primary, 1));
        timeInput = new EditText(activity);
        timeInput.setHint("오전 08:00");
        bristolInput = new Spinner(activity);
        bristolInput.setAdapter(new ArrayAdapter<>(
                activity,
                android.R.layout.simple_spinner_dropdown_item,
                UiCopy.BRISTOL_LABELS));
        bristolInput.setSelection(3);
        completeInput = checkbox("완전 자발 배변");
        urgencyInput = checkbox("배변 급박감");
        bloodInput = checkbox("혈변 또는 검은 변");
        Button saveButton = ClinicalUi.primaryButton(activity, "기록 저장");
        saveButton.setOnClickListener(view -> saveEntry());
        savedSummary = text("", 14, R.color.text_secondary, 0);
        addLabeled(panel, "시간", timeInput);
        addLabeled(panel, "변 모양 (Bristol 유형)", bristolInput);
        panel.addView(completeInput);
        panel.addView(urgencyInput);
        panel.addView(bloodInput);
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(saveButton);
        ClinicalUi.gap(activity, panel, 8);
        panel.addView(savedSummary);
        return panel;
    }

    public void prefillSuggestedTime(String suggestedTime) {
        timeInput.setText(suggestedTime);
        timeInput.requestFocus();
    }

    public void updateSavedSummary() {
        savedSummary.setText(repository.lastSummary(todayProvider.get()));
    }

    private void saveEntry() {
        repository.save(BowelLogEntry.builder(todayProvider.get())
                .time(timeInput.getText().toString())
                .bristolType(bristolInput.getSelectedItem().toString())
                .completeSpontaneous(completeInput.isChecked())
                .urgency(urgencyInput.isChecked())
                .bloodOrBlackStool(bloodInput.isChecked())
                .build());
        savedSummary.setText("저장 완료 · " + repository.lastSummary(todayProvider.get()));
        onSaved.run();
    }

    private CheckBox checkbox(String label) {
        CheckBox checkBox = new CheckBox(activity);
        checkBox.setText(label);
        return checkBox;
    }

    private void addLabeled(LinearLayout panel, String label, View input) {
        ClinicalUi.gap(activity, panel, 12);
        panel.addView(text(label, 14, R.color.text_secondary, 1));
        panel.addView(input);
    }

    private TextView text(String value, int sizeSp, int colorRes, int style) {
        return ClinicalUi.text(activity, TextSpec.builder(value)
                .sizeSp(sizeSp)
                .colorRes(colorRes)
                .style(style)
                .build());
    }
}
