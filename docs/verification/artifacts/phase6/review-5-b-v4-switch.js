async page => {
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'独立审查5 B 书架灯检查',exact:true}).click();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByRole('combobox',{name:'向量模型',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'V4 · 1024维',exact:true}).click();
  await page.getByRole('button',{name:'构建索引',exact:true}).click();
  await page.getByText('构建完成',{exact:true}).nth(1).waitFor({timeout:30000});
  await page.getByRole('dialog',{name:'独立审查5 B 书架灯检查',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.getByRole('combobox',{name:'独立审查5 B 书架灯检查候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:/text-embedding-v4/}).click();
  await page.getByRole('button',{name:'确认整批发布',exact:true}).click();
  await page.getByRole('button',{name:'整批发布',exact:true}).click();
  await page.getByText('当前发布记录 4 · 2 份生效资料',{exact:true}).waitFor({timeout:10000});
}
