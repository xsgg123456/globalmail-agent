async(page)=>{
  const out='D:/Work_Project/globalmail-agent/tmp/phase8-review7/';
  await page.getByRole('dialog',{name:'Agent 处理记录与人审'}).getByRole('button',{name:'关闭此对话框'}).click();
  await page.locator('[aria-label="当前可见邮件"] button[title]').click();
  await page.getByRole('button',{name:'撤销这张图片证据',exact:true}).click();
  await page.getByRole('button',{name:'确认撤销',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('[aria-label="当前可见邮件"] button[title]')?.disabled===true);
  const dom=await page.locator('[aria-label="当前可见邮件"]').evaluate(p=>({images:p.querySelectorAll('img').length,
    filenameDisabled:p.querySelector('button[title]').disabled,text:p.innerText,client:p.clientWidth,scroll:p.scrollWidth}));
  const base='http://127.0.0.1:15174/api/v1';
  const cid='140428bc-1654-42c8-b6e6-7ae22b5825b4',id='d3e61c1a-8e60-4cfb-9abb-5976517f5a8f';
  const http={};
  for(const [name,url] of Object.entries({thumbnail:base+'/attachments/'+id+'/preview?conversation_id='+cid+'&thumbnail=true',
     original:base+'/attachments/'+id+'/preview?conversation_id='+cid,
     evidence:base+'/conversations/'+cid+'/visual-evidence?attachment_id='+id})){
    const r=await page.request.get(url);http[name]={status:r.status(),body:await r.text(),cache:r.headers()['cache-control']};
  }
  await page.screenshot({path:out+'after-revoke-900.png',fullPage:true});
  if(dom.images!==0||!dom.filenameDisabled||Object.values(http).some(r=>r.status!==410))throw Error('revocation_failed');
  return {dom,http};
}
