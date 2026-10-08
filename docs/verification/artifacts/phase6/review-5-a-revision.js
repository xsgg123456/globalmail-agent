async page => {
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'独立审查5 A 连接排障',exact:true}).click();
  await page.getByRole('button',{name:'修订正文 / 适用范围',exact:true}).click();
  const editor=page.getByRole('dialog',{name:'创建资料新版本',exact:true});
  const input=editor.getByRole('textbox',{name:'Markdown 正文（必填）',exact:true});
  await input.fill((await input.inputValue())+'\n\n# 草稿补充\n这是独立审查5新草稿，不应取代已发布第1版。');
  await editor.getByRole('button',{name:'保存为新版本',exact:true}).click();
  await page.getByRole('combobox',{name:'资料版本',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').waitFor();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByText('当前生效：第 1 版 · 发布记录 5',{exact:true}).waitFor();
  await page.getByRole('dialog',{name:'独立审查5 A 连接排障',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.getByRole('combobox',{name:'整批发布模型',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'Qwen3.7 · 1024维',exact:true}).click();
  await page.getByRole('combobox',{name:'独立审查5 A 连接排障候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
}
