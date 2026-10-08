async page => {
  page.setDefaultTimeout(5000);
  await page.getByRole('button',{name:'独立审查5 A 连接排障',exact:true}).click();
  await page.getByRole('tab',{name:'索引与发布',exact:true}).click();
  await page.getByText('当前生效：第 1 版 · 发布记录 5',{exact:true}).waitFor();
  await page.getByRole('button',{name:'下架这份资料',exact:true}).click();
  await page.getByRole('button',{name:'下架',exact:true}).click();
  await page.getByText('资料已下架，重新构建并发布后才能恢复。',{exact:true}).waitFor({timeout:10000});
}
