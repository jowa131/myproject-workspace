package com.ibscare.android.data;

public final class BowelLogEntry {
    private final String date;
    private final String time;
    private final String bristolType;
    private final boolean completeSpontaneous;
    private final boolean urgency;
    private final boolean bloodOrBlackStool;

    private BowelLogEntry(Builder builder) {
        date = builder.date;
        time = builder.time;
        bristolType = builder.bristolType;
        completeSpontaneous = builder.completeSpontaneous;
        urgency = builder.urgency;
        bloodOrBlackStool = builder.bloodOrBlackStool;
    }

    public static Builder builder(String date) {
        return new Builder(date);
    }

    public String date() {
        return date;
    }

    public String time() {
        return time;
    }

    public String bristolType() {
        return bristolType;
    }

    public boolean completeSpontaneous() {
        return completeSpontaneous;
    }

    public boolean urgency() {
        return urgency;
    }

    public boolean bloodOrBlackStool() {
        return bloodOrBlackStool;
    }

    public static final class Builder {
        private final String date;
        private String time = "";
        private String bristolType = "";
        private boolean completeSpontaneous;
        private boolean urgency;
        private boolean bloodOrBlackStool;

        private Builder(String date) {
            this.date = date;
        }

        public Builder time(String value) {
            time = value;
            return this;
        }

        public Builder bristolType(String value) {
            bristolType = value;
            return this;
        }

        public Builder completeSpontaneous(boolean value) {
            completeSpontaneous = value;
            return this;
        }

        public Builder urgency(boolean value) {
            urgency = value;
            return this;
        }

        public Builder bloodOrBlackStool(boolean value) {
            bloodOrBlackStool = value;
            return this;
        }

        public BowelLogEntry build() {
            return new BowelLogEntry(this);
        }
    }
}
