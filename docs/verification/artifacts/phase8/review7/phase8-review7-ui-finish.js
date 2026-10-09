async (page) => {
  const out='D:/Work_Project/globalmail-agent/tmp/phase8-review7/';
  const cid='140428bc-1654-42c8-b6e6-7ae22b5825b4';
  const id='d3e61c1a-8e60-4cfb-9abb-5976517f5a8f';
  const base='http://127.0.0.1:15174/api/v1';
  const measure=()=>{
    const p=document.querySelector('[aria-label="当前可见邮件"]');
    const i=p.querySelector('.el-image img');const b=p.querySelector('button[title]');
    return {viewport:innerWidth,pane:{width:p.clientWidth,height:p.clientHeight,scrollWidth:p.scrollWidth},
      image:i?{url:i.src,natural:i.naturalWidth,width:i.getBoundingClientRect().width,height:i.getBoundingClientRect().height}:null,
      filename:{title:b.title,disabled:b.disabled,width:b.getBoundingClientRect().width},text:p.innerText};
  };
  const sizes=[];
  for(const width of [1440,1280,900]){
    await page.setViewportSize({width,height:900});
    await page.waitForTimeout(500);
    await page.locator('[aria-label="当前可见邮件"]').evaluate(e=>e.scrollTop=e.scrollHeight);
    sizes.push(await page.evaluate(measure));
    await page.screenshot({path:out+'timeline-stable-'+width+'.png',fullPage:true});
  }
  await page.route('**/api/v1/attachments/**/preview?**',async route=>{
    if(new URL(route.request().url()).searchParams.get('thumbnail')==='true')
      await route.fulfill({status:503,contentType:'application/json',body:'{"detail":"review7_thumbnail_unavailable"}'});
    else await route.continue();
  });
  await page.reload();
  await page.getByRole('button',{name:/review7-ui@example.test/}).click();
  await page.locator('[aria-label="当前可见邮件"]').getByText('无法预览',{exact:true}).waitFor();
  await page.locator('[aria-label="当前可见邮件"]').evaluate(e=>e.scrollTop=e.scrollHeight);
  const fallback=await page.evaluate(measure);
  await page.screenshot({path:out+'thumbnail-error.png',fullPage:true});
  await page.locator('[aria-label="当前可见邮件"] button[title]').click();
  const drawer=page.getByRole('dialog');
  await drawer.locator('img').waitFor();
  await page.waitForFunction(()=>[...document.querySelectorAll('[role="dialog"] img')].some(i=>i.naturalWidth>0));
  const original=await drawer.locator('img').evaluate(i=>({natural:i.naturalWidth,url:i.src}));
  const readableBefore={};
  for(const [name,url] of Object.entries({original:base+'/attachments/'+id+'/preview?conversation_id='+cid,
      evidence:base+'/conversations/'+cid+'/visual-evidence?attachment_id='+id}))
    readableBefore[name]=(await page.request.get(url)).status();
  await page.screenshot({path:out+'original-on-thumbnail-error.png',fullPage:true});
  return {sizes,fallback,original,readableBefore};
}
