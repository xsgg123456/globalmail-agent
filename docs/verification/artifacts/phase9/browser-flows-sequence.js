async (page) => {
  const proof={events:[], frontend_rejections:[], backend_rejections:[]};
  const panel=()=>page.getByRole('button',{name:'售后申请与模拟执行',exact:true});
  const control=()=>page.getByRole('region',{name:'模拟售后控制台',exact:true});
  async function expand(){if(await panel().getAttribute('aria-expanded')!=='true')await panel().click();}
  async function choose(label){if(await control().getByRole('combobox',{name:'当前可用操作'}).getAttribute('aria-expanded')!=='true')await control().locator('.el-select').first().click();await page.getByRole('option',{name:label,exact:true}).click();}
  async function fill(values){for(const [label,value] of Object.entries(values))await control().getByRole('textbox',{name:label,exact:true}).fill(value);}
  async function commit(label,values={},expectStatus=200){
    await choose(label);await fill(values);
    await control().getByRole('button',{name:'确认模拟记录',exact:true}).click();
    const responsePromise=page.waitForResponse(r=>r.url().endsWith('/events')&&r.request().method()==='POST');
    await page.getByRole('button',{name:'确认记录',exact:true}).click();
    const response=await responsePromise,body=await response.json();
    if(response.status()!==expectStatus)throw new Error(label+':'+JSON.stringify(body));
    if(expectStatus!==200){proof.backend_rejections.push({event:label,status:response.status(),reason:body.msg});return;}
    await page.getByText('模拟记录已保存，请以刷新后的申请和执行回执核对进度。',{exact:true}).waitFor();
    proof.events.push({event:body.data.event,id:body.data.operation_id,version:body.data.operation_version});
  }
  async function selectScene(number){
    await page.getByRole('dialog').first().getByRole('button').first().click();
    await page.getByRole('button',{name:new RegExp('customer-base-outon-'+number+'@')}).click();
    await page.getByRole('button',{name:'处理详情与人审',exact:true}).click();
    await expand();
    const op=number==='07'?'OP-8c5bf66730f74be5a0c90e5bd5b2616b':'OP-d554d75fd59f44b0881b78a537399bca';
    await page.waitForFunction(op=>Array.from(document.querySelectorAll('section')).some(el=>el.getAttribute('aria-label')==='售后申请与模拟执行'&&el.innerText.includes(op)),op);
  }
  if(!await panel().isVisible())await page.getByRole('button',{name:'处理详情与人审',exact:true}).click();
  await expand();
  const refund=await page.request.get('http://127.0.0.1:15174/api/v1/conversations/3bb18055-5741-4515-bb70-e605ce2b2b22/business');
  const refundBody=await refund.json();
  proof.refund={http:refund.status(),refunded_minor:refundBody.data.data.orders[0].refunded_minor,pending_minor:refundBody.data.data.orders[0].pending_refund_minor};
  if(proof.refund.refunded_minor!==5499||proof.refund.pending_minor!==0)throw new Error('refund_not_applied_exactly');
  await selectScene('07');
  const spareBefore=await(await page.request.get('http://127.0.0.1:15174/api/v1/conversations/f99d6dea-ee29-4b1f-b669-aa45a3c09f7f/operations')).json();
  proof.spare_before={executions:spareBefore.data.data.executions.length,parcel:spareBefore.data.data.shipments[0]?.status};
  if(proof.spare_before.executions!==1||proof.spare_before.parcel!=='label_created')throw new Error('spare_initial_state_not_label');
  await page.screenshot({path:'D:/Work_Project/globalmail-agent/docs/verification/artifacts/phase9/spare-label-not-shipped.png',fullPage:true});
  await commit('记录承运商已收件',{'实际模拟回执或标签编号':'SIM-CARRIER-ACCEPTED-UI','承运商':'UI Simulation Carrier','运单号':'SIM-TRACK-UI'});
  await commit('记录实际模拟成功回执',{'实际模拟回执或标签编号':'SIM-ERP-UI-1'});
  await commit('记录物流已送达',{'实际模拟回执或标签编号':'SIM-CARRIER-DELIVERED-UI'});
  await selectScene('05');
  await commit('建立模拟执行单');
  await choose('建立退货资料或物流标签');
  await control().getByRole('button',{name:'确认模拟记录',exact:true}).click();
  await control().getByText('退货授权须填写授权编号、模拟退货地址和包装说明。',{exact:true}).waitFor();
  proof.frontend_rejections.push('missing_return_documents');
  await commit('建立退货资料或物流标签',{'退货授权编号':'SIM-RMA-UI','模拟退货地址':'模拟仓库 9 号，仅用于本次测试','包装说明':'完整包装并附上模拟授权编号'});
  await commit('记录仓库已收件',{'实际模拟回执或标签编号':'SIM-WAREHOUSE-UI','实际收件或质检合格数量':'1'});
  await choose('记录仓库质检通过');
  await fill({'实际模拟回执或标签编号':'SIM-INSPECT-UI','实际收件或质检合格数量':'1'});
  await control().locator('.el-select').last().click();await page.getByRole('option',{name:'通过',exact:true}).click();
  await control().getByRole('button',{name:'确认模拟记录',exact:true}).click();
  const inspectionPromise=page.waitForResponse(r=>r.url().endsWith('/events')&&r.request().method()==='POST');
  await page.getByRole('button',{name:'确认记录',exact:true}).click();
  const inspection=await inspectionPromise; if(inspection.status()!==200)throw new Error('inspection_failed');
  await page.getByText('模拟记录已保存，请以刷新后的申请和执行回执核对进度。',{exact:true}).waitFor();
  await commit('记录实际模拟成功回执',{'实际模拟回执或标签编号':'SIM-RETURN-COMPLETED-UI'});
  await page.screenshot({path:'D:/Work_Project/globalmail-agent/docs/verification/artifacts/phase9/return-completed.png',fullPage:true});
  proof.final=[];
  for(const id of ['3bb18055-5741-4515-bb70-e605ce2b2b22','f99d6dea-ee29-4b1f-b669-aa45a3c09f7f','ad457328-4697-4b71-95e9-ef47eca01de4']){
    const data=(await(await page.request.get('http://127.0.0.1:15174/api/v1/conversations/'+id+'/operations')).json()).data.data;
    if(data.operations[0].status!=='succeeded'||data.executions.length!==1)throw new Error('final_ledger_not_succeeded');
    proof.final.push({id,kind:data.operations[0].kind,status:data.operations[0].status,executions:data.executions.length,
      shipments:data.shipments.map(r=>({status:r.status,receipt:r.receipt_ref})),returns:data.returns.map(r=>({received:r.received,inspection:r.inspection,address:r.return_address,packing:r.packing_instructions,postage:r.postage_responsibility}))});
  }
  return proof;
}
