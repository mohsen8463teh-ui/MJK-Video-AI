export default async function handler(req, res) {
  const path = Array.isArray(req.query.path)
    ? req.query.path.join("/")
    : (req.query.path || "");

  const queryIndex = req.url.indexOf("?");
  const query = queryIndex >= 0 ? req.url.slice(queryIndex) : "";

  const target =
    `https://mjk-video-ai.onrender.com/v1/${path}` + query;

  try {
    const headers = { ...req.headers };

    delete headers.host;
    delete headers["content-length"];

    let body;

    if (!["GET", "HEAD"].includes(req.method)) {
      const chunks = [];
      for await (const chunk of req) chunks.push(chunk);
      body = Buffer.concat(chunks);
    }

    const upstream = await fetch(target, {
      method: req.method,
      headers,
      body,
      redirect: "follow"
    });

    res.status(upstream.status);

    upstream.headers.forEach((value, key) => {
      if (!["content-encoding", "transfer-encoding", "connection"].includes(key)) {
        res.setHeader(key, value);
      }
    });

    const data = Buffer.from(await upstream.arrayBuffer());
    res.send(data);
  } catch (error) {
    res.status(502).json({
      ok: false,
      error: "proxy_error",
      message: error instanceof Error ? error.message : String(error)
    });
  }
}
