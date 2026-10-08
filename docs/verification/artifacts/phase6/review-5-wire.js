async page => {
  page.setDefaultTimeout(5000);
  await page.evaluate(() => { window.review5Wire = []; });
  page.on('response', async response => {
    const request = response.request(), url = request.url();
    if (!url.includes('/api/v1/knowledge')) return;
    if (request.method() !== 'POST' && !/references|index|releases/.test(url)) return;
    try {
      const item = {url, method: request.method(), key: request.headers()['idempotency-key'], request: request.postData(), status: response.status(), body: await response.json()};
      await page.evaluate(value => window.review5Wire.push(value), item);
    } catch { /* Aborted response captured independently by unknown route. */ }
  });
}
