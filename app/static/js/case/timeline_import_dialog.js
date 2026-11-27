import { display_toast } from '../toaster.js'

const { ref, computed, onMounted, onUnmounted } = Vue

const sources = {
    objects: { label: 'MISP objects', placeholder: 'Search object names or attribute values' },
    attributes: { label: 'Standalone attributes', placeholder: 'Search values, types, or relations' },
    files: { label: 'Files', placeholder: 'Search filenames, types, or task names' }
}

export default {
    delimiters: ['[[', ']]'],
    props: { case_id: Number },
    emits: ['close', 'imported'],
    setup(props, { emit }) {
        const dialog = ref(null)
        const source = ref('objects')
        const search = ref('')
        const page = ref(1)
        const items = ref([])
        const total = ref(null)
        const total_pages = ref(null)
        const has_next = ref(false)
        const loading = ref(true)
        const load_error = ref(false)
        const selecting_all = ref(false)
        const saving = ref(false)
        const save_error = ref('')
        const selected = ref({ objects: new Set(), attributes: new Set(), files: new Set() })
        const selection_count = computed(() => Object.values(selected.value).reduce((sum, ids) => sum + ids.size, 0))
        const available = computed(() => items.value.filter(item => !item.is_imported))
        const page_selected = computed(() => available.value.length > 0 &&
            available.value.every(item => selected.value[source.value].has(item.id)))
        const base = '/case/' + props.case_id + '/'
        let timer
        let request
        let unmounted = false

        function reset_results() {
            clearTimeout(timer)
            request?.abort()
            selecting_all.value = false
            loading.value = true
            load_error.value = false
            items.value = []
            total.value = null
            total_pages.value = null
            has_next.value = false
        }

        async function load_page(number) {
            if (unmounted) return
            reset_results()
            page.value = number
            const controller = new AbortController()
            request = controller
            const params = new URLSearchParams({ source: source.value, q: search.value.trim(), page: number })
            try {
                const response = await fetch(base + 'timeline_import_candidates?' + params, { signal: controller.signal })
                if (!response.ok) throw new Error()
                const data = await response.json()
                if (controller.signal.aborted) return
                if (data.total_pages > 0 && number > data.total_pages) return load_page(data.total_pages)
                if (data.total === 0) page.value = 1
                items.value = data.items
                total.value = data.total
                total_pages.value = data.total_pages
                has_next.value = data.has_next
                for (const item of data.items) {
                    if (item.is_imported) selected.value[source.value].delete(item.id)
                }
            } catch {
                if (!controller.signal.aborted) load_error.value = true
            } finally {
                if (!controller.signal.aborted) loading.value = false
            }
        }

        function change_source(value) {
            if (source.value === value) return
            source.value = value
            search.value = ''
            return load_page(1)
        }

        function search_items(value) {
            search.value = value
            reset_results()
            page.value = 1
            timer = setTimeout(() => load_page(1), 200)
        }

        function toggle_page(checked) {
            const ids = selected.value[source.value]
            for (const item of available.value) {
                if (checked) ids.add(item.id)
                else ids.delete(item.id)
            }
        }

        async function select_all_matches() {
            if (selecting_all.value || saving.value) return
            selecting_all.value = true
            save_error.value = ''
            const signal = request.signal
            const params = new URLSearchParams({ source: source.value, q: search.value.trim(), ids_only: 1 })
            try {
                const response = await fetch(base + 'timeline_import_candidates?' + params, { signal })
                if (!response.ok) throw new Error()
                const { ids } = await response.json()
                if (!signal.aborted) {
                    for (const id of ids) selected.value[source.value].add(id)
                }
            } catch {
                if (!signal.aborted) save_error.value = 'Couldn’t select all matches. Please try again.'
            } finally {
                if (!signal.aborted) selecting_all.value = false
            }
        }

        async function post_import(path, payload) {
            const response = await fetch(base + path, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById('csrf_token').value },
                body: JSON.stringify(payload)
            })
            if (!response.ok) {
                const data = await response.json().catch(() => ({}))
                throw new Error(data.message || 'Import failed. Please try again.')
            }
            return response
        }

        async function perform_import() {
            if (saving.value || selecting_all.value || !selection_count.value) return
            saving.value = true
            save_error.value = ''
            const { objects, attributes, files } = selected.value
            const completed = []
            try {
                if (objects.size || attributes.size) {
                    completed.push(await post_import('import_misp_to_timeline', {
                        object_ids: [...objects], attribute_ids: [...attributes]
                    }))
                    objects.clear()
                    attributes.clear()
                }
                if (files.size) {
                    completed.push(await post_import('import_files_to_timeline', { file_ids: [...files] }))
                    files.clear()
                }
                emit('close')
            } catch (error) {
                save_error.value = error.message || 'Import failed. Please try again.'
                await load_page(page.value)
            } finally {
                if (completed.length) emit('imported')
                saving.value = false
            }
            for (const response of completed) await display_toast(response)
        }

        onMounted(() => {
            dialog.value.showModal()
            return load_page(1)
        })
        onUnmounted(() => {
            unmounted = true
            clearTimeout(timer)
            request?.abort()
        })

        return {
            dialog, sources, source, search, page, items, total, total_pages, has_next, loading, load_error, saving, save_error,
            selected, selection_count, available, page_selected, change_source, search_items,
            load_page, toggle_page, selecting_all, select_all_matches, perform_import
        }
    },
    template: `
        <dialog ref="dialog" class="timeline-import-dialog" aria-labelledby="timeline-import-title"
                @cancel.prevent="!saving && $emit('close')">
            <div class="timeline-import-content">
                <header class="d-flex justify-content-between align-items-center gap-3">
                    <h5 class="mb-0" id="timeline-import-title">Import data to timeline</h5>
                    <button type="button" class="btn-close" aria-label="Close import" :disabled="saving" @click="$emit('close')"></button>
                </header>
                <div class="d-flex align-items-center flex-wrap gap-2">
                    <div class="d-flex flex-wrap gap-1" role="group" aria-label="Import source">
                        <button v-for="(option, key) in sources" :key="key" type="button" class="btn btn-sm"
                                :class="source === key ? 'btn-primary' : 'btn-outline-secondary'"
                                :aria-pressed="source === key" :disabled="saving" @click="change_source(key)">[[ option.label ]]</button>
                    </div>
                    <span class="small text-body-secondary ms-auto" role="status">
                        <template v-if="total != null">[[ total.toLocaleString() ]] [[ total === 1 ? 'result' : 'results' ]]</template>
                    </span>
                </div>
                <input type="search" autofocus class="form-control" :aria-label="'Search ' + sources[source].label"
                       :placeholder="sources[source].placeholder" :value="search" :disabled="saving"
                       @input="search_items($event.target.value)">
                <div class="timeline-import-results border rounded" :aria-busy="loading">
                    <p v-if="loading" class="text-body-secondary m-3" role="status">
                        <span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span> Loading results…
                    </p>
                    <div v-else-if="load_error" class="m-3" role="alert">
                        Couldn’t load results. <button type="button" class="btn btn-link btn-sm" @click="load_page(page)">Retry</button>
                    </div>
                    <p v-else-if="!items.length" class="text-body-secondary m-3" role="status">
                        [[ search ? 'No matches for this search.' : 'No ' + sources[source].label.toLowerCase() + ' on this page.' ]]
                    </p>
                    <template v-else>
                        <div class="timeline-import-select-page d-flex flex-wrap align-items-center gap-2 px-3 py-2 border-bottom small">
                            <label class="d-flex align-items-center gap-2 me-auto">
                                <input type="checkbox" class="form-check-input mt-0" :checked="page_selected"
                                       :disabled="saving || selecting_all || !available.length" @change="toggle_page($event.target.checked)">
                                Select this page
                            </label>
                            <button v-if="has_next || page > 1" type="button" class="btn btn-link btn-sm p-0"
                                    :disabled="saving || selecting_all" @click="select_all_matches">
                                [[ selecting_all ? 'Selecting…' : 'Select all matches' ]]
                            </button>
                            <button v-if="selected[source].size" type="button" class="btn btn-link btn-sm p-0"
                                    :aria-label="'Clear selected ' + sources[source].label" :disabled="saving || selecting_all"
                                    @click="selected[source].clear()">Clear</button>
                        </div>
                        <label v-for="item in items" :key="item.id" class="d-flex gap-2 align-items-center border-bottom px-3 py-2">
                            <input type="checkbox" class="form-check-input mt-0 flex-shrink-0" :value="item.id"
                                   v-model="selected[source]" :disabled="saving || selecting_all || item.is_imported">
                            <span class="text-truncate flex-grow-1" :title="[item.label, item.detail].filter(Boolean).join(' · ')">
                                <span class="fw-semibold">[[ item.label ]]</span>
                                <small v-if="source === 'objects'" class="text-body-secondary ms-1">#[[ item.id ]]</small>
                                <small v-if="item.detail" class="d-block text-truncate text-body-secondary">[[ item.detail ]]</small>
                            </span>
                            <span v-if="item.is_imported" class="small text-body-secondary">Imported</span>
                        </label>
                    </template>
                </div>
                <nav v-if="total_pages != null || page > 1" class="d-flex align-items-center justify-content-between" aria-label="Import result pages">
                    <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="page === 1 || loading || saving"
                            @click="load_page(page - 1)">Previous</button>
                    <span class="small text-body-secondary" role="status">
                        <template v-if="total_pages">Page [[ page.toLocaleString() ]] of [[ total_pages.toLocaleString() ]]</template>
                        <template v-else-if="total_pages === 0">0 pages</template>
                    </span>
                    <button type="button" class="btn btn-outline-secondary btn-sm" :disabled="!has_next || loading || saving"
                            @click="load_page(page + 1)">Next</button>
                </nav>
                <p v-if="save_error" class="alert alert-danger mb-0" role="alert">[[ save_error ]]</p>
                <footer class="d-flex justify-content-end gap-2">
                    <button type="button" class="btn btn-outline-secondary" :disabled="saving" @click="$emit('close')">Cancel</button>
                    <button type="button" class="btn btn-primary" :disabled="!selection_count || saving || selecting_all" @click="perform_import">
                        [[ saving ? 'Importing…' : 'Import selected (' + selection_count + ')' ]]
                    </button>
                </footer>
            </div>
        </dialog>
    `
}
