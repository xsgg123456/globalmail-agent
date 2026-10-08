async page => {
  const b = page.getByRole('combobox', {name:'独立审查4 B 书架灯检查候选构建',exact:true})
    .locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]');
  await b.hover();
  await b.locator('.el-select__clear').click();
  await page.evaluate(() => window.review4Unknown=[]);
  let number=0;
  await page.route('**/api/v1/knowledge/releases', async route => {
    const request = route.request();
    if(request.method()!=='POST') return route.continue();
    const response = await route.fetch();
    const record = {number:++number, request:request.postData(), key:request.headers()['idempotency-key'],
      status:response.status(), response:await response.json()};
    await page.evaluate(value=>window.review4Unknown.push(value),record);
    if(number===1) await route.abort('failed');
    else await route.fulfill({response});
  });
}
