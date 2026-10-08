async page => {
  await page.getByRole('option',{name:/^F-SJ001-US-BK ·/}).click();
  const d=page.getByRole('dialog',{name:'新建知识资料',exact:true});
  await d.getByRole('textbox',{name:'适用依据',exact:true}).fill('项目自编模拟B，仅限OUTONLIFE精确登记型号，用于独立页面核验');
  await d.getByRole('button',{name:'保存为新版本',exact:true}).click();
  await page.getByRole('button',{name:'独立审查5 B 书架灯检查',exact:true}).click();
  await page.getByRole('button',{name:'开始解析',exact:true}).click();
  await page.getByRole('button',{name:'重新解析，撤销旧核对',exact:true}).waitFor({timeout:20000});
  await page.getByRole('tab',{name:'原件与解析对照',exact:true}).click();
  await page.getByRole('textbox',{name:'人工核对备注（必填）',exact:true}).fill('逐字核对自编B原件，安全停止及书架灯精确SKU保留，不冒充厂家说明');
  await page.getByText('我已对照原件核对保留内容，确认型号范围；已明确排除不能作为完整依据的内容',{exact:true}).click();
  await page.getByRole('button',{name:'保存人工核对',exact:true}).click();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByRole('button',{name:'构建索引',exact:true}).click();
  await page.getByText('构建完成',{exact:true}).waitFor({timeout:30000});
  await page.getByRole('dialog',{name:'独立审查5 B 书架灯检查',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
}
