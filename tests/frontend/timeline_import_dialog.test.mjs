import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { Script, createContext } from 'node:vm';

const file = new URL('../../app/static/js/case/timeline_import_dialog.js', import.meta.url);
const source = await readFile(file, 'utf8');
const result = (items, has_next = false, total = items.length) => ({
  ok: true, json: async () => ({ items, has_next, total, total_pages: Math.ceil(total / 20) }),
});

function harness(fetch) {
  let mount, unmount, timer;
  const events = [], requests = [];
  const context = createContext({
    Vue: {
      ref: value => ({value}), computed: get => ({ get value() { return get(); } }),
      onMounted: fn => { mount = fn; }, onUnmounted: fn => { unmount = fn; },
    },
    URLSearchParams, AbortController,
    setTimeout: fn => { timer = fn; return 1; }, clearTimeout: () => { timer = undefined; },
    fetch: (url, options) => { requests.push({url, options}); return fetch(url, options); },
    display_toast: async () => {}, document: { getElementById: () => ({value: 'csrf'}) },
  });
  new Script(source.replace(/^import .*$/gm, '').replace('export default', 'globalThis.component =')).runInContext(context);
  const api = context.component.setup({case_id: 7}, {emit: event => events.push(event)});
  api.dialog.value = {open: false, showModal() { this.open = true; }};
  return {api, mount, unmount, events, requests, flushSearch: () => timer?.()};
}

test('dialog opens before the first response and ignores superseded searches', async () => {
  let resolveFirst;
  const h = harness(url => {
    if (new URL(url, 'http://local').searchParams.get('q') === 'final & value')
      return result([{id: 9, label: 'Match'}]);
    return new Promise(resolve => { resolveFirst = resolve; });
  });
  const first = h.mount();
  assert.equal(h.api.dialog.value.open, true);
  assert.equal(h.api.loading.value, true);
  h.api.search_items('f'); h.api.search_items('final & value');
  assert.equal(h.requests.length, 1);
  assert.equal(h.requests[0].options.signal.aborted, true);
  await h.flushSearch();
  resolveFirst(result([{id: 1}], true, 32)); await first;
  assert.equal(h.api.items.value[0].id, 9);
  assert.equal(h.api.total.value, 1);
  assert.equal(h.api.total_pages.value, 1);
  assert.equal(h.api.loading.value, false);
  h.api.search_items('pending'); h.unmount(); h.flushSearch();
  assert.equal(h.requests.length, 2);
});

test('selections survive pages, search, and source changes and submit only eligible IDs', async () => {
  const h = harness((url, options) => {
    if (options.method === 'POST') return {ok: true};
    const params = new URL(url, 'http://local').searchParams;
    if (params.get('q')) return result([]);
    if (params.get('source') === 'files') return result([{id: 1}]);
    if (params.get('source') === 'attributes') return result([{id: 1}]);
    if (params.get('page') === '2') return result([{id: 3}], false, 21);
    return result([{id: 1}, {id: 2, is_imported: true}], true, 21);
  });
  await h.mount(); h.api.toggle_page(true);
  await h.api.load_page(2); h.api.toggle_page(true);
  assert.equal(h.api.total.value, 21);
  assert.equal(h.api.total_pages.value, 2);
  h.api.search_items('unmatched'); await h.flushSearch();
  assert.equal(h.api.page.value, 1);
  assert.equal(h.api.total.value, 0);
  assert.equal(h.api.total_pages.value, 0);
  assert.equal(h.api.selection_count.value, 2);
  await h.api.change_source('attributes'); h.api.toggle_page(true);
  await h.api.change_source('files'); h.api.toggle_page(true);
  assert.equal(h.api.selection_count.value, 4);
  await h.api.perform_import();
  const posts = h.requests.filter(req => req.options.method === 'POST');
  assert.equal(posts[0].url, '/case/7/import_misp_to_timeline');
  assert.deepEqual(JSON.parse(posts[0].options.body), {object_ids: [1, 3], attribute_ids: [1]});
  assert.equal(posts[1].url, '/case/7/import_files_to_timeline');
  assert.deepEqual(JSON.parse(posts[1].options.body), {file_ids: [1]});
  assert.ok(posts.every(req => req.options.headers['X-CSRFToken'] === 'csrf'));
  assert.deepEqual(h.events, ['close', 'imported']);
});

test('failed reads can be retried and partial imports retain only the failed selection', async () => {
  let offline = true, failFiles = true;
  const h = harness((url, options) => {
    if (offline) throw new Error('offline');
    if (options.method !== 'POST') return result([{id: 5}]);
    if (url.endsWith('/import_files_to_timeline') && failFiles)
      return { ok: false, json: async () => ({message: 'File import failed'}) };
    return {ok: true};
  });
  await h.mount(); assert.equal(h.api.load_error.value, true);
  offline = false; await h.api.load_page(1);
  assert.equal(h.api.load_error.value, false);
  h.api.toggle_page(true);
  await h.api.change_source('files'); h.api.toggle_page(true);
  await h.api.perform_import();
  assert.deepEqual(h.events, ['imported']);
  assert.equal(h.api.selection_count.value, 1); assert.equal(h.api.save_error.value, 'File import failed');
  failFiles = false; await h.api.perform_import();
  assert.equal(h.requests.filter(req => req.url.endsWith('/import_misp_to_timeline')).length, 1);
  assert.deepEqual(h.events, ['imported', 'close', 'imported']);
});

test('bulk selection uses the active search and ignores a late response after changing sources', async () => {
  let resolveBulk;
  const h = harness(url => {
    const params = new URL(url, 'http://local').searchParams;
    if (params.has('ids_only')) {
      assert.equal(params.get('q'), 'example');
      return new Promise(resolve => { resolveBulk = ids => resolve({ok: true, json: async () => ({ids})}); });
    }
    return result([{id: 1}], true);
  });
  await h.mount(); h.api.search_items('example'); await h.flushSearch();
  const first = h.api.select_all_matches();
  resolveBulk([1, 3, 5]); await first;
  assert.equal(h.api.selection_count.value, 3);
  const stale = h.api.select_all_matches();
  await h.api.change_source('files');
  resolveBulk([7, 9]); await stale;
  assert.equal(h.api.selected.value.files.size, 0);
  assert.equal(h.api.selection_count.value, 3);
});
