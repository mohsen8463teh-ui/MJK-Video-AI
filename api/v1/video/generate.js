const MODEL = "fal-ai/wan/v2.2-5b/text-to-video/fast-wan";

function json(res, status, body) {
  res.status(status).setHeader("Content-Type", "application/json");
  res.send(JSON.stringify(body));
}

export default async function handler(req, res) {
  if (req.method !== "POST") return json(res, 405, { ok: false, error: "method_not_allowed" });
  if (!process.env.FAL_KEY) {
    return json(res, 503, {
      ok: false,
      error: "fal_key_missing",
      message: "FAL_KEY is not configured on the Vercel server."
    });
  }

  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    const prompt = String(body.prompt || "").trim();
    const seconds = Math.min(240, Math.max(5, Number(body.duration_seconds || 25)));
    const aspect = ["9:16", "16:9", "1:1"].includes(body.aspect_ratio) ? body.aspect_ratio : "9:16";
    const resolution = ["480p", "580p", "720p"].includes(body.resolution) ? body.resolution : "480p";

    if (!prompt) return json(res, 400, { ok: false, error: "prompt_required" });

    const clipCount = Math.ceil(seconds / 5);
    const shotTypes = [
      "wide establishing shot, slow cinematic camera movement",
      "medium shot, gentle camera push-in, natural subject movement",
      "close-up detail shot, shallow depth of field",
      "tracking shot following the main action",
      "low-angle cinematic shot, controlled camera movement",
      "over-the-shoulder shot, cinematic composition",
      "high-angle shot revealing the environment",
      "side profile shot, realistic lighting and movement",
      "handheld documentary-style shot, stable natural motion",
      "hero shot, dramatic lighting, slow controlled camera move",
      "macro detail shot, realistic textures and subtle motion",
      "final cinematic shot, gradual pull-back and visual resolution"
    ];

    const jobs = await Promise.all(Array.from({ length: clipCount }, async (_, index) => {
      const scenePrompt = [
        "Create one coherent AI-generated video shot for a larger story.",
        `Main concept: ${prompt}`,
        `Scene ${index + 1} of ${clipCount}.`,
        `Camera direction: ${shotTypes[index % shotTypes.length]}.`,
        "Keep the same subject identity, environment, visual style, lighting language and color mood throughout the project.",
        "No subtitles, no logos, no watermark, no UI and no random on-screen text.",
        "Believable physics, natural motion, cinematic composition."
      ].join(" ");

      const upstream = await fetch(`https://queue.fal.run/${MODEL}`, {
        method: "POST",
        headers: {
          "Authorization": `Key ${process.env.FAL_KEY}`,
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          prompt: scenePrompt,
          num_frames: 120,
          frames_per_second: 24,
          resolution,
          aspect_ratio: aspect,
          enable_safety_checker: true,
          enable_output_safety_checker: false,
          enable_prompt_expansion: false,
          acceleration: "regular",
          video_quality: "balanced",
          video_write_mode: "fast"
        })
      });

      const text = await upstream.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { raw: text }; }

      if (!upstream.ok) {
        const err = new Error(data?.detail || data?.message || `fal HTTP ${upstream.status}`);
        err.status = upstream.status;
        throw err;
      }

      return {
        index,
        request_id: data.request_id,
        status_url: data.status_url,
        response_url: data.response_url
      };
    }));

    const pricePerClip = resolution === "480p" ? 0.0125 : resolution === "580p" ? 0.01875 : 0.025;

    return json(res, 200, {
      ok: true,
      model: MODEL,
      duration_seconds: seconds,
      clip_count: clipCount,
      clip_seconds: 5,
      resolution,
      aspect_ratio: aspect,
      estimated_cost_usd: Number((clipCount * pricePerClip).toFixed(4)),
      jobs
    });
  } catch (error) {
    console.error("mjk_video_generate", error);
    return json(res, Number(error?.status) || 500, {
      ok: false,
      error: "video_submit_failed",
      message: error instanceof Error ? error.message : String(error)
    });
  }
}
