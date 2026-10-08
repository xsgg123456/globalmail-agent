async page => {
  const d=page.getByRole('dialog',{name:'检索试查',exact:true});
  await page.route('**/api/v1/knowledge/search',route=>route.abort('failed'));
  await d.getByRole('textbox',{name:'检索问题',exact:true}).fill('A bookshelf connector is loose. What should I do safely?');
  await d.getByRole('button',{name:'检索试查',exact:true}).click();
  await page.getByText('请求结果还未确认，请重试同一操作。输入已保留。',{exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-search-error.png'});
  if(await d.getByRole('button',{name:'检查引用是否仍有效',exact:true}).count()) throw new Error('Network error must not retain old evidence');
  await page.unroute('**/api/v1/knowledge/search');
  await d.getByRole('button',{name:'检索试查',exact:true}).click();
  await page.getByText('已找到当前有效的证据。',{exact:true}).waitFor({timeout:20000});
  await d.getByRole('combobox',{name:'试查用途',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'历史复盘',exact:true}).click();
  if(!await d.getByRole('button',{name:'检索试查',exact:true}).isDisabled()) throw new Error('Historical time is mandatory');
  const date=d.getByRole('combobox',{name:'可用时间截点',exact:true});
  await date.fill('2026-10-08 11:00:00'); await date.press('Enter');
  await d.getByRole('button',{name:'检索试查',exact:true}).click();
  await page.getByText('当前用途还没有合法的发布资料，无法试查。',{exact:true}).waitFor();
}
