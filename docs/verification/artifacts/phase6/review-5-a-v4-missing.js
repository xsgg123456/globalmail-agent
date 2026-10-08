async page => {
  await page.getByRole('button',{name:'查看原件与核对结果',exact:true}).click();
  await page.getByRole('tab',{name:'原件与解析对照',exact:true}).click();
  await page.getByRole('link',{name:'下载原件',exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-source-compare.png'});
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByRole('combobox',{name:'向量模型',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'V4 · 1024维',exact:true}).click();
  await page.getByRole('button',{name:'构建索引',exact:true}).click();
  await page.getByText('构建完成',{exact:true}).nth(2).waitFor({timeout:30000});
  await page.getByRole('dialog',{name:'独立审查5 A 连接排障',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.getByRole('combobox',{name:'整批发布模型',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:'V4 · 1024维',exact:true}).click();
  await page.getByText('还缺 1 份生效资料的目标构建，暂不能整体发布。',{exact:true}).waitFor();
  if(!await page.getByRole('button',{name:'确认整批发布',exact:true}).isDisabled()) throw new Error('Missing B must block full space switch');
}
