async page => {
  await page.getByRole('dialog',{name:'检索试查',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  const prior=page.getByRole('article').filter({hasText:/记录 3 ·/});
  await prior.getByRole('button',{name:'恢复这个发布清单',exact:true}).click();
  await page.getByRole('button',{name:'恢复清单',exact:true}).click();
  await page.getByText('当前发布记录 5 · 2 份生效资料',{exact:true}).waitFor({timeout:10000});
}
