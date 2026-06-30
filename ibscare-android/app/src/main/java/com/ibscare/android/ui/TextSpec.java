package com.ibscare.android.ui;

public final class TextSpec {
    private final String value;
    private final int sizeSp;
    private final int colorRes;
    private final int style;

    private TextSpec(Builder builder) {
        value = builder.value;
        sizeSp = builder.sizeSp;
        colorRes = builder.colorRes;
        style = builder.style;
    }

    public static Builder builder(String value) {
        return new Builder(value);
    }

    String value() {
        return value;
    }

    int sizeSp() {
        return sizeSp;
    }

    int colorRes() {
        return colorRes;
    }

    int style() {
        return style;
    }

    public static final class Builder {
        private final String value;
        private int sizeSp = 15;
        private int colorRes = android.R.color.black;
        private int style;

        private Builder(String value) {
            this.value = value;
        }

        public Builder sizeSp(int value) {
            sizeSp = value;
            return this;
        }

        public Builder colorRes(int value) {
            colorRes = value;
            return this;
        }

        public Builder style(int value) {
            style = value;
            return this;
        }

        public TextSpec build() {
            return new TextSpec(this);
        }
    }
}
