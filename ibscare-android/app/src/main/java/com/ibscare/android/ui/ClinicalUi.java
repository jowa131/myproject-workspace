package com.ibscare.android.ui;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.View;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import com.ibscare.android.R;

public final class ClinicalUi {
    private ClinicalUi() {
    }

    public static TextView text(Context context, TextSpec spec) {
        TextView view = new TextView(context);
        view.setText(spec.value());
        view.setTextSize(spec.sizeSp());
        view.setTextColor(context.getColor(spec.colorRes()));
        view.setTypeface(Typeface.DEFAULT, typefaceStyle(spec.style()));
        view.setLineSpacing(0.0f, 1.18f);
        return view;
    }

    public static LinearLayout panel(Context context, int backgroundColorRes) {
        LinearLayout layout = new LinearLayout(context);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setPadding(dp(context, 16), dp(context, 16), dp(context, 16), dp(context, 16));
        layout.setBackground(surface(context, backgroundColorRes));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT);
        params.setMargins(0, 0, 0, dp(context, 12));
        layout.setLayoutParams(params);
        return layout;
    }

    public static Button primaryButton(Context context, String label) {
        Button button = new Button(context);
        button.setText(label);
        button.setTextColor(context.getColor(android.R.color.white));
        button.setTextSize(15);
        button.setAllCaps(false);
        button.setBackground(surface(context, R.color.accent_primary));
        return button;
    }

    public static void gap(Context context, LinearLayout layout, int dp) {
        View view = new View(context);
        view.setLayoutParams(new LinearLayout.LayoutParams(1, dp(context, dp)));
        layout.addView(view);
    }

    public static int dp(Context context, int value) {
        return Math.round(value * context.getResources().getDisplayMetrics().density);
    }

    private static GradientDrawable surface(Context context, int colorRes) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(context.getColor(colorRes));
        drawable.setCornerRadius(dp(context, 8));
        drawable.setStroke(dp(context, 1), context.getColor(R.color.border_default));
        return drawable;
    }

    private static int typefaceStyle(int style) {
        switch (style) {
            case Typeface.BOLD:
                return Typeface.BOLD;
            case Typeface.ITALIC:
                return Typeface.ITALIC;
            case Typeface.BOLD_ITALIC:
                return Typeface.BOLD_ITALIC;
            default:
                return Typeface.NORMAL;
        }
    }
}
