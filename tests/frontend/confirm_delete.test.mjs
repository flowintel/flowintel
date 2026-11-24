import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {Script,createContext} from 'node:vm';
const source=await readFile(new URL('../../app/static/js/confirm.js',import.meta.url),'utf8');
function harness(){
  const elements=new Map();
  const get=id=>{if(!elements.has(id))elements.set(id,Object.assign(new EventTarget(),{style:{}}));return elements.get(id);};
  let instance;
  const context=createContext({document:{createElement:()=>({firstElementChild:{}}),body:{appendChild(){}},getElementById:get},bootstrap:{Modal:class{
    constructor(){instance=this;this.hides=0;}
    show(){}
    hide(){this.hides++;get('shared-confirm-delete-modal').dispatchEvent(new Event('hidden.bs.modal'));}
  }}});
  new Script(source.replace('export function confirmDelete','globalThis.confirmDelete = function confirmDelete')).runInContext(context);
  return {confirm:()=>context.confirmDelete(),shown:()=>get('shared-confirm-delete-modal').dispatchEvent(new Event('shown.bs.modal')),hidden:()=>get('shared-confirm-delete-modal').dispatchEvent(new Event('hidden.bs.modal')),click:()=>get('shared-confirm-delete-confirm').dispatchEvent(new Event('click')),hides:()=>instance.hides};
}
test('a fast confirmation waits for the modal to finish opening before hiding',async()=>{
  const h=harness(),pending=h.confirm();h.click();assert.equal(h.hides(),0);h.shown();assert.equal(await pending,true);assert.equal(h.hides(),1);
});
test('normal confirmation hides once and does not retain handlers on the next open',async()=>{
  const h=harness(),pending=h.confirm();h.shown();h.click();h.click();assert.equal(await pending,true);assert.equal(h.hides(),1);
  const again=h.confirm();h.shown();assert.equal(h.hides(),1);h.hidden();assert.equal(await again,false);
});
test('cancelling before a deferred confirmation does not leak a delete into the next dialog',async()=>{
  const h=harness(),pending=h.confirm();h.click();h.hidden();assert.equal(await pending,false);
  const again=h.confirm();h.shown();assert.equal(h.hides(),0);h.hidden();assert.equal(await again,false);
});
