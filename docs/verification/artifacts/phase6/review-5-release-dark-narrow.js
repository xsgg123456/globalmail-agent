async page => {
  await page.setViewportSize({width:900,height:1000});
  await page.waitForFunction(()=>document.documentElement.classList.contains('dark'));
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('[class*="-enter-active"], [class*="-leave-active"]'));
  const actual = await page.evaluate(()=>({width:window.innerWidth,bodyWidth:document.documentElement.scrollWidth,dark:document.documentElement.classList.contains('dark')}));
  if(actual.width!==900||actual.bodyWidth!==900||!actual.dark) throw new Error(JSON.stringify(actual));
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-release-dark-900.png',fullPage:true});
  console.log(JSON.stringify(actual));
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
}
