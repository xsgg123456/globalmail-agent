async page => {
  const a500=await page.evaluate(()=>window.review5Wire.find(x=>x.method==='POST'&&/\/build$/.test(x.url)&&JSON.parse(x.request).chunking_profile_key==='structure_v1_500').body.data.build_id);
  await page.getByRole('combobox',{name:'独立审查5 A 连接排障候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
  await page.getByRole('option',{name:new RegExp(a500.slice(0,8))}).click();
  const b=page.getByRole('combobox',{name:'独立审查5 B 书架灯检查候选构建',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]');
  await b.hover();
  await b.locator('.el-select__clear').click();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-release-selection.png'});
  await page.evaluate(()=>{window.review5Unknown=[];});
  let number=0;
  await page.route('**/api/v1/knowledge/releases',async route=>{
    const request=route.request();
    if(request.method()!=='POST') return route.continue();
    const response=await route.fetch();
    const item={number:++number,request:request.postData(),key:request.headers()['idempotency-key'],status:response.status(),response:await response.json()};
    await page.evaluate(v=>window.review5Unknown.push(v),item);
    if(number===1) await route.abort('failed'); else await route.fulfill({response});
  });
  await page.getByRole('button',{name:'确认整批发布',exact:true}).click();
  await page.getByRole('button',{name:'整批发布',exact:true}).click();
  await page.getByText('请求结果还未确认，请重试同一操作。输入已保留。',{exact:true}).waitFor({timeout:10000});
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-unknown-first.png'});
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  await page.getByRole('button',{name:'发布记录与模型切换',exact:true}).click();
  await page.getByRole('button',{name:'整批发布 / 切换向量模型',exact:true}).click();
  await page.getByRole('button',{name:'确认整批发布',exact:true}).waitFor();
  await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-unknown-reopened.png'});
}

