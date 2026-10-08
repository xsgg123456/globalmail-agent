async page => {
  const dialog = page.getByRole('dialog', { name: '新建知识资料', exact: true });
  await dialog.getByRole('textbox', { name: '资料标题（必填）', exact: true }).fill('独立审查5 B 书架灯检查');
  await dialog.getByRole('combobox', { name: '品牌', exact: true }).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option', { name: 'OUTONLIFE', exact: true }).click();
  await dialog.getByRole('textbox', { name: '资料来源（必填）', exact: true }).fill('项目自编模拟资料，独立页面核验B，不是厂家说明');
  const date = dialog.getByRole('combobox', { name: '资料原本可用时间（必填）', exact: true });
  await date.fill('2026-10-08 10:00:00');
  await date.press('Enter');
  await dialog.getByRole('textbox', { name: 'Markdown 正文（必填）', exact: true }).fill('# 安全\n先断电，焦味立即停止转人工。\n\n# 操作\n检查外部连接，不拆封闭控制器。\n独立B仅适用于 F-SJ001-US-BK；书架灯接头松动时检查外部插头，反复失败停止操作交人工。');
  await dialog.getByRole('button', { name: '添加型号适用范围', exact: true }).click();
  await dialog.getByRole('combobox', { name: '精确型号', exact: true }).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
}

