// @variable autocomplete suggestions for CodeMirror 6 editors
// Loaded as a plain <script> tag, registers on window.FlowintelVarComplete
// Usage: add FlowintelVarComplete.extension() to your EditorView extensions array
(function () {
    'use strict'

    // ── Suggestion data ───────────────────────────────────────────────

    const ROOT_ITEMS = [
        { label: '@case.',  insert: '@case.',  info: 'Reference a case property' },
        { label: '@task.',  insert: '@task.',  info: 'Reference a task property' },
        { label: '@this.',  insert: '@this.',  info: 'Current case / task' },
        { label: '@now',    insert: '@now',    info: 'Current date & time' },
        { label: '@today',  insert: '@today',  info: 'Current date' },
    ]

    const THIS_ITEMS = [
        { label: 'case.',   insert: '@this.case.',   info: 'Current case' },
        { label: 'task.',   insert: '@this.task.',   info: 'Current task' },
    ]

    // Case-specific properties (from note_variables.py _resolve_case_property)
    const CASE_PROPERTY_ITEMS = [
        { label: 'title',           insert: 'title',           info: 'Case title' },
        { label: 'description',     insert: 'description',     info: 'Case description' },
        { label: 'id',              insert: 'id',              info: 'Case ID' },
        { label: 'uuid',            insert: 'uuid',            info: 'Case UUID' },
        { label: 'status',          insert: 'status',          info: 'Status name' },
        { label: 'completed',       insert: 'completed',       info: 'Yes / No' },
        { label: 'creation_date',   insert: 'creation_date',   info: 'Creation date' },
        { label: 'deadline',        insert: 'deadline',        info: 'Deadline' },
        { label: 'finish_date',     insert: 'finish_date',     info: 'Finish date' },
        { label: 'last_modif',      insert: 'last_modif',      info: 'Last modified' },
        { label: 'nb_tasks',        insert: 'nb_tasks',        info: 'Number of tasks' },
        { label: 'time_required',   insert: 'time_required',   info: 'Time required' },
        { label: 'ticket_id',       insert: 'ticket_id',       info: 'External ticket ID' },
        { label: 'is_private',      insert: 'is_private',      info: 'Yes / No' },
        { label: 'recurring_type',  insert: 'recurring_type',  info: 'Recurring type' },
        { label: 'recurring_date',  insert: 'recurring_date',  info: 'Recurring date' },
        { label: 'notes',           insert: 'notes',           info: 'Case notes (raw)' },
        { label: 'link',            insert: 'link',            info: 'URL to case' },
        { label: 'owner_org',       insert: 'owner_org',       info: 'Owner organization' },
        { label: 'tags',            insert: 'tags',            info: 'Tags (comma-sep)' },
        { label: 'clusters',        insert: 'clusters',        info: 'Galaxy clusters' },
        { label: 'custom_tags',     insert: 'custom_tags',     info: 'Custom tags' },
        { label: 'orgs',            insert: 'orgs',            info: 'Organizations in case' },
        { label: 'tasks.',          insert: 'tasks.',          info: 'Tasks by position (N)' },
        { label: 'misp_objects',    insert: 'misp_objects',    info: 'MISP objects list' },
        { label: 'misp_objects.',   insert: 'misp_objects.',   info: 'MISP object by position' },
    ]

    // Task-specific properties (from note_variables.py _resolve_task_property)
    const TASK_PROPERTY_ITEMS = [
        { label: 'title',           insert: 'title',           info: 'Task title' },
        { label: 'description',     insert: 'description',     info: 'Task description' },
        { label: 'id',              insert: 'id',              info: 'Task ID' },
        { label: 'uuid',            insert: 'uuid',            info: 'Task UUID' },
        { label: 'status',          insert: 'status',          info: 'Status name' },
        { label: 'completed',       insert: 'completed',       info: 'Yes / No' },
        { label: 'creation_date',   insert: 'creation_date',   info: 'Creation date' },
        { label: 'deadline',        insert: 'deadline',        info: 'Deadline' },
        { label: 'finish_date',     insert: 'finish_date',     info: 'Finish date' },
        { label: 'last_modif',      insert: 'last_modif',      info: 'Last modified' },
        { label: 'case_id',         insert: 'case_id',         info: 'Parent case ID' },
        { label: 'case_title',      insert: 'case_title',      info: 'Parent case title' },
        { label: 'nb_notes',        insert: 'nb_notes',        info: 'Number of notes' },
        { label: 'time_required',   insert: 'time_required',   info: 'Time required' },
        { label: 'link',            insert: 'link',            info: 'URL to task' },
        { label: 'assigned_users',  insert: 'assigned_users',  info: 'Assigned users' },
        { label: 'tags',            insert: 'tags',            info: 'Tags (comma-sep)' },
        { label: 'clusters',        insert: 'clusters',        info: 'Galaxy clusters' },
        { label: 'custom_tags',     insert: 'custom_tags',     info: 'Custom tags' },
        { label: 'subtasks',        insert: 'subtasks',        info: 'Subtask count' },
        { label: 'subtasks.',       insert: 'subtasks.',       info: 'Subtask by position (N)' },
        { label: 'notes',           insert: 'notes',           info: 'Note count' },
        { label: 'notes.',          insert: 'notes.',          info: 'Note by position (N)' },
    ]

    // Sub-properties shown after @...tasks.<n>.
    const TASK_SUB_ITEMS = TASK_PROPERTY_ITEMS

    // Sub-properties for subtasks: @...subtasks.<n>.<prop>
    const SUBTASK_PROPERTY_ITEMS = [
        { label: 'id',          insert: 'id',          info: 'Subtask ID' },
        { label: 'description', insert: 'description', info: 'Subtask description' },
        { label: 'completed',   insert: 'completed',   info: 'Yes / No' },
    ]

    // Sub-properties for notes: @...notes.<n>.<prop>
    const NOTE_PROPERTY_ITEMS = [
        { label: 'id',   insert: 'id',   info: 'Note ID' },
        { label: 'uuid', insert: 'uuid', info: 'Note UUID' },
        { label: 'note', insert: 'note', info: 'Note content' },
    ]

    // Sub-properties for misp_objects: @...misp_objects.<n>.<prop>
    const MISP_OBJECT_PROPERTY_ITEMS = [
        { label: 'name',          insert: 'name',          info: 'Object name' },
        { label: 'id',            insert: 'id',            info: 'Object ID' },
        { label: 'template_uuid', insert: 'template_uuid', info: 'Template UUID' },
        { label: 'creation_date', insert: 'creation_date', info: 'Creation date' },
        { label: 'last_modif',    insert: 'last_modif',    info: 'Last modified' },
        { label: 'attributes',    insert: 'attributes',    info: 'All attributes formatted' },
        { label: 'attributes.',   insert: 'attributes.',   info: 'Attribute by position' },
    ]

    // Sub-properties for attribute: @...attributes.<n>.<prop>
    const ATTRIBUTE_PROPERTY_ITEMS = [
        { label: 'value',           insert: 'value',           info: 'Attribute value' },
        { label: 'type',            insert: 'type',            info: 'Attribute type' },
        { label: 'object_relation', insert: 'object_relation', info: 'Object relation' },
        { label: 'comment',         insert: 'comment',         info: 'Comment' },
        { label: 'ids_flag',        insert: 'ids_flag',        info: 'IDS flag (Yes/No)' },
        { label: 'first_seen',      insert: 'first_seen',      info: 'First seen date' },
        { label: 'last_seen',       insert: 'last_seen',       info: 'Last seen date' },
        { label: 'id',              insert: 'id',              info: 'Attribute ID' },
    ]

    // All leaf-level property item lists for doPick matching
    const ALL_PROPERTY_LISTS = [
        CASE_PROPERTY_ITEMS, TASK_PROPERTY_ITEMS,
        SUBTASK_PROPERTY_ITEMS, NOTE_PROPERTY_ITEMS,
        MISP_OBJECT_PROPERTY_ITEMS, ATTRIBUTE_PROPERTY_ITEMS,
    ]

    // ── Token detection ───────────────────────────────────────────────

    function getTokenBefore(docText, pos) {
        const before = docText.slice(0, pos)
        const m = before.match(/@[\w.]*$/)
        return m ? { text: m[0], from: pos - m[0].length } : null
    }

    // ── Shared state ──────────────────────────────────────────────────

    let _dropdown = null
    let _activeView = null    // the CM6 EditorView that owns the current dropdown
    let _selectedIdx = 0
    let _items = []
    let _suppressUntil = 0

    // ── Pick logic (always re-reads fresh state) ──────────────────────

    function isLeafProperty(picked) {
        return ALL_PROPERTY_LISTS.some(list => list.some(p => p === picked))
    }

    function doPick(picked) {
        if (!_activeView) return
        const view = _activeView

        // Close dropdown FIRST to prevent re-entry
        closeDropdownFull()
        _suppressUntil = Date.now() + 150

        // Re-read the current editor state to get fresh positions
        const state = view.state
        const pos = state.selection.main.head
        const docText = state.doc.toString()
        const tok = getTokenBefore(docText, pos)

        if (!tok) return

        // Compute the final text to insert
        let insertText = picked.insert

        // For leaf properties, prepend the existing prefix (everything up to last dot)
        if (isLeafProperty(picked)) {
            const prefixMatch = tok.text.match(/^(.*\.)/)
            if (prefixMatch) {
                insertText = prefixMatch[1] + picked.insert
            }
        }

        view.dispatch({
            changes: { from: tok.from, to: pos, insert: insertText }
        })
        view.focus()
    }

    // ── Dropdown UI ───────────────────────────────────────────────────

    function closeDropdown() {
        if (_dropdown && _dropdown._cleanup) _dropdown._cleanup()
        if (_dropdown && _dropdown.parentElement) _dropdown.remove()
        _dropdown = null
        _items = []
        _selectedIdx = 0
    }

    function closeDropdownFull() {
        closeDropdown()
    }

    function createDropdown(items, rect) {
        closeDropdown()

        _items = items
        _selectedIdx = 0

        const el = document.createElement('div')
        el.className = 'var-suggest-dropdown'
        Object.assign(el.style, {
            position: 'fixed',
            zIndex: '10000',
            minWidth: '180px',
            maxHeight: '220px',
            overflowY: 'auto',
            background: 'var(--bs-body-bg, #fff)',
            color: 'var(--bs-body-color, #212529)',
            border: '1px solid var(--bs-border-color, #dee2e6)',
            borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,.18)',
            padding: '4px 0',
            fontSize: '13px',
            left: rect.left + 'px',
            top: rect.bottom + 2 + 'px',
        })

        function renderItems() {
            el.innerHTML = ''
            _items.forEach((it, idx) => {
                const row = document.createElement('div')
                row.className = 'var-suggest-item' + (idx === _selectedIdx ? ' var-suggest-active' : '')
                Object.assign(row.style, {
                    padding: '4px 10px',
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: idx === _selectedIdx ? 'var(--bs-primary, #0d6efd)' : 'transparent',
                    color: idx === _selectedIdx ? '#fff' : 'inherit',
                    borderRadius: '3px',
                    margin: '0 4px',
                })
                const lbl = document.createElement('span')
                lbl.textContent = it.label
                lbl.style.fontFamily = 'monospace'
                row.appendChild(lbl)
                if (it.info) {
                    const inf = document.createElement('span')
                    inf.textContent = it.info
                    Object.assign(inf.style, { fontSize: '11px', opacity: '0.6', marginLeft: '8px' })
                    row.appendChild(inf)
                }
                row.addEventListener('mousedown', (ev) => {
                    ev.preventDefault()
                    ev.stopPropagation()
                    doPick(it)
                })
                row.addEventListener('mouseenter', () => {
                    _selectedIdx = idx
                    renderItems()
                })
                el.appendChild(row)
            })
        }

        el._renderItems = renderItems
        renderItems()
        document.body.appendChild(el)

        // Keyboard handler — only arrows and escape (Tab handled by CM6 domEventHandlers)
        function onKey(ev) {
            if (ev.key === 'ArrowDown') {
                ev.preventDefault()
                ev.stopImmediatePropagation()
                _selectedIdx = (_selectedIdx + 1) % _items.length
                renderItems()
            } else if (ev.key === 'ArrowUp') {
                ev.preventDefault()
                ev.stopImmediatePropagation()
                _selectedIdx = (_selectedIdx - 1 + _items.length) % _items.length
                renderItems()
            } else if (ev.key === 'Escape') {
                ev.preventDefault()
                ev.stopImmediatePropagation()
                closeDropdownFull()
            }
            // Tab is NOT handled here — handled by CM6 domEventHandlers
        }
        document.addEventListener('keydown', onKey, true)

        el._cleanup = () => {
            document.removeEventListener('keydown', onKey, true)
        }
        _dropdown = el
        return el
    }

    // ── Suggestion logic ──────────────────────────────────────────────

    // Helpers
    const ID_SEG = '(?:\\d+|[0-9a-f-]{36})'     // numeric id or UUID

    function filterItems(items, query) {
        const q = query.toLowerCase()
        return items.filter(it => it.label.toLowerCase().startsWith(q))
    }

    function getSuggestions(token) {
        const t = token

        // ── Root level ────────────────────────────────────────────────
        // "@"
        if (t === '@') return { items: ROOT_ITEMS }

        // "@th", "@ca", etc → filter roots
        if (/^@\w+$/.test(t) && !t.endsWith('.')) {
            const q = t.slice(1).toLowerCase()
            return { items: ROOT_ITEMS.filter(it =>
                it.label.toLowerCase().startsWith('@' + q) || it.label.toLowerCase().includes(q)
            )}
        }

        // ── @this. ───────────────────────────────────────────────────
        if (t === '@this.') return { items: THIS_ITEMS }
        if (/^@this\.\w+$/.test(t) && !t.endsWith('.')) {
            return { items: filterItems(THIS_ITEMS, t.slice(6)) }
        }

        // ── Determine entity type from prefix ────────────────────────
        // Match patterns like:
        //   @case.          @task.          @this.case.     @this.task.
        //   @case.<id>.     @task.<id>.
        //   ...and deeper sub-paths
        const caseDirectRe = new RegExp('^@(?:this\\.)?case\\.')
        const taskDirectRe = new RegExp('^@(?:this\\.)?task\\.')
        const caseIdRe     = new RegExp('^@case\\.' + ID_SEG + '\\.')
        const taskIdRe     = new RegExp('^@task\\.' + ID_SEG + '\\.')

        const isCase = caseDirectRe.test(t) || caseIdRe.test(t)
        const isTask = taskDirectRe.test(t) || taskIdRe.test(t)

        if (!isCase && !isTask) return { items: [] }

        // Strip the entity prefix to get the "rest" after the entity dot
        // e.g. "@this.case.tasks.1.tit" → "tasks.1.tit"
        //      "@case."                 → ""
        //      "@task.42.sub"           → "sub"
        let rest
        if (/^@this\.(case|task)\./.test(t)) {
            rest = t.replace(/^@this\.(case|task)\./, '')
        } else if (new RegExp('^@(case|task)\\.' + ID_SEG + '\\.').test(t)) {
            rest = t.replace(new RegExp('^@(case|task)\\.' + ID_SEG + '\\.'), '')
        } else {
            // "@case." or "@task." with nothing after yet
            rest = t.replace(/^@(case|task)\./, '')
        }

        const propItems = isCase ? CASE_PROPERTY_ITEMS : TASK_PROPERTY_ITEMS

        // ── First-level property ──────────────────────────────────────
        // rest is "" → show all props
        if (rest === '') return { items: propItems }

        // rest is a partial word like "tit" → filter props
        if (/^\w+$/.test(rest) && !rest.endsWith('.')) {
            return { items: filterItems(propItems, rest) }
        }

        // ── tasks.<n>. sub-path (case only) ───────────────────────────
        if (isCase && /^tasks\./.test(rest)) {
            const afterTasks = rest.slice(6) // after "tasks."
            // "tasks." → prompt for <n> (just show hint)
            if (afterTasks === '') return { items: [{ label: '<n>', insert: '', info: 'Task position (1-based)' }] }
            // "tasks.1" (no trailing dot yet) → no suggestions, user types a number
            if (/^\d+$/.test(afterTasks)) return { items: [] }
            // "tasks.1." → show task properties
            if (/^\d+\.$/.test(afterTasks)) return { items: TASK_PROPERTY_ITEMS }
            // "tasks.1.tit" → filter task properties
            const m = afterTasks.match(/^\d+\.(\w+)$/)
            if (m) return { items: filterItems(TASK_PROPERTY_ITEMS, m[1]) }
            // deeper sub-paths of tasks.<n>.subtasks / tasks.<n>.notes
            return resolveTaskSubpath(afterTasks)
        }

        // ── subtasks.<n>. sub-path (task only) ────────────────────────
        if (isTask && /^subtasks\./.test(rest)) {
            return resolveSubtaskPath(rest.slice(9))
        }

        // ── notes.<n>. sub-path (task only) ───────────────────────────
        if (isTask && /^notes\./.test(rest)) {
            return resolveNotePath(rest.slice(6))
        }

        // ── misp_objects sub-paths (case only) ────────────────────────
        if (isCase && /^misp_objects\./.test(rest)) {
            return resolveMispPath(rest.slice(13))
        }

        return { items: [] }
    }

    // Sub-path resolvers for nested collections

    function resolveTaskSubpath(afterN) {
        // afterN is everything after "tasks.<n>." e.g. "subtasks.1.desc"
        // First strip the "<n>." part
        const m = afterN.match(/^\d+\.(.*)$/)
        if (!m) return { items: [] }
        const rest = m[1]

        if (/^subtasks\./.test(rest)) return resolveSubtaskPath(rest.slice(9))
        if (/^notes\./.test(rest)) return resolveNotePath(rest.slice(6))

        return { items: [] }
    }

    function resolveSubtaskPath(after) {
        // after is everything after "subtasks."
        if (after === '') return { items: [{ label: '<n>', insert: '', info: 'Subtask position (1-based)' }] }
        if (/^\d+$/.test(after)) return { items: [] }
        if (/^\d+\.$/.test(after)) return { items: SUBTASK_PROPERTY_ITEMS }
        const m = after.match(/^\d+\.(\w+)$/)
        if (m) return { items: filterItems(SUBTASK_PROPERTY_ITEMS, m[1]) }
        return { items: [] }
    }

    function resolveNotePath(after) {
        if (after === '') return { items: [{ label: '<n>', insert: '', info: 'Note position (1-based)' }] }
        if (/^\d+$/.test(after)) return { items: [] }
        if (/^\d+\.$/.test(after)) return { items: NOTE_PROPERTY_ITEMS }
        const m = after.match(/^\d+\.(\w+)$/)
        if (m) return { items: filterItems(NOTE_PROPERTY_ITEMS, m[1]) }
        return { items: [] }
    }

    function resolveMispPath(after) {
        // after is everything after "misp_objects."
        if (after === '') return { items: [{ label: '<n>', insert: '', info: 'MISP object position (1-based)' }] }
        if (/^\d+$/.test(after)) return { items: [] }
        if (/^\d+\.$/.test(after)) return { items: MISP_OBJECT_PROPERTY_ITEMS }
        // misp_objects.<n>.attr_partial
        const propM = after.match(/^\d+\.(\w+)$/)
        if (propM) return { items: filterItems(MISP_OBJECT_PROPERTY_ITEMS, propM[1]) }
        // misp_objects.<n>.attributes.<m>...
        const attrDeep = after.match(/^\d+\.attributes\.(.*)$/)
        if (attrDeep) return resolveAttributePath(attrDeep[1])
        return { items: [] }
    }

    function resolveAttributePath(after) {
        if (after === '') return { items: [{ label: '<m>', insert: '', info: 'Attribute position (1-based)' }] }
        if (/^\d+$/.test(after)) return { items: [] }
        if (/^\d+\.$/.test(after)) return { items: ATTRIBUTE_PROPERTY_ITEMS }
        const m = after.match(/^\d+\.(\w+)$/)
        if (m) return { items: filterItems(ATTRIBUTE_PROPERTY_ITEMS, m[1]) }
        return { items: [] }
    }

    // ── CodeMirror 6 Extension ────────────────────────────────────────

    function extension() {
        const { EditorView } = window.CodeMirrorBundle

        // Intercept Tab at CM6 DOM level — this is the ONLY place Tab is handled
        const keyIntercept = EditorView.domEventHandlers({
            keydown(event, view) {
                if (!_dropdown) return false
                if (event.key === 'Tab') {
                    event.preventDefault()
                    event.stopImmediatePropagation()
                    const picked = _items[_selectedIdx]
                    if (picked) doPick(picked)
                    return true
                }
                return false
            }
        })

        // Disable browser autocomplete/autofill on the editor
        const noAutocomplete = EditorView.contentAttributes.of({
            autocomplete: 'off',
            autocorrect: 'off',
            autocapitalize: 'off',
            spellcheck: 'false',
        })

        return [
        keyIntercept,
        noAutocomplete,
        EditorView.updateListener.of((update) => {
            if (!update.docChanged && !update.selectionSet) return
            if (Date.now() < _suppressUntil) return

            const state = update.state
            const pos = state.selection.main.head
            const docText = state.doc.toString()
            const tok = getTokenBefore(docText, pos)

            if (!tok) {
                closeDropdownFull()
                return
            }

            const { items } = getSuggestions(tok.text)
            if (!items.length) {
                closeDropdownFull()
                return
            }

            // Store the active view so doPick can use it
            _activeView = update.view

            let rect
            try {
                rect = update.view.coordsAtPos(pos)
            } catch (e) {
                rect = null
            }
            if (!rect) {
                const domRect = update.view.dom.getBoundingClientRect()
                rect = { left: domRect.left + 8, bottom: domRect.top + 20 }
            }

            createDropdown(items, rect)
        })
        ]
    }

    // ── CSS injection ─────────────────────────────────────────────────
    const styleId = 'var-suggest-style'
    if (!document.getElementById(styleId)) {
        const s = document.createElement('style')
        s.id = styleId
        s.textContent = [
            '.var-suggest-dropdown { font-family: system-ui, sans-serif; }',
            '.var-suggest-item { transition: background 0.1s; }',
        ].join('\n')
        document.head.appendChild(s)
    }

    // Close dropdown on outside click
    document.addEventListener('mousedown', (ev) => {
        if (_dropdown && !_dropdown.contains(ev.target)) {
            closeDropdownFull()
        }
    })

    // ── Public API ────────────────────────────────────────────────────
    window.FlowintelVarComplete = {
        extension: extension,
    }

})();
