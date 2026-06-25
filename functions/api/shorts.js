// Cloudflare Pages Function — proxies YouTube Data API calls server-side
// so the API key never reaches the browser/public HTML.
// Requires: set YOUTUBE_API_KEY as an encrypted secret in
// Cloudflare dashboard → Workers & Pages → team-gaia-site → Settings →
// Variables and Secrets → Add → type "Secret".

export async function onRequestGet(context) {
  const { env } = context;
  const API_KEY = env.YOUTUBE_API_KEY;
  const HANDLE = "michaelsawyer627";

  if (!API_KEY) {
    return new Response(JSON.stringify({ error: "Server not configured" }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }

  try {
    const chRes = await fetch(
      `https://www.googleapis.com/youtube/v3/channels?part=contentDetails&forHandle=${HANDLE}&key=${API_KEY}`
    );
    const ch = await chRes.json();
    const uploadsId = ch.items[0].contentDetails.relatedPlaylists.uploads;

    const plRes = await fetch(
      `https://www.googleapis.com/youtube/v3/playlistItems?part=contentDetails&maxResults=50&playlistId=${uploadsId}&key=${API_KEY}`
    );
    const pl = await plRes.json();
    const ids = pl.items.map(i => i.contentDetails.videoId);

    const vdRes = await fetch(
      `https://www.googleapis.com/youtube/v3/videos?part=contentDetails,statistics,snippet&id=${ids.join(",")}&key=${API_KEY}`
    );
    const vd = await vdRes.json();

    // Return only the fields the front end needs — never the raw API response.
    const items = vd.items.map(v => ({
      id: v.id,
      title: v.snippet.title,
      thumbnails: v.snippet.thumbnails,
      viewCount: parseInt(v.statistics.viewCount || 0),
      publishedAt: v.snippet.publishedAt,
      duration: v.contentDetails.duration
    }));

    return new Response(JSON.stringify({ items }), {
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=600" // 10 min edge cache — keeps quota usage low
      }
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: "Failed to load shorts" }), {
      status: 502,
      headers: { "Content-Type": "application/json" }
    });
  }
}
