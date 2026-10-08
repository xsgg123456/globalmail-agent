async page => {
  const a=page.getByRole('combobox',{name:'独立审查5 A 连接排障候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]');
  const b=page.getByRole('combobox',{name:'独立审查5 B 书架灯检查候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]');
  await page.evaluate(v=>{window.review5Reopened=v;},{a:await a.innerText(),b:await b.innerText()});
  await page.getByRole('button',{name:'确认整批发布',exact:true}).click();
  await page.getByRole('button',{name:'整批发布',exact:true}).click();
  await page.getByText('操作已保存。',{exact:true}).waitFor({timeout:10000});
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-unknown-retry.png'});
  await page.unroute('**/api/v1/knowledge/releases');
}
