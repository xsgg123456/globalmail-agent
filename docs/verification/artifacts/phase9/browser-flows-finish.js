async(page)=>{
  const control=page.getByRole('region',{name:'模拟售后控制台',exact:true});
  await page.getByRole('option',{name:'记录仓库质检通过',exact:true}).click();
  await control.getByRole('textbox',{name:'实际模拟回执或标签编号',exact:true}).fill('SIM-INSPECT-UI');
  await control.getByRole('textbox',{name:'实际收件或质检合格数量',exact:true}).fill('1');
  await control.locator('.el-select').last().click();
  await page.getByRole('option',{name:'通过',exact:true}).click();
  await control.getByRole('button',{name:'确认模拟记录',exact:true}).click();
  const inspectionPromise=page.waitForResponse(r=>r.url().endsWith('/events')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'确认记录',exact:true}).click();
  const inspection=await inspectionPromise;if(inspection.status()!==200)throw new Error('inspection_failed');
  await page.getByText('模拟记录已保存，请以刷新后的申请和执行回执核对进度。',{exact:true}).waitFor();
  await page.getByRole('button',{name:'刷新售后记录',exact:true}).click();
  await control.locator('.el-select').first().click();
  await page.getByRole('option',{name:'记录实际模拟成功回执',exact:true}).click();
  await control.getByRole('textbox',{name:'实际模拟回执或标签编号',exact:true}).fill('SIM-RETURN-COMPLETED-UI');
  await control.getByRole('button',{name:'确认模拟记录',exact:true}).click();
  const successPromise=page.waitForResponse(r=>r.url().endsWith('/events')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'确认记录',exact:true}).click();
  const success=await successPromise;if(success.status()!==200)throw new Error('return_complete_failed');
  await page.getByText('模拟记录已保存，请以刷新后的申请和执行回执核对进度。',{exact:true}).waitFor();
  const proof={inspection_http:inspection.status(),success_http:success.status(),final:[]};
  for(const id of ['3bb18055-5741-4515-bb70-e605ce2b2b22','f99d6dea-ee29-4b1f-b669-aa45a3c09f7f','ad457328-4697-4b71-95e9-ef47eca01de4']){
    const response=await page.request.get('http://127.0.0.1:15174/api/v1/conversations/'+id+'/operations');
    const data=(await response.json()).data.data;
    if(response.status()!==200||data.operations[0].status!=='succeeded'||data.executions.length!==1)throw new Error('final_ledger_not_succeeded');
    proof.final.push({id,kind:data.operations[0].kind,status:data.operations[0].status,executions:data.executions.length,
      receipt:data.executions[0].receipt_ref,amount_minor:data.executions[0].amount_minor,
      shipments:data.shipments.map(r=>({status:r.status,receipt:r.receipt_ref})),
      returns:data.returns.map(r=>({received:r.received,inspection:r.inspection,address:r.return_address,packing:r.packing_instructions,postage:r.postage_responsibility}))});
  }
  await page.screenshot({path:'D:/Work_Project/globalmail-agent/docs/verification/artifacts/phase9/return-completed.png',fullPage:true});
  return proof;
}
