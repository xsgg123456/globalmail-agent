async page => {
  const d=page.getByRole('dialog',{name:'检索试查',exact:true});
  await d.getByRole('button',{name:'检查引用是否仍有效',exact:true}).click();
  await page.getByText('引用已停用或来源不完整，请重新试查。',{exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-old-reference-disabled.png'});
  await d.getByRole('button',{name:'检索试查',exact:true}).click();
  await page.getByText('这个型号和条件下没有合格证据。',{exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-withdraw-search-empty.png'});
  await d.getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('article').filter({hasText:/记录 3 ·/}).getByRole('button',{name:'恢复这个发布清单',exact:true}).click();
  await page.getByRole('button',{name:'恢复清单',exact:true}).click();
  await page.getByText('构建已失去发布资格，请检查原件、核对版本和下架记录后重新构建。',{exact:true}).waitFor();
  await page.getByText('当前发布记录 6 · 1 份生效资料',{exact:true}).waitFor();
}
