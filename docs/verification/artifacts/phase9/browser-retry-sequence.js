async (page) => {
  const panel=page.getByRole('button',{name:'售后申请与模拟执行',exact:true});
  if (await panel.getAttribute('aria-expanded') !== 'true') await panel.click();
  const control=page.getByRole('region',{name:'模拟售后控制台',exact:true});
  await page.keyboard.press('Escape');
  await control.locator('.el-select').first().click();
  await page.getByRole('option',{name:'记录结果未知',exact:true}).click();
  await control.getByRole('textbox',{name:'失败、未知或对账依据'}).fill('工程故障测试：控制器未取得实际结果，等待核对原尝试');
  const calls=[];
  page.on('request', request => {
    if(request.url().endsWith('/events') && request.method()==='POST')
      calls.push({key:request.headers()['idempotency-key'],payload:request.postDataJSON()});
  });
  let committed;
  await page.route('**/api/v1/simulation/branches/*/events', async route => {
    const response=await route.fetch();
    const body=await response.json();
    committed={status:response.status(),conversation:body.data.conversation_id,event_id:body.data.event_id};
    await route.abort('failed');
  },{times:1});
  await control.getByRole('button',{name:'确认模拟记录',exact:true}).click();
  await page.getByRole('button',{name:'确认记录',exact:true}).click();
  await page.getByRole('button',{name:'核对原请求结果',exact:true}).waitFor();
  await page.getByRole('button',{name:'刷新售后记录',exact:true}).click();
  await page.getByRole('button',{name:'核对原请求结果',exact:true}).click();
  await page.getByRole('button',{name:'确认核对',exact:true}).click();
  await page.getByText('模拟记录已保存，请以刷新后的申请和执行回执核对进度。',{exact:true}).waitFor();
  const response=await page.request.get(new URL('/api/v1/conversations/'+committed.conversation+'/operations', page.url()).href);
  const body=await response.json(), data=body.data.data;
  if(calls.length!==2 || calls[0].key!==calls[1].key || JSON.stringify(calls[0].payload)!==JSON.stringify(calls[1].payload)
    || committed.status!==200 || data.executions.length!==1 || data.executions[0].status!=='unknown')
    throw new Error('lost_response_retry_not_proven');
  await page.screenshot({path:'D:/Work_Project/globalmail-agent/docs/verification/artifacts/phase9/lost-response-recovered.png',fullPage:true});
  return {committed,calls,executions:data.executions.map(row=>({id:row.execution_id,status:row.status})),operations:data.operations.length};
}
