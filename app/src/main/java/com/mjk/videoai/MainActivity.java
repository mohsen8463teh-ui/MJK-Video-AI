package com.mjk.videoai;

import android.app.Activity;
import android.app.AlertDialog;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public class MainActivity extends Activity {

    private static final String BACKEND_URL = "http://127.0.0.1:5000/v1/llm/director-generate";

    private final int BG = Color.rgb(10, 12, 18);
    private final int CARD = Color.rgb(22, 25, 34);
    private final int OPTION = Color.rgb(29, 33, 44);
    private final int TEXT = Color.WHITE;
    private final int MUTED = Color.rgb(165, 171, 185);
    private final int ACCENT = Color.rgb(118, 86, 255);
    private final int SELECTED = Color.rgb(74, 52, 170);

    private String selectedOutputType = "youtube";
    private String selectedStyle = "cinematic";
    private int selectedDurationSeconds = 60;
    private String selectedLanguage = "فارسی";
    private String selectedAspectRatio = "9:16";

    private int dp(float v) {
        return (int)(v * getResources().getDisplayMetrics().density + 0.5f);
    }

    private GradientDrawable rounded(int color, float radius) {
        GradientDrawable g = new GradientDrawable();
        g.setColor(color);
        g.setCornerRadius(dp(radius));
        return g;
    }

    private TextView text(String value, float size, int color, boolean bold) {
        TextView v = new TextView(this);
        v.setText(value);
        v.setTextSize(size);
        v.setTextColor(color);
        v.setTypeface(Typeface.DEFAULT, bold ? Typeface.BOLD : Typeface.NORMAL);
        v.setGravity(Gravity.CENTER_VERTICAL);
        v.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);
        return v;
    }

    private LinearLayout card() {
        LinearLayout v = new LinearLayout(this);
        v.setOrientation(LinearLayout.VERTICAL);
        v.setPadding(dp(18), dp(18), dp(18), dp(18));
        v.setBackground(rounded(CARD, 18));
        return v;
    }

    private LinearLayout.LayoutParams margin(int top) {
        LinearLayout.LayoutParams p =
                new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, dp(top), 0, 0);
        return p;
    }

    private TextView option(String label) {
        TextView v = text(label, 14, TEXT, false);
        v.setGravity(Gravity.CENTER);
        v.setPadding(dp(8), dp(10), dp(8), dp(10));
        v.setBackground(rounded(OPTION, 14));
        return v;
    }

    private void choose(TextView selected, LinearLayout row) {
        for (int i = 0; i < row.getChildCount(); i++) {
            View v = row.getChildAt(i);
            if (v instanceof TextView) {
                v.setBackground(rounded(OPTION, 14));
                ((TextView)v).setTextColor(TEXT);
            }
        }

        selected.setBackground(rounded(SELECTED, 14));
        selected.setTextColor(Color.WHITE);
    }

    private LinearLayout options(String[] values, int selectedIndex) {
        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);
        row.setGravity(Gravity.CENTER);

        for (int i = 0; i < values.length; i++) {
            TextView v = option(values[i]);

            LinearLayout.LayoutParams p =
                    new LinearLayout.LayoutParams(0, dp(48), 1f);

            if (i > 0) {
                p.setMargins(dp(6), 0, 0, 0);
            }

            row.addView(v, p);

            final TextView selected = v;
            v.setOnClickListener(view -> choose(selected, row));

            if (i == selectedIndex) {
                choose(v, row);
            }
        }

        return row;
    }

    private void appendResult(StringBuilder display, String title, String value) {
        if (value != null && !value.trim().isEmpty()) {
            display.append(title)
                    .append(":\n")
                    .append(value)
                    .append("\n\n");
        }
    }

    private void requestDirector(String userPrompt) {
        new Thread(() -> {
            HttpURLConnection connection = null;
            try {
                URL url = new URL(BACKEND_URL);
                connection = (HttpURLConnection) url.openConnection();
                connection.setRequestMethod("POST");
                connection.setConnectTimeout(10000);
                connection.setReadTimeout(120000);
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
                connection.setRequestProperty("Accept", "application/json");

                JSONObject body = new JSONObject();
                body.put("prompt", userPrompt);
                body.put("duration_seconds", selectedDurationSeconds);
                body.put("style", selectedStyle);
                body.put("language", selectedLanguage);
                body.put("aspect_ratio", selectedAspectRatio);
                body.put("output_type", selectedOutputType);

                OutputStream os = connection.getOutputStream();
                os.write(body.toString().getBytes("UTF-8"));
                os.flush();
                os.close();

                int statusCode = connection.getResponseCode();
                InputStream stream = (statusCode >= 200 && statusCode < 300)
                        ? connection.getInputStream() : connection.getErrorStream();

                BufferedReader reader = new BufferedReader(new InputStreamReader(stream, "UTF-8"));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) response.append(line);
                reader.close();

                final String result = response.toString();
                final int finalStatus = statusCode;

                runOnUiThread(() -> {
                    if (finalStatus >= 200 && finalStatus < 300) {
                        try {
                            JSONObject json = new JSONObject(result);
                            JSONObject plan = json.optJSONObject("plan");

                            StringBuilder display = new StringBuilder();

                            if (plan != null) {
                                appendResult(display, "ایده", plan.optString("concept", ""));
                                appendResult(display, "Hook", plan.optString("hook", ""));
                                appendResult(display, "مخاطب", plan.optString("audience", ""));
                                appendResult(display, "سناریو", plan.optString("story", ""));
                                appendResult(display, "CTA", plan.optString("cta", ""));

                                if (plan.has("characters")) {
                                    appendResult(display, "شخصیت‌ها",
                                            plan.optJSONArray("characters") != null
                                                    ? plan.optJSONArray("characters").toString()
                                                    : plan.optString("characters", ""));
                                }

                                if (plan.has("locations")) {
                                    appendResult(display, "لوکیشن‌ها",
                                            plan.optJSONArray("locations") != null
                                                    ? plan.optJSONArray("locations").toString()
                                                    : plan.optString("locations", ""));
                                }

                                if (plan.has("scenes")) {
                                    appendResult(display, "صحنه‌ها",
                                            plan.optJSONArray("scenes") != null
                                                    ? plan.optJSONArray("scenes").toString(2)
                                                    : plan.optString("scenes", ""));
                                }

                                appendResult(display, "گویندگی", plan.optString("voiceover", ""));
                                appendResult(display, "موسیقی", plan.optString("music", ""));
                                appendResult(display, "افکت‌های صوتی", plan.optString("sound_effects", ""));
                                appendResult(display, "کپشن", plan.optString("captions", ""));
                            }

                            if (display.length() == 0) {
                                display.append("پاسخ خام AI:\n\n").append(result);
                            }

                            TextView resultView = new TextView(this);
                            resultView.setText(display.toString());
                            resultView.setTextColor(Color.BLACK);
                            resultView.setTextSize(16);
                            resultView.setPadding(dp(20), dp(16), dp(20), dp(16));
                            resultView.setTextIsSelectable(true);
                            resultView.setGravity(Gravity.RIGHT | Gravity.TOP);
                            resultView.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);

                            ScrollView resultScroll = new ScrollView(this);
                            resultScroll.setFillViewport(true);
                            resultScroll.addView(resultView);

                            new AlertDialog.Builder(this)
                                    .setTitle("AI Director")
                                    .setView(resultScroll)
                                    .setPositiveButton("باشه", null)
                                    .show();

                        } catch (Exception e) {
                            new AlertDialog.Builder(this)
                                    .setTitle("AI Director")
                                    .setMessage(result)
                                    .setPositiveButton("باشه", null)
                                    .show();
                        }
                    } else {
                        new AlertDialog.Builder(this)
                                .setTitle("خطا")
                                .setMessage("Backend پاسخ موفق نداد.\n\nHTTP " + finalStatus + "\n\n" + result)
                                .setPositiveButton("باشه", null)
                                .show();
                    }
                });
            } catch (Exception e) {
                final String error = e.getClass().getSimpleName() + ": " + String.valueOf(e.getMessage());
                runOnUiThread(() -> new AlertDialog.Builder(this)
                        .setTitle("خطای اتصال")
                        .setMessage("اتصال به AI Director برقرار نشد.\n\n" + error)
                        .setPositiveButton("باشه", null)
                        .show());
            } finally {
                if (connection != null) connection.disconnect();
            }
        }).start();
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        getWindow().setStatusBarColor(Color.rgb(7, 8, 12));
        getWindow().setNavigationBarColor(Color.rgb(7, 8, 12));

        ScrollView scroll = new ScrollView(this);
        scroll.setBackgroundColor(BG);

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setPadding(dp(16), dp(18), dp(16), dp(28));
        root.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);

        scroll.addView(root);

        TextView brand = text("MJK", 30, TEXT, true);
        root.addView(brand);

        TextView title = text("ساخت ویدیو با هوش مصنوعی", 23, TEXT, true);
        title.setPadding(0, dp(5), 0, dp(4));
        root.addView(title);

        TextView subtitle = text(
                "ایده‌ات را بنویس؛ MJK آن را به یک پروژه ویدیویی تبدیل می‌کند.",
                14, MUTED, false);
        root.addView(subtitle);

        LinearLayout promptCard = card();
        promptCard.addView(
                text("ایده یا پرامپت", 17, TEXT, true));

        EditText prompt = new EditText(this);
        prompt.setHint(
                "مثلاً: یک تبلیغ سینمایی برای فروشگاه من با شروع هیجان‌انگیز...");
        prompt.setHintTextColor(Color.rgb(125, 130, 145));
        prompt.setTextColor(TEXT);
        prompt.setTextSize(15);
        prompt.setGravity(Gravity.TOP | Gravity.RIGHT);
        prompt.setPadding(dp(14), dp(14), dp(14), dp(14));
        prompt.setMinLines(5);
        prompt.setBackground(rounded(OPTION, 14));
        prompt.setLayoutDirection(View.LAYOUT_DIRECTION_RTL);

        promptCard.addView(
                prompt,
                new LinearLayout.LayoutParams(-1, dp(140)));

        root.addView(promptCard, margin(18));

        LinearLayout typeCard = card();
        typeCard.addView(text("نوع خروجی", 17, TEXT, true));
        typeCard.addView(
                options(
                        new String[]{"YouTube", "Shorts / Reels", "تبلیغ مغازه"},
                        0),
                margin(12));
        root.addView(typeCard, margin(12));

        LinearLayout styleCard = card();
        styleCard.addView(text("سبک ویدیو", 17, TEXT, true));
        styleCard.addView(
                options(
                        new String[]{"سینمایی", "واقع‌گرایانه", "انیمیشنی", "فانتزی"},
                        0),
                margin(12));
        root.addView(styleCard, margin(12));

        LinearLayout settings = card();
        settings.addView(text("تنظیمات سریع", 17, TEXT, true));

        TextView duration = text("مدت ویدیو", 14, MUTED, false);
        settings.addView(duration, margin(12));

        settings.addView(
                options(
                        new String[]{"30 ثانیه", "60 ثانیه", "چند دقیقه"},
                        1),
                margin(6));

        TextView language = text("زبان گوینده", 14, MUTED, false);
        settings.addView(language, margin(12));

        settings.addView(
                options(
                        new String[]{"فارسی", "English", "بدون گوینده"},
                        0),
                margin(6));

        root.addView(settings, margin(12));

        LinearLayout director = card();

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);

        TextView directorTitle =
                text("AI Director", 17, TEXT, true);

        header.addView(
                directorTitle,
                new LinearLayout.LayoutParams(0, dp(35), 1f));

        TextView status = text("آماده", 13,
                Color.rgb(110, 220, 150), true);
        status.setGravity(Gravity.CENTER);
        status.setBackground(
                rounded(Color.rgb(30, 68, 50), 12));

        header.addView(
                status,
                new LinearLayout.LayoutParams(dp(72), dp(32)));

        director.addView(header);

        TextView info = text(
                "AI Director ایده را به سناریو، Hook، Storyboard و صحنه‌های قابل تولید تبدیل می‌کند.",
                13, MUTED, false);

        director.addView(info, margin(8));

        root.addView(director, margin(12));

        Button create = new Button(this);
        create.setText("ساخت ویدیو با AI  ✦");
        create.setTextSize(17);
        create.setTextColor(Color.WHITE);
        create.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        create.setAllCaps(false);
        create.setBackground(rounded(ACCENT, 18));

        create.setOnClickListener(v -> {
            String userPrompt = prompt.getText().toString().trim();

            if (userPrompt.isEmpty()) {
                Toast.makeText(this, "لطفاً ابتدا توضیح ویدیو را وارد کنید.", Toast.LENGTH_SHORT).show();
                prompt.requestFocus();
                return;
            }

            Toast.makeText(this, "AI Director در حال تحلیل درخواست شماست...", Toast.LENGTH_SHORT).show();
            requestDirector(userPrompt);
        });

        root.addView(
                create,
                new LinearLayout.LayoutParams(-1, dp(58)) {{
                    setMargins(0, dp(16), 0, 0);
                }});

        TextView footer =
                text("MJK Video AI  •  نسخه اولیه",
                        12, Color.rgb(105, 110, 125), false);

        footer.setGravity(Gravity.CENTER);

        root.addView(footer, margin(14));

        setContentView(scroll);
    }
}
