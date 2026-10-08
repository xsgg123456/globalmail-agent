async page => {
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'独立审查5 B 书架灯检查',exact:true}).click();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByRole('button',{name:'发布这个构建',exact:true}).click();
  await page.getByRole('button',{name:'发布',exact:true}).click();
  await page.getByText('当前生效：第 1 版 · 发布记录 3',{exact:true}).waitFor({timeout:10000});
  await page.getByRole('dialog',{name:'独立审查5 B 书架灯检查',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'检索试查',exact:true}).click();
  const d=page.getByRole('dialog',{name:'检索试查',exact:true});
  await d.getByRole('combobox',{name:'试查型号',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'H-CTD16-US-BK',exact:true}).click();
  await d.getByRole('textbox',{name:'检索问题',exact:true}).fill('Wie prüfe ich die externe Verbindung? Darf ich den Controller öffnen?');
  await d.getByRole('button',{name:'检索试查',exact:true}).click();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-search-loading.png'});
  await page.getByText('已找到当前有效的证据。',{exact:true}).waitFor({timeout:20000});
  await d.getByRole('button',{name:'检查引用是否仍有效',exact:true}).click();
  await page.getByText('引用仍有效。',{exact:true}).waitFor();
}
