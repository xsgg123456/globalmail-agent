async page => {
  const dialog = page.getByRole('dialog', { name: '新建知识资料', exact: true });
  await dialog.getByRole('textbox', { name: '资料标题（必填）', exact: true }).fill('独立审查4 A 连接排障');
  await dialog.getByRole('combobox', { name: '品牌', exact: true }).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option', { name: 'OUTON', exact: true }).click();
  await dialog.getByRole('textbox', { name: '资料来源（必填）', exact: true }).fill('项目自编模拟资料，独立页面核验A，不是厂家说明');
  await dialog.getByRole('combobox', { name: '资料原本可用时间（必填）', exact: true }).fill('2026-10-08 10:00:00');
  await dialog.getByRole('combobox', { name: '资料原本可用时间（必填）', exact: true }).press('Enter');
  await dialog.getByRole('textbox', { name: 'Markdown 正文（必填）', exact: true }).fill('# 安全\n先断电，焦味立即停止转人工。\n\n# 操作\n检查外部连接，不拆封闭控制器。\n独立A仅适用于 H-CTD16-US-BK；断电后检查插头是否松动，仍不亮交人工。');
  await dialog.getByRole('button', { name: '添加型号适用范围', exact: true }).click();
  await dialog.getByRole('combobox', { name: '精确型号', exact: true }).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
}
