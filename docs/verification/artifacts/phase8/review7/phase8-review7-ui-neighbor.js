async(page)=>{
  const out='D:/Work_Project/globalmail-agent/tmp/phase8-review7/';
  await page.goto('http://127.0.0.1:15174/#/knowledge');
  await page.getByRole('heading',{name:'知识库',exact:true}).waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({path:out+'neighbor-knowledge.png',fullPage:true});
  const knowledge=await page.locator('main').innerText();
  await page.goto('http://127.0.0.1:15174/#/system-status');
  await page.getByText('本机运行状态',{exact:true}).waitFor();
  await page.waitForTimeout(1200);
  await page.screenshot({path:out+'neighbor-system-status.png',fullPage:true});
  return {knowledge,systemStatus:await page.locator('main').innerText()};
}
