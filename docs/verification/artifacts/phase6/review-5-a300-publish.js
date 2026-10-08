async page => {
  await page.getByRole('combobox',{name:'切分方案',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'结构切分 300 代理tokens',exact:true}).click();
  await page.getByRole('button',{name:'构建索引',exact:true}).click();
  await page.getByText('构建完成',{exact:true}).nth(1).waitFor({timeout:30000});
  await page.getByRole('button',{name:'发布这个构建',exact:true}).nth(1).click();
  await page.getByRole('button',{name:'发布',exact:true}).click();
  await page.getByText('当前生效：第 1 版 · 发布记录 1',{exact:true}).waitFor({timeout:10000});
  await page.getByRole('dialog',{name:'独立审查5 A 连接排障',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'新建资料',exact:true}).click();
}
