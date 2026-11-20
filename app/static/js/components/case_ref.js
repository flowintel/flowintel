/**
 * case_ref.js — a reference to a case (link), in three sizes.
 *
 *   <case_ref :item="{ id: 119, title: 'Phishing…', is_private: true }" mode="id"></case_ref>
 *
 *   mode  'id'      #119
 *         'simple'  #119 Phishing campaign…          (title cut with an ellipsis)
 *         'full'    #119 Phishing campaign… [status] 🔒 🛡   (status if given in item.status)
 *
 * The prop is "item", not "case": "case" is a JS keyword and breaks template expressions.
 * Styles: /static/css/components/case_ref.css
 */
export default {
    name: 'case_ref',
    delimiters: ['[[', ']]'],
    props: {
        item: { type: Object, required: true },        // at least { id }, title / flags if known
        mode: { type: String, default: 'simple' },     // 'id' | 'simple' | 'full'
        href: { type: String, default: '' },           // default: /case/<id>
    },
    computed: {
        url() { return this.href || `/case/${this.item.id}` },
        privileged() { return this.item.privileged_case ?? this.item.privileged },
        tooltip() { return `Case #${this.item.id}${this.item.title ? ': ' + this.item.title : ''}` },
    },
    template: /* html */ `
    <a :href="url" class="cr" :class="'cr--' + mode" :title="tooltip">
      <span class="cr-id">#[[ item.id ]]</span>
      <span v-if="mode !== 'id' && item.title" class="cr-title">[[ item.title ]]</span>
      <span v-if="mode === 'full' && item.status" :class="'cr-status text-bg-' + item.status.style">[[ item.status.name ]]</span>
      <i v-if="item.is_private" class="fa-solid fa-lock cr-flag" title="Private case"></i>
      <i v-if="privileged" class="fa-solid fa-user-shield cr-flag cr-priv" title="Privileged case"></i>
    </a>
    `,
}
