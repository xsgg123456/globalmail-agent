async page => {
  await page.goto('http://127.0.0.1:15177/#/knowledge');
  await page.getByRole('heading',{name:'知识库',exact:true}).waitFor();
  await page.waitForFunction(()=>!document.querySelector('[class*="-enter-active"], [class*="-leave-active"]'));
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('[class*="-enter-active"], [class*="-leave-active"]'));
  await page.getByText('当前发布记录 6 · 1 份生效资料',{exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-release-dark-900.png'});
  await page.setViewportSize({width:1440,height:1000});
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-release-dark-1440.png'});
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'检索试查',exact:true}).click();
  const d=page.getByRole('dialog',{name:'检索试查',exact:true});
  await d.getByRole('combobox',{name:'试查型号',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'F-SJ001-US-BK',exact:true}).click();
  await d.getByRole('textbox',{name:'检索问题',exact:true}).fill('How can I safely check a loose bookshelf lamp plug?');
  const [response]=await Promise.all([
    page.waitForResponse(r=>r.url().endsWith('/knowledge/search')&&r.request().method()==='POST',{timeout:20000}),
    d.getByRole('button',{name:'检索试查',exact:true}).click()
  ]);
  await page.evaluate(v=>window.review5DarkSearch=v,await response.json());
  await page.getByText('已找到当前有效的证据。',{exact:true}).waitFor({timeout:20000});
  await d.getByRole('button',{name:'检查引用是否仍有效',exact:true}).click();
  await page.getByText('引用仍有效。',{exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-search-dark-1440.png'});
  await page.setViewportSize({width:900,height:1000});
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-search-dark-900.png'});
}
