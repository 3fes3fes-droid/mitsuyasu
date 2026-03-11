exports.handler = async function(event) {
  const url = event.queryStringParameters?.url;
  if (!url) return { statusCode: 400, body: 'url parameter required' };

  const ALLOWED = [
    'news.yahoo.co.jp', 'www3.nhk.or.jp', 'www.asahi.com',
    'news.google.com', 'news.livedoor.com', 'gigazine.net',
    'rss.itmedia.co.jp', 'ascii.jp', 'news.mynavi.jp',
    'www.watch.impress.co.jp', 'pc.watch.impress.co.jp',
    'akiba-pc.watch.impress.co.jp', 'internet.watch.impress.co.jp',
    'www.4gamer.net', 'feeds.bbci.co.uk', 'trends.google.co.jp',
    'www.shinmai.co.jp', 'shimintimes.co.jp',
  ];

  let hostname;
  try { hostname = new URL(url).hostname; }
  catch { return { statusCode: 400, body: 'invalid url' }; }

  if (!ALLOWED.some(d => hostname === d || hostname.endsWith('.' + d))) {
    return { statusCode: 403, body: `domain not allowed: ${hostname}` };
  }

  try {
    const res = await fetch(url, {
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; RSSReader/1.0)', 'Accept': 'application/rss+xml, application/xml, text/xml, */*' },
      signal: AbortSignal.timeout(10000),
    });
    if (!res.ok) return { statusCode: res.status, body: `upstream error: ${res.status}` };
    const body = await res.text();
    return {
      statusCode: 200,
      headers: { 'Content-Type': res.headers.get('content-type') || 'text/xml', 'Access-Control-Allow-Origin': '*', 'Cache-Control': 'public, max-age=300' },
      body,
    };
  } catch(e) { return { statusCode: 500, body: `fetch error: ${e.message}` }; }
};
