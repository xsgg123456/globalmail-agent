async page => {
  await page.waitForFunction(()=>!document.documentElement.classList.contains('dark'));
  await page.getByRole('button',{name:'独立审查5 B 书架灯检查',exact:true}).click();
  await page.getByRole('tab',{name:'原件与解析对照',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('[class*="-enter-active"], [class*="-leave-active"]'));
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-source-light-900.png',fullPage:true});
  await page.getByRole('dialog',{name:'独立审查5 B 书架灯检查',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('[class*="-enter-active"], [class*="-leave-active"]'));
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-release-light-900.png',fullPage:true});
}
