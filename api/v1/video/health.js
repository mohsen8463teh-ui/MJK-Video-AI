export default function handler(req, res) {
  res.status(200).json({
    ok: true,
    service: "MJK Video AI Proxy",
    fal_configured: Boolean(process.env.FAL_KEY),
    model: "fal-ai/wan/v2.2-5b/text-to-video/fast-wan"
  });
}
