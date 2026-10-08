async page => {
  await page.getByRole('dialog',{name:'发布记录与模型切换',exact:true}).getByRole('button',{name:'关闭此对话框',exact:true}).click();
  const values=[];
  for(const [label,key,title] of [['已下架','withdrawn','独立审查5 A 连接排障'],['有生效版本','published','独立审查5 B 书架灯检查'],['未发布','unpublished',null]]) {
    await page.getByRole('combobox',{name:'筛选发布状态',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]').click();
    const [response]=await Promise.all([
      page.waitForResponse(r=>r.url().includes('/knowledge/documents?')&&r.url().includes('publication='+key)),
      page.getByRole('option',{name:label,exact:true}).click()
    ]);
    const body=await response.json();
    values.push({label,key,status:response.status(),body});
    if(body.data.items.length!==(title?1:0)||title&&body.data.items[0].title!==title) throw new Error('Wrong publication filter '+key);
    if(title) await page.getByRole('button',{name:title,exact:true}).waitFor();
    else await page.getByText('暂无符合条件的资料，可以新建或导入准备资料',{exact:true}).waitFor();
    await page.screenshot({path:'docs/verification/artifacts/phase6/review-5-filter-'+key+'.png'});
  }
  await page.evaluate(v=>window.review5Filters=v,values);
  const filter=page.getByRole('combobox',{name:'筛选发布状态',exact:true}).locator('xpath=ancestor::div[contains(@class,"el-select__wrapper")]');
  await filter.hover(); await filter.locator('.el-select__clear').click();
  await page.getByRole('button',{name:'独立审查5 A 连接排障',exact:true}).waitFor();
}
