import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Script, createContext } from 'node:vm';
import { setImmediate } from 'node:timers/promises';
const root = new URL('../../', import.meta.url);
const model = 'data:text/javascript;base64,' + Buffer.from(await readFile(new URL('app/assets/vendor/vitrine/flowtime.js', root))).toString('base64');
const helper = (await readFile(new URL('app/static/js/case/misp_timeline.js', root), 'utf8')).replace("'../vendor/vitrine/flowtime.js'", JSON.stringify(model));
const { fromMispObjects } = await import('data:text/javascript;base64,' + Buffer.from(helper).toString('base64'));
const preferencesSource = await readFile(new URL('app/static/js/case/flowtime_preferences.js', root), 'utf8');
const historySource = await readFile(new URL('app/static/js/case/case_history.js', root), 'utf8');
const object = extra => ({ object_id: 1, object_name: 'network-connection', object_uuid: 'template-uuid', object_creation_date: '2026-11-19 09:00', attributes: [], ...extra });
test('MISP history uses earliest valid first_seen and retains all attribute fields as text', () => {
  const input = object({ attributes: [{ first_seen: '2026-11-19 08:45' }, { first_seen: '2026-11-19 08:15', last_seen: '2026-11-19 08:50', value: '<b>literal text</b>', type: 'domain', comment: 'investigation', ids_flag: false }, { first_seen: 'invalid' }] });
  const { events, rejected } = fromMispObjects([input]);
  assert.equal(events[0].start, Date.UTC(2026, 10, 19, 8, 15)); assert.equal(rejected.length, 0);
  for (const value of ['<b>literal text</b>', 'domain', 'investigation', '2026-11-19 08:50', 'IDS: false']) assert.ok(events[0].description.includes(value));
  assert.equal(events[0].metadata['Object UUID'], 'template-uuid'); assert.equal(events[0].source, input);
});
test('MISP history falls back through creation dates and reports genuinely undated objects', () => {
  const { events, rejected } = fromMispObjects([object({ attributes: null }), object({ object_id: 2, object_creation_date: 'bad', creation_date: '2026-11-18' }), object({ object_id: 3, object_creation_date: '2026-02-30' })]);
  assert.equal(events.length, 2); assert.equal(events[1].start, Date.UTC(2026, 10, 18)); assert.equal(rejected.length, 1);
});
function historyHarness(canView = true) {
  let resolveObjects;
  const instances = [], unmounted = [], requests = [];
  const tabs = new Map(['history-case', 'history-misp', 'history-audit'].map(name => [name, new Set(name === 'history-case' ? ['active'] : [])]));
  const context = createContext({
    Vue: { ref: value => ({ value }), nextTick: async () => {}, onMounted() {}, onUnmounted: fn => unmounted.push(fn) },
    Flowtime: class {
      constructor(host, options) { this.view = options.view; this.events = options.events; this.destroyed = 0; instances.push(this); }
      destroy() { this.destroyed++; }
      setEvents(events) { this.events = events; }
    },
    fromMispObjects, AbortController, history_log: {}, url_set() {}, url_get() {}, window: {}, display_toast() {}, console,
    document: { getElementById: id => { const set = tabs.get(id.replace('tab-', '')); return { classList: { contains: name => set.has(name), add: name => set.add(name), remove: name => set.delete(name) } }; } },
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (url.endsWith('/get_case_misp_object')) return { ok: true, status: 200, json: () => new Promise(resolve => { resolveObjects = resolve; }) };
      return { status: 200, json: async () => ({ history: [], audit_logs: [] }) };
    },
  });
  new Script(preferencesSource.replace(/^export /gm, '') + '\n' + historySource.replace(/^import .*$/gm, '').replace('export default', 'globalThis.component =')).runInContext(context);
  const api = context.component.setup({ case_id: 42, can_view_history: canView }); api.misp_timeline_embed.value = new EventTarget();
  return { api, instances, requests, unmount: () => unmounted[0](), load: async objects => { await setImmediate(); resolveObjects({ 'misp-object': objects }); await setImmediate(); } };
}
test('opening MISP history before data arrives renders once loaded, and switching tabs destroys the viewer', async () => {
  const h = historyHarness(); await h.api.active_tab('history-misp'); assert.equal(h.instances.length, 0);
  await h.load([object()]); assert.equal(h.instances.length, 1);
  h.instances[0].view = 'feed'; await h.api.active_tab('history-case'); assert.equal(h.instances[0].destroyed, 1);
  await h.api.active_tab('history-misp'); assert.equal(h.instances[1].view, 'feed');
  h.unmount(); assert.equal(h.instances[1].destroyed, 1);
});
test('late MISP history responses do not create a viewer after unmount', async () => {
  const h = historyHarness(); await h.api.active_tab('history-misp'); h.unmount(); await h.load([object()]);
  assert.equal(h.instances.length, 0); assert.ok(h.requests.find(request => request.options?.signal).options.signal.aborted);
});
test('restricted history does not fetch data or mount a viewer', () => {
  const h = historyHarness(false); assert.equal(h.requests.length, 0); assert.equal(h.instances.length, 0); h.unmount();
});
