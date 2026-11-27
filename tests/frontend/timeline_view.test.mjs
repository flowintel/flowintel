import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Script, createContext } from 'node:vm';

const root = new URL('../../', import.meta.url);
const source = await readFile(new URL('app/static/js/case/timeline_view.js', root), 'utf8');
const preferencesSource = await readFile(new URL('app/static/js/case/flowtime_preferences.js', root), 'utf8');
const vendor = new URL('app/assets/vendor/vitrine/flowtime.js', root);
const modelURL = 'data:text/javascript;base64,' + Buffer.from(await readFile(vendor)).toString('base64');
const adapter = (await readFile(new URL('app/static/js/case/flowtime_adapter.js', root), 'utf8')).replace("'../vendor/vitrine/flowtime.js'", JSON.stringify(modelURL));
const { fromFlowintel } = await import('data:text/javascript;base64,' + Buffer.from(adapter).toString('base64'));
const record = (id = 1, extra = {}) => ({ id, date_parsed: '2026-11-19 14:30:00', date_text: '2026-11-19 14:30', description: 'Investigation event', additional_note: 'Evidence note', ...extra });
const response = events => ({ ok: true, status: 200, json: async () => ({ events }) });
function storage() {
  const data = new Map();
  return { getItem: key => data.get(key) ?? null, setItem: (key, value) => data.set(key, value) };
}
function fire(host, type, detail) {
  const event = new Event(type); event.detail = detail; host.dispatchEvent(event);
}
function harness({ fetch = async () => response([record()]), sessionStorage = storage(), localStorage = storage(), caseId = 42, casesInfo = {permission:{admin:true,read_only:false},present_in_case:true}, confirm = true, initialView = '' } = {}) {
  const mounted = [], unmounted = [], instances = [], requests = [], notifications = [], watchers = [], emitted = [];
  const host = new EventTarget();
  class Flowtime {
    constructor(container, options) {
      assert.equal(container, host);
      this.options = options; this.view = options.view; this.events = options.events;
      this.updates = []; this.filters = []; this.destroyed = 0;
      instances.push(this);
    }
    setEvents(events) { this.events = events; this.updates.push(events); }
    setFilter(filter) { this.filters.push(filter); }
    setView(view) { this.view = view; fire(host, 'flowtime:viewchange', { view }); }
    destroy() { this.destroyed++; }
  }
  const context = createContext({
    Vue: {
      ref: value => ({ value }), computed: callback => ({ get value() { return callback(); } }),
      watch: (get, callback) => watchers.push(callback), nextTick: async () => {}, onMounted: callback => mounted.push(callback), onUnmounted: callback => unmounted.push(callback),
    },
    TimelineImportDialog: {}, Flowtime, fromFlowintel, AbortController, sessionStorage, localStorage,
    createFlowtimeGraphView: host => ({id:'graph',label:'Graph',filters:false,inspector:false,mount(){},host}),
    fetch: (url, options) => { requests.push({ url, options }); return fetch(url, options); },
    display_toast: res => notifications.push(res), create_message: () => {},
    touchCaseLastModif: () => {}, confirmDelete: async () => confirm, open_timeline_date_picker: () => {},
    document: { getElementById: () => ({ value: 'test-csrf' }) },
    console: { error() {} },
  });
  // Run the real Vue setup without a browser; substitute only its imports and Vue lifecycle.
  new Script(preferencesSource.replace(/^export /gm, '') + '\n' + source.replace(/^import .*$/gm, '').replace('export default', 'globalThis.component ='), { filename: 'timeline_view.js' }).runInContext(context);
  const props = { case_id: caseId, cases_info: casesInfo, initial_view: initialView };
  const api = context.component.setup(props, {emit:(name,value)=>emitted.push({name,value})});
  api.timeline_embed.value = host;
  api.inspector_edit_dialog.value = {open:false,showModal(){this.open=true;},close(){this.open=false;}};
  return { api, host, instances, requests, notifications, emitted, setInitialView(view){props.initial_view=view;watchers.forEach(callback=>callback(view));}, mount: () => mounted[0](), unmount: () => unmounted[0](), sessionStorage, localStorage };
}

test('mount maps API records, preserves source records, and reports undated events', async () => {
  const events = [record(1), record(2, { misp_object_id: 7 }), record(3, { misp_object_id: -8 }), record(4, { file_id: 9 }), record(5, { date_parsed: null, date_text: 'unknown' })];
  const h = harness({ fetch: async () => response(events) }); await h.mount();
  assert.equal(h.requests[0].url, '/case/42/get_timeline_events');
  assert.deepEqual(h.instances[0].events.map(event => event.group), ['analysis', 'objects', 'attributes', 'files']);
  const groups = Array.from(h.instances[0].options.groups);
  assert.deepEqual(groups.map(group => group.id), h.instances[0].events.map(event => event.group));
  assert.deepEqual(groups.map(group => group.label), ['Analyst notes', 'MISP objects', 'MISP attributes', 'Files & evidence']);
  assert.equal(h.instances[0].events[0].source, events[0]);
  assert.equal(h.api.timeline_rejected_count.value, 1);
  assert.equal(h.instances[0].options.timeZone, 'UTC');
});
test('Flowtime toolbar actions open Flowintel forms and import modal without writing data', async () => {
  const h = harness();
  await h.mount();
  const actions = h.instances[0].options.actions;
  assert.deepEqual(Array.from(actions, action => action.id), ['add-event','import-data']);
  assert.ok(actions.every(action => action.visible()));
  h.api.new_description.value = 'Keep this draft';
  await actions[0].onClick(); assert.equal(h.api.show_add_form.value,true);
  await actions[0].onClick(); assert.equal(h.api.show_add_form.value,false);
  assert.equal(h.api.new_description.value,'Keep this draft');
  await actions[1].onClick();
  assert.equal(h.api.show_import_modal.value,true);
  assert.equal(h.requests.length, 1);
  await h.api.fetch_timeline_events(); assert.equal(h.instances.length,1);
  await actions[0].onClick(); assert.equal(h.api.show_add_form.value,true);
});
test('toolbar action callbacks recheck current case permissions before opening forms or fetching imports', async () => {
  const casesInfo={permission:{admin:true,read_only:false},present_in_case:true};
  const h=harness({casesInfo}); await h.mount();
  const actions=h.instances[0].options.actions;
  casesInfo.permission.read_only=true;
  assert.ok(actions.every(action => !action.visible()));
  for (const action of actions) await action.onClick();
  assert.equal(h.api.show_add_form.value,false); assert.equal(h.api.show_import_modal.value,false);
  assert.equal(h.requests.length,1);
});
test('feed preference survives refresh and remount, scoped to the case', async () => {
  const shared = storage(), h = harness({ sessionStorage: shared }); await h.mount();
  h.instances[0].setView('feed'); await h.api.fetch_timeline_events();
  assert.equal(h.instances.length, 1); assert.equal(h.instances[0].view, 'feed'); h.unmount();
  const remount = harness({ sessionStorage: shared }); await remount.mount(); assert.equal(remount.instances[0].view, 'feed');
  const otherCase = harness({ sessionStorage: shared, caseId: 43 }); await otherCase.mount(); assert.equal(otherCase.instances[0].view, 'timeline');
});
test('combined timeline preference survives refresh and remount, scoped to the case', async () => {
  const shared = storage(), h = harness({ sessionStorage: shared }); await h.mount();
  h.instances[0].setView('combined'); await h.api.fetch_timeline_events();
  assert.equal(h.instances.length, 1); assert.equal(h.instances[0].view, 'combined'); h.unmount();
  const remount = harness({ sessionStorage: shared }); await remount.mount();
  assert.equal(remount.instances[0].view, 'combined');
  const otherCase = harness({ sessionStorage: shared, caseId: 43 }); await otherCase.mount();
  assert.equal(otherCase.instances[0].view, 'timeline');
});
test('unknown stored views fall back to the source-lane timeline', async () => {
  const shared = storage(); shared.setItem('flowintel:case:42:timeline-view', 'unknown');
  const h = harness({ sessionStorage: shared }); await h.mount();
  assert.equal(h.instances[0].view, 'timeline');
});
test('search and source filters are reapplied after a data refresh', async () => {
  const h = harness(); await h.mount();
  fire(h.host, 'flowtime:filterchange', { query: 'evidence', groups: ['files'] });
  await h.api.fetch_timeline_events();
  assert.equal(h.instances[0].filters[0].query, 'evidence');
  assert.deepEqual(Array.from(h.instances[0].filters[0].groups), ['files']);
});
test('empty cases still mount the switchable viewer', async () => {
  const h = harness({ fetch: async () => response([]) }); await h.mount();
  assert.equal(h.instances[0].events.length, 0); assert.equal(h.api.timeline_rejected_count.value, 0);
});
test('blocked browser storage does not prevent mounting or switching views', async () => {
  const h = harness({ sessionStorage: { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('blocked'); } } });
  await h.mount(); assert.doesNotThrow(() => h.instances[0].setView('feed')); assert.equal(h.instances[0].view, 'feed');
});
test('HTTP and network failures expose a retryable error, then recover', async () => {
  let count = 0;
  const h = harness({ fetch: async () => {
    count++; if (count === 1) return { ok: false, status: 403 }; if (count === 2) throw new Error('offline'); return response([record()]);
  } });
  await h.mount(); assert.match(h.api.timeline_load_error.value, /Unable to load/); assert.equal(h.notifications.length, 1);
  await h.api.fetch_timeline_events(); assert.match(h.api.timeline_load_error.value, /Unable to load/);
  await h.api.fetch_timeline_events(); assert.equal(h.api.timeline_load_error.value, ''); assert.equal(h.instances.length, 1);
});
test('unmount destroys the viewer and removes its storage listener', async () => {
  const h = harness(); await h.mount(); const instance = h.instances[0]; h.unmount();
  assert.equal(instance.destroyed, 1);
  fire(h.host, 'flowtime:viewchange', { view: 'feed' });
  assert.equal(h.sessionStorage.getItem('flowintel:case:42:timeline-view'), null);
});
test('late data cannot recreate a viewer after unmount', async () => {
  let resolveJSON, markStarted;
  const started = new Promise(resolve => { markStarted = resolve; });
  const h = harness({ fetch: async () => ({ ok: true, status: 200, json: () => new Promise(resolve => { resolveJSON = resolve; markStarted(); }) }) });
  const pending = h.mount(); await started; h.unmount(); resolveJSON({ events: [record()] }); await pending;
  assert.equal(h.instances.length, 0); assert.equal(h.requests[0].options.signal.aborted, true);
});
test('a stale response cannot replace a newer refresh', async () => {
  let firstResolve, markStarted, count = 0;
  const started = new Promise(resolve => { markStarted = resolve; });
  const h = harness({ fetch: async () => ++count === 1 ? { ok: true, json: () => new Promise(resolve => { firstResolve = resolve; markStarted(); }) } : response([record(2)]) });
  const first = h.mount(); await started; await h.api.fetch_timeline_events(); firstResolve({ events: [record(1)] }); await first;
  assert.equal(h.instances.length, 1); assert.equal(h.instances[0].events[0].id, 2);
});
test('existing create, edit, delete and import actions refresh the same viewer', async () => {
  const h = harness(); await h.mount();
  h.api.new_date_text.value = '2026-11-19 14:30'; h.api.new_description.value = 'New finding'; await h.api.add_event();
  await h.instances[0].options.onEdit(h.instances[0].events[0]); h.api.edit_description.value = 'Edited finding'; await h.api.save_edit(1);
  await h.api.delete_event(1);
  await h.api.on_timeline_import();
  assert.equal(h.instances.length, 1); assert.equal(h.instances[0].updates.length, 4);
  const writes = h.requests.filter(request => request.options?.method === 'POST');
  assert.equal(writes.length, 2);
  assert.equal(writes[0].options.headers['X-CSRFToken'], 'test-csrf');
  assert.ok(h.requests.some(request => request.url.endsWith('/delete_timeline_event/1')));
});

test('inspector edit opens a populated dialog and saves through the existing CSRF-protected endpoint', async () => {
  const h=harness();await h.mount();
  await h.instances[0].options.onEdit(h.instances[0].events[0]);
  assert.equal(h.api.inspector_edit_dialog.value.open,true);
  assert.equal(h.api.edit_description.value,'Investigation event');assert.equal(h.api.edit_additional_note.value,'Evidence note');
  h.api.edit_description.value='Updated from inspector';await h.api.save_edit(h.api.editing_event_id.value);
  assert.equal(h.api.inspector_edit_dialog.value.open,false);assert.equal(h.api.editing_event_id.value,null);
  const request=h.requests.find(request=>request.url.endsWith('/edit_timeline_event/1'));
  assert.equal(request.options.headers['X-CSRFToken'],'test-csrf');assert.equal(JSON.parse(request.options.body).description,'Updated from inspector');
  assert.equal(h.instances[0].updates.length,1);
});
test('failed inspector saves preserve the dialog and draft for retry', async () => {
  const h=harness({fetch:async url=>url.includes('/edit_timeline_event/')?{status:403,ok:false}:response([record()])});await h.mount();
  await h.instances[0].options.onEdit(h.instances[0].events[0]);h.api.edit_description.value='Retained draft';await h.api.save_edit(1);
  assert.equal(h.api.inspector_edit_dialog.value.open,true);assert.equal(h.api.edit_description.value,'Retained draft');
  assert.match(h.api.edit_error.value,/Unable to save/);assert.equal(h.api.edit_saving.value,false);
});
test('inspector delete uses the selected source ID and respects cancelled confirmation', async () => {
  const h=harness();await h.mount();await h.instances[0].options.onDelete(h.instances[0].events[0]);
  assert.ok(h.requests.some(request=>request.url.endsWith('/delete_timeline_event/1')));assert.equal(h.instances[0].updates.length,1);
  const cancelled=harness({confirm:false});await cancelled.mount();await cancelled.instances[0].options.onDelete(cancelled.instances[0].events[0]);
  assert.equal(cancelled.requests.length,1);
});
test('read-only users and nonmembers have no inspector mutation actions', async () => {
  for(const casesInfo of [{permission:{read_only:true,admin:false},present_in_case:true},{permission:{read_only:false,admin:false},present_in_case:false}]){
    const h=harness({casesInfo});await h.mount();assert.equal(h.instances[0].options.onEdit,undefined);assert.equal(h.instances[0].options.onDelete,undefined);assert.ok(h.instances[0].options.actions.every(action=>!action.visible()));
  }
});
test('date-range filters are reapplied after event writes together with search and source filters', async () => {
  const h=harness();await h.mount();
  fire(h.host,'flowtime:filterchange',{query:'evidence',groups:['files'],dateRange:{start:100,end:200}});
  await h.api.fetch_timeline_events();const filter=h.instances[0].filters[0];assert.equal(filter.dateRange.start,100);assert.equal(filter.dateRange.end,200);
});

test('Graph is registered as a host-owned custom view and graph event writes refresh the shared viewer', async () => {
  const h=harness();await h.mount();const graph=h.instances[0].options.customViews[0];
  assert.equal(graph.id,'graph');assert.equal(graph.filters,false);assert.equal(graph.inspector,false);
  assert.equal(graph.host.caseId,42);assert.equal(graph.host.getCasesInfo().permission.admin,true);
  assert.ok(h.requests.every(request=>!request.url.endsWith('/get_timeline_graph')));
  await graph.host.onEventsChanged();assert.equal(h.instances.length,1);assert.equal(h.instances[0].updates.length,1);
});
test('Graph preference restores per case, URL view requests take precedence, and later requests switch the mounted viewer', async () => {
  const shared=storage();let h=harness({sessionStorage:shared});await h.mount();h.instances[0].setView('graph');
  assert.equal(h.emitted.at(-1).value,'graph');h.unmount();
  h=harness({sessionStorage:shared});await h.mount();assert.equal(h.instances[0].view,'graph');
  const explicit=harness({sessionStorage:shared,initialView:'combined'});await explicit.mount();assert.equal(explicit.instances[0].view,'combined');
  explicit.setInitialView('graph');assert.equal(explicit.instances[0].view,'graph');
  explicit.setInitialView('unknown');assert.equal(explicit.instances[0].view,'graph');
  const other=harness({sessionStorage:shared,caseId:43});await other.mount();assert.equal(other.instances[0].view,'timeline');
});
test('legacy Graph URLs route to the integrated view without referring to removed subtab buttons', async () => {
  const page=await readFile(new URL('app/templates/case/case_view.html',root),'utf8');
  const start=page.indexOf('async function active_subtab_timeline(');
  const end=page.indexOf('async function active_subtab_misp(',start);
  const changes=[],mode={value:''};
  const context=createContext({timeline_view_mode:mode,url_set:(...args)=>changes.push(args),nextTick:async()=>{}});
  new Script(page.slice(start,end)).runInContext(context);
  await context.active_subtab_timeline('timeline-graph');assert.equal(mode.value,'graph');assert.deepEqual(Array.from(changes.at(-1)),['timeline','graph','timeline']);
  await context.active_subtab_timeline('timeline-view');assert.equal(mode.value,'timeline');
  await context.active_subtab_timeline('feed');assert.equal(mode.value,'feed');
  await context.active_subtab_timeline('invalid');assert.equal(mode.value,'feed');
  assert.ok(!page.includes('id="subtab-timeline-graph"'));
});

test('text size preference is restored and saved across case timeline mounts', async () => {
  const localStorage = storage();
  localStorage.setItem('flowintel:flowtime:text-scale', '1.25');
  const h = harness({localStorage}); await h.mount();
  assert.equal(h.instances[0].options.textScale, 1.25);
  fire(h.host, 'flowtime:textscalechange', {textScale: 0.5});
  assert.equal(localStorage.getItem('flowintel:flowtime:text-scale'), '0.5');
  await h.api.fetch_timeline_events();
  assert.equal(h.instances.length, 1);
  h.unmount();
  fire(h.host, 'flowtime:textscalechange', {textScale: 0.8});
  assert.equal(localStorage.getItem('flowintel:flowtime:text-scale'), '0.5');
  const next = harness({localStorage}); await next.mount();
  assert.equal(next.instances[0].options.textScale, 0.5); next.unmount();
});
test('invalid or blocked text size storage leaves the viewer usable', async () => {
  for (const value of ['garbage', '2', '0', '0.49', 'Infinity']) {
    const localStorage = storage(); localStorage.setItem('flowintel:flowtime:text-scale', value);
    const h = harness({localStorage}); await h.mount();
    assert.equal(h.instances[0].options.textScale, 1); h.unmount();
  }
  const h = harness({localStorage: {getItem(){throw new Error('blocked')},setItem(){throw new Error('blocked')}}});
  await h.mount(); assert.equal(h.instances[0].options.textScale, 1);
  assert.doesNotThrow(() => fire(h.host, 'flowtime:textscalechange', {textScale: 0.5})); h.unmount();
});
