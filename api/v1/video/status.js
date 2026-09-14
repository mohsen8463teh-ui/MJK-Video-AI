const MODEL = "fal-ai/wan/v2.2-5b/text-to-video/fast-wan";

function json(res, status, body) {
  res.status(status).setHeader("Content-Type", "application/json");
  res.send(JSON.stringify(body));
}

export default async function handler(req, res) {
  if (req.method !== "POST") return json(res, 405, { ok: false, error: "method_not_allowed" });
  if (!process.env.FAL_KEY) {
    return json(res, 503, { ok: false, error: "fal_key_missing", message: "FAL_KEY is not configured." });
  }

  try {
    const body = typeof req.body === "string" ? JSON.parse(req.body) : (req.body || {});
    const jobs = Array.isArray(body.jobs) ? body.jobs : [];
    if (!jobs.length) return json(res, 400, { ok: false, error: "jobs_required" });

    const output = await Promise.all(jobs.map(async (job) => {
      const requestId = String(job.request_id || "");
      if (!requestId) return { index: job.index, status: "FAILED", error: "request_id_missing" };

      const statusUrl = job.status_url ||
        `https://queue.fal.run/${MODEL}/requests/${encodeURIComponent(requestId)}/status`;

      const r = await fetch(statusUrl, {
        headers: { "Authorization": `Key ${process.env.FAL_KEY}` }
      });

      const text = await r.text();
      let data;
      try { data = JSON.parse(text); } catch { data = { raw: text }; }

      if (!r.ok) {
        return { index: job.index, request_id: requestId, status: "FAILED", error: data?.detail || data?.message || `status HTTP ${r.status}` };
      }

      if (data.status !== "COMPLETED") {
        return {
          index: job.index,
          request_id: requestId,
          status: data.status || "UNKNOWN",
          queue_position: data.queue_position ?? null
        };
      }

      const responseUrl = data.response_url || job.response_url ||
        `https://queue.fal.run/${MODEL}/requests/${encodeURIComponent(requestId)}`;

      const rr = await fetch(responseUrl, {
        headers: { "Authorization": `Key ${process.env.FAL_KEY}` }
      });
      const resultText = await rr.text();
      let result;
      try { result = JSON.parse(resultText); } catch { result = { raw: resultText }; }

      if (!rr.ok) {
        return { index: job.index, request_id: requestId, status: "FAILED", error: result?.detail || result?.message || `result HTTP ${rr.status}` };
      }

      const videoUrl = result?.video?.url || result?.data?.video?.url || "";
      if (!videoUrl) {
        return { index: job.index, request_id: requestId, status: "FAILED", error: "completed_without_video_url" };
      }

      return {
        index: job.index,
        request_id: requestId,
        status: "COMPLETED",
        video_url: videoUrl
      };
    }));

    return json(res, 200, {
      ok: true,
      jobs: output.sort((a, b) => (a.index || 0) - (b.index || 0))
    });
  } catch (error) {
    console.error("mjk_video_status", error);
    return json(res, 500, {
      ok: false,
      error: "video_status_failed",
      message: error instanceof Error ? error.message : String(error)
    });
  }
}
