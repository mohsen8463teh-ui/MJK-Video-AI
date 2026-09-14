package com.mjk.videoai;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ContentValues;
import android.content.Intent;
import android.net.Uri;
import android.os.Environment;
import android.provider.MediaStore;

import androidx.media3.common.MediaItem;
import androidx.media3.common.MimeTypes;
import androidx.media3.common.util.UnstableApi;
import androidx.media3.transformer.Composition;
import androidx.media3.transformer.EditedMediaItem;
import androidx.media3.transformer.EditedMediaItemSequence;
import androidx.media3.transformer.ExportException;
import androidx.media3.transformer.ExportResult;
import androidx.media3.transformer.Transformer;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.BufferedReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@UnstableApi
public final class VideoGenerator {
    private static final String API = "https://mjk-video-ai-proxy.vercel.app";
    private static final int POLL_MS = 5000;
    private final Activity activity;
    private final ExecutorService io = Executors.newFixedThreadPool(8);

    private VideoGenerator(Activity activity) { this.activity = activity; }

    public static void start(Activity activity, String prompt, int durationSeconds, String aspectRatio) {
        new VideoGenerator(activity).submit(prompt, durationSeconds, aspectRatio);
    }

    private void status(String s) {
        activity.runOnUiThread(() -> {
            android.widget.Toast.makeText(activity, s, android.widget.Toast.LENGTH_SHORT).show();
        });
    }

    private JSONObject post(String url, JSONObject body) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
        try {
            c.setRequestMethod("POST");
            c.setConnectTimeout(15000);
            c.setReadTimeout(30000);
            c.setDoOutput(true);
            c.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            c.getOutputStream().write(body.toString().getBytes("UTF-8"));
            int code = c.getResponseCode();
            InputStream in = code >= 200 && code < 300 ? c.getInputStream() : c.getErrorStream();
            StringBuilder sb = new StringBuilder();
            if (in != null) {
                BufferedReader r = new BufferedReader(new InputStreamReader(in, "UTF-8"));
                String line; while ((line = r.readLine()) != null) sb.append(line);
                r.close();
            }
            JSONObject out = sb.length() == 0 ? new JSONObject() : new JSONObject(sb.toString());
            if (code < 200 || code >= 300)
                throw new Exception("HTTP " + code + "\n" + out.optString("message", out.toString()));
            return out;
        } finally { c.disconnect(); }
    }

    private void submit(String prompt, int duration, String aspect) {
        io.execute(() -> {
            try {
                status("در حال ثبت صحنه‌های AI...");
                JSONObject b = new JSONObject();
                b.put("prompt", prompt);
                b.put("duration_seconds", Math.min(240, Math.max(5, duration)));
                b.put("aspect_ratio", aspect);
                b.put("resolution", "480p");
                JSONObject r = post(API + "/v1/video/generate", b);
                JSONArray jobs = r.getJSONArray("jobs");
                status("تعداد صحنه‌ها: " + jobs.length());
                poll(jobs);
            } catch (Exception e) { error("تولید شروع نشد", e.getMessage()); }
        });
    }

    private void poll(JSONArray jobs) {
        io.execute(() -> {
            try {
                while (true) {
                    JSONObject b = new JSONObject(); b.put("jobs", jobs);
                    JSONObject r = post(API + "/v1/video/status", b);
                    JSONArray a = r.getJSONArray("jobs");
                    int done = 0, failed = 0;
                    for (int i=0;i<a.length();i++) {
                        String s = a.getJSONObject(i).optString("status");
                        if ("COMPLETED".equals(s)) done++;
                        if ("FAILED".equals(s)) failed++;
                    }
                    status("تولید AI: " + done + "/" + a.length());
                    if (failed > 0) { error("تولید ناقص شد", "حداقل یک صحنه شکست خورد."); return; }
                    if (done == a.length()) {
                        ArrayList<JSONObject> list = new ArrayList<>();
                        for (int i=0;i<a.length();i++) list.add(a.getJSONObject(i));
                        list.sort(Comparator.comparingInt(x -> x.optInt("index",0)));
                        download(list);
                        return;
                    }
                    Thread.sleep(POLL_MS);
                }
            } catch (Exception e) { error("پیگیری تولید شکست خورد", e.getMessage()); }
        });
    }

    private void download(List<JSONObject> jobs) {
        io.execute(() -> {
            try {
                File dir = new File(activity.getExternalFilesDir(null), "mjk_ai_clips");
                if (!dir.exists() && !dir.mkdirs()) throw new Exception("ساخت پوشه موقت ممکن نشد.");
                ArrayList<File> files = new ArrayList<>();
                for (int i=0;i<jobs.size();i++) {
                    File f = new File(dir, String.format("scene_%03d.mp4", i+1));
                    downloadFile(jobs.get(i).getString("video_url"), f);
                    files.add(f);
                    status("دریافت: " + (i+1) + "/" + jobs.size());
                }
                compose(files);
            } catch (Exception e) { error("دریافت ویدیو شکست خورد", e.getMessage()); }
        });
    }

    private void downloadFile(String u, File f) throws Exception {
        HttpURLConnection c = (HttpURLConnection) new URL(u).openConnection();
        c.setConnectTimeout(20000); c.setReadTimeout(60000); c.setInstanceFollowRedirects(true);
        try (InputStream in = new BufferedInputStream(c.getInputStream());
             FileOutputStream out = new FileOutputStream(f)) {
            byte[] buf = new byte[65536]; int n;
            while ((n=in.read(buf)) != -1) out.write(buf,0,n);
        } finally { c.disconnect(); }
    }

    private void compose(List<File> files) {
        activity.runOnUiThread(() -> {
            try {
                ArrayList<EditedMediaItem> items = new ArrayList<>();
                for (File f : files)
                    items.add(new EditedMediaItem.Builder(MediaItem.fromUri(Uri.fromFile(f))).build());

                EditedMediaItemSequence seq = EditedMediaItemSequence.withVideoFrom(items);
                Composition comp = new Composition.Builder(seq).build();

                File dir = new File(activity.getExternalFilesDir(null), "mjk_output");
                if (!dir.exists()) dir.mkdirs();
                File out = new File(dir, "MJK_AI_" + System.currentTimeMillis() + ".mp4");

                status("مونتاژ نهایی روی گوشی...");
                Transformer t = new Transformer.Builder(activity)
                        .setVideoMimeType(MimeTypes.VIDEO_H264)
                        .addListener(new Transformer.Listener() {
                            @Override public void onCompleted(Composition c, ExportResult result) {
                                try {
                                    Uri uri = publish(out);
                                    new AlertDialog.Builder(activity)
                                            .setTitle("ویدیو آماده شد")
                                            .setMessage("فایل در Movies/MJK Video AI ذخیره شد.")
                                            .setPositiveButton("اشتراک‌گذاری", (d,w) -> share(uri))
                                            .setNegativeButton("باشه", null).show();
                                } catch (Exception e) { error("انتقال فایل شکست خورد", e.getMessage()); }
                            }
                            @Override public void onError(Composition c, ExportResult result, ExportException e) {
                                error("مونتاژ شکست خورد", e.getMessage());
                            }
                        }).build();
                t.start(comp, out.getAbsolutePath());
            } catch (Exception e) { error("مونتاژ شروع نشد", e.getMessage()); }
        });
    }

    private Uri publish(File source) throws Exception {
        ContentValues v = new ContentValues();
        v.put(MediaStore.Video.Media.DISPLAY_NAME, source.getName());
        v.put(MediaStore.Video.Media.MIME_TYPE, "video/mp4");
        v.put(MediaStore.Video.Media.RELATIVE_PATH, Environment.DIRECTORY_MOVIES + "/MJK Video AI");
        v.put(MediaStore.Video.Media.IS_PENDING, 1);
        Uri uri = activity.getContentResolver().insert(MediaStore.Video.Media.EXTERNAL_CONTENT_URI, v);
        if (uri == null) throw new Exception("MediaStore نتوانست فایل را ایجاد کند.");
        try (InputStream in = new BufferedInputStream(new java.io.FileInputStream(source));
             java.io.OutputStream out = activity.getContentResolver().openOutputStream(uri)) {
            if (out == null) throw new Exception("خروجی MediaStore باز نشد.");
            byte[] buf = new byte[65536]; int n;
            while ((n=in.read(buf)) != -1) out.write(buf,0,n);
        } catch (Exception e) {
            activity.getContentResolver().delete(uri,null,null); throw e;
        }
        ContentValues done = new ContentValues(); done.put(MediaStore.Video.Media.IS_PENDING, 0);
        activity.getContentResolver().update(uri,done,null,null);
        return uri;
    }

    private void share(Uri uri) {
        Intent i = new Intent(Intent.ACTION_SEND);
        i.setType("video/mp4"); i.putExtra(Intent.EXTRA_STREAM,uri);
        i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        activity.startActivity(Intent.createChooser(i,"اشتراک‌گذاری ویدیو"));
    }

    private void error(String title, String message) {
        activity.runOnUiThread(() -> new AlertDialog.Builder(activity)
                .setTitle(title).setMessage(message == null ? "" : message)
                .setPositiveButton("باشه",null).show());
    }
}
