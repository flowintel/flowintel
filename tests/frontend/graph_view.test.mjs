import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Script, createContext } from 'node:vm';
const root=new URL('../../',import.meta.url);
const source=await readFile(new URL('app/static/js/case/timeline_graph.js',root),'utf8');
const adapter=await readFile(new URL('app/static/js/case/flowtime_graph_view.js',root),'utf8');
const record=id=>({id,date_text:'2026-11-19 08:00',date_parsed:'2026-11-19 08:00',description:`Event ${id}`});
const response=(events=[record(1)])=>({status:200,json:async()=>({events,links:[]})});
// The graph itself (Pivotick) is not drawn here: its container is absent, so only the data side runs.
function harness(fetch=async()=>response()){
  const mounted=[],unmounted=[],requests=[],emitted=[];
  const context=createContext({
    Vue:{ref:value=>({value}),nextTick:async()=>{},onMounted:fn=>mounted.push(fn),onBeforeUnmount:fn=>unmounted.push(fn)},
    AbortController,localStorage:{getItem:()=>null,setItem(){}},flow_loader:{},setTimeout,clearTimeout,
    fetch:(url,options)=>{requests.push({url,options});return fetch(url,options);},
    document:{getElementById:id=>id==='csrf_token'?{value:'test-csrf'}:null,removeEventListener(){},addEventListener(){}},
    display_toast:async()=>{},create_message(){},confirmDelete:async()=>true,touchCaseLastModif(){},
  });
  new Script(source.replace(/^import .*$/gm,'').replace('export default','globalThis.component =')).runInContext(context);
  const api=context.component.setup({case_id:42,cases_info:{permission:{admin:true}}},{emit:name=>emitted.push(name)});
  return{api,requests,emitted,mount:()=>mounted[0](),unmount:()=>unmounted[0]()};
}
test('Flowintel mounts the existing Vue graph component in the custom slot and unmounts it on cleanup',()=>{
  const component={},apps=[];let info={permission:{admin:true}};const changed=()=>{};
  const context=createContext({timeline_graph:component,Vue:{h:(type,props)=>({type,props}),createApp:options=>{const app={options,mount(container){this.container=container;},unmount(){this.unmounted=true;}};apps.push(app);return app;}}});
  new Script(adapter.replace(/^import .*$/gm,'').replace('export function','function')).runInContext(context);
  const view=context.createFlowtimeGraphView({caseId:42,getCasesInfo:()=>info,onEventsChanged:changed});
  const container={};const mounted=view.mount(container);
  assert.equal(view.filters,false);assert.equal(view.inspector,false);assert.equal(apps[0].container,container);
  const vnode=apps[0].options.render();assert.equal(vnode.type,component);assert.equal(vnode.props.case_id,42);assert.equal(vnode.props.onEventsChanged,changed);
  info={permission:{read_only:true}};assert.equal(apps[0].options.render().props.cases_info,info);
  mounted.destroy();assert.equal(apps[0].unmounted,true);
});
test('graph data is loaded by Flowintel and no request runs after leaving',async()=>{
  const h=harness();await h.mount();assert.equal(h.requests[0].url,'/case/42/get_timeline_graph');
  assert.equal(h.api.graph_events.value[0].id,1);assert.equal(h.emitted.length,0);
  h.unmount();await h.api.fetch_graph_data();assert.equal(h.requests.length,1);
});
test('a pending graph response is aborted and ignored after leaving',async()=>{
  let resolveJson,started;const ready=new Promise(resolve=>{started=resolve;});
  const h=harness(async()=>({status:200,json:()=>new Promise(resolve=>{resolveJson=resolve;started();})}));
  const pending=h.mount();await ready;h.unmount();resolveJson({events:[record(1)],links:[]});await pending;
  assert.equal(h.requests[0].options.signal.aborted,true);assert.equal(h.api.graph_events.value.length,0);
});
test('stale graph requests are ignored and graph load failures remain retryable',async()=>{
  let firstResolve,started,count=0;const ready=new Promise(resolve=>{started=resolve;});
  const h=harness(async()=>++count===1?{status:200,json:()=>new Promise(resolve=>{firstResolve=resolve;started();})}:response([record(2)]));
  const first=h.mount();await ready;await h.api.fetch_graph_data();firstResolve({events:[record(1)],links:[]});await first;
  assert.equal(h.api.graph_events.value[0].id,2);h.unmount();
  let attempts=0;const retry=harness(async()=>{if(++attempts===1)throw new Error('Network');return response();});
  await retry.mount();assert.match(retry.api.graph_load_error.value,/Unable to load/);await retry.api.fetch_graph_data();assert.equal(retry.api.graph_load_error.value,'');retry.unmount();
});
test('events created or deleted from the graph notify the shared viewer and are saved with the CSRF token',async()=>{
  const h=harness(async(url,options)=>options?.method==='POST'?{status:200}:response());await h.mount();
  await h.api.persist_node_create({promptData:async()=>({date_text:'2026-11-19 10:00',description:'New graph event',additional_note:''})});
  assert.deepEqual(h.emitted,['events-changed']);
  const write=h.requests.find(request=>request.url.endsWith('/create_timeline_event'));
  assert.equal(write.options.headers['X-CSRFToken'],'test-csrf');assert.equal(JSON.parse(write.options.body).description,'New graph event');
  await h.api.persist_delete({nodes:[{getData:()=>({event:record(1)})}],edges:[]});assert.equal(h.emitted.length,2);
  assert.ok(h.requests.some(request=>request.url==='/case/42/delete_timeline_event/1'));h.unmount();
});
