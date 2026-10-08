async page => {
  await page.getByRole('option', {name:'H-CTD16-US-BK · 朝天灯-四按键-美规-黑色',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'新建知识资料',exact:true});
  await dialog.getByRole('textbox',{name:'适用依据',exact:true}).fill('项目自编模拟A，仅限精确登记型号，用于独立页面核验');
  await dialog.getByRole('button',{name:'保存为新版本',exact:true}).click();
  await page.getByRole('button',{name:'独立审查5 A 连接排障',exact:true}).click();
  await page.getByRole('button',{name:'开始解析',exact:true}).click();
  await page.getByRole('button',{name:'重新解析，撤销旧核对',exact:true}).waitFor({timeout:20000});
  await page.getByRole('tab',{name:'原件与解析对照',exact:true}).click();
  await page.getByRole('textbox',{name:'人工核对备注（必填）',exact:true}).fill('独立审查5逐字对照自编原件，安全前提、停止条件与精确SKU均一致；不冒充厂家资料');
  await page.getByText('我已对照原件核对保留内容，确认型号范围；已明确排除不能作为完整依据的内容',{exact:true}).click();
  await page.getByRole('button',{name:'保存人工核对',exact:true}).click();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByRole('button',{name:'构建索引',exact:true}).click();
  await page.getByText('构建完成',{exact:true}).waitFor({timeout:30000});
}
