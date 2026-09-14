export default function handler(req, res) {
  res.status(404).json({
    ok: false,
    error: "route_not_found",
    message: "MJK Video AI API route not found."
  });
}
