"""SDK callback, async trace isolation and export masking smoke checks; no cloud export."""
import asyncio
import json
import os
from pathlib import Path

os.environ['LANGCHAIN_TRACING_V2']='false'
os.environ['LANGSMITH_TRACING']='false'
os.environ['LANGFUSE_MEDIA_UPLOAD_ENABLED']='false'

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_openai import ChatOpenAI
from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from langfuse.types import MaskOtelSpansResult, OtelSpanPatch
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from probe_provider import config
from probe_support import run_reported

MARKER='synthetic-person@example.invalid'
REPORT=Path(__file__).with_name('observability-results.json')


class CaptureExporter(SpanExporter):
    def __init__(self):
        self.spans=[]
        self.fail=False
        self.failed_exports=0

    def export(self,spans):
        if self.fail:
            self.failed_exports+=1
            return SpanExportResult.FAILURE
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self):
        pass


def main():
    exporter=CaptureExporter()
    masks=[0]
    def mask(*,params):
        patches={}
        for key,span in params.spans.items():
            remove=tuple(k for k,v in span.attributes.items() if MARKER in str(v))
            if remove:
                masks[0]+=len(remove)
                patches[key]=OtelSpanPatch(delete_attributes=remove,set_attributes={'probe.redacted':True})
        return MaskOtelSpansResult(span_patches=patches)

    lf=Langfuse(public_key='pk-lf-local-probe',secret_key='sk-lf-local-probe',base_url='http://127.0.0.1:1',
                tracer_provider=TracerProvider(),span_exporter=exporter,mask_otel_spans=mask,
                flush_at=128,flush_interval=1,timeout=1)
    cfg=config()
    model=ChatOpenAI(model=cfg['LLM_MODEL'],base_url=cfg['LLM_BASE_URL'],api_key=cfg['LLM_API_KEY'],
                    max_tokens=50,max_retries=0,timeout=30,use_responses_api=False,
                    extra_body={'enable_thinking':False})
    actual_usage=[]

    async def run_one(run_id):
        with lf.start_as_current_observation(name='mail_agent.'+run_id,metadata={'run_id':run_id},input=MARKER):
            await asyncio.sleep(0)
            answer=await model.ainvoke('Synthetic prompt '+MARKER,
                config={'callbacks':[CallbackHandler(public_key='pk-lf-local-probe')], 'run_name':'model.'+run_id})
            with lf.start_as_current_observation(name='business.'+run_id,input={'customer':MARKER}):
                if answer.usage_metadata:
                    actual_usage.append(answer.usage_metadata)
                return answer.content

    async def parallel():
        return await asyncio.gather(run_one('run-a'),run_one('run-b'))

    try:
        assert len(asyncio.run(parallel()))==2
        lf.flush()
        spans=list(exporter.spans)
        roots={s.name:s for s in spans if s.name.startswith('mail_agent.')}
        assert set(roots)=={'mail_agent.run-a','mail_agent.run-b'}
        assert roots['mail_agent.run-a'].context.trace_id != roots['mail_agent.run-b'].context.trace_id
        for run_id in ['run-a','run-b']:
            children=[s for s in spans if s.name in ('model.'+run_id,'business.'+run_id)]
            assert len(children)==2
            assert all(s.context.trace_id==roots['mail_agent.'+run_id].context.trace_id for s in children)
            assert all(s.parent.span_id==roots['mail_agent.'+run_id].context.span_id for s in children)
        assert masks[0]>0 and all(MARKER not in str(dict(s.attributes)) for s in spans)
        generations=[s for s in spans if s.name.startswith('model.')]
        assert len(generations)==2
        assert len(actual_usage)==2 and all(u['total_tokens']>0 for u in actual_usage)
        usage_attributes=[{k:v for k,v in s.attributes.items() if 'usage' in k or 'model' in k} for s in generations]
        assert all(any('usage' in k for k in attrs) for attrs in usage_attributes)

        exporter.fail=True
        model=FakeListChatModel(responses=['Synthetic response '+MARKER])
        assert asyncio.run(run_one('export-failure')).startswith('Synthetic response')
        lf.flush()
        assert exporter.failed_exports>0
        result={'scope':'local_sdk_real_qwen_callback_and_synthetic_export_failure_no_langfuse_server',
                'passed':True,'checks':[
                    {'name':'callback_and_manual_spans','passed':True,'span_count':len(spans),'generations':len(generations)},
                    {'name':'two_async_runs_have_separate_traces_and_correct_parents','passed':True},
                    {'name':'real_model_usage_recorded_once_per_generation','passed':True,'provider_usage':actual_usage,
                     'generation_usage_attributes':usage_attributes},
                    {'name':'export_mask_removes_synthetic_attributes','passed':True,'removed_attribute_count':masks[0]},
                    {'name':'exporter_failure_does_not_fail_model_result','passed':True,'failed_export_batches':exporter.failed_exports}],
                'not_tested':['real Langfuse server ingestion/UI','network timeout/queue saturation','complete production privacy filtering']}
        REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,ensure_ascii=False))
    finally:
        lf.shutdown()


if __name__=='__main__':
    run_reported(REPORT,main)
