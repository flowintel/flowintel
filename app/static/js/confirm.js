// Shared confirmation modal used by destructive actions.
//
// Returns a Promise that resolves to `true` if the user confirms, or `false`
// otherwise. The modal element is created once per page and reused.

let _modal = null
let _bs = null
let _titleEl = null
let _msgEl = null
let _confirmBtn = null
let _detailEl = null

function _ensureModal() {
    if (_modal) return
    const wrapper = document.createElement('div')
    wrapper.innerHTML = `
        <div class="modal fade" id="shared-confirm-delete-modal" tabindex="-1" aria-labelledby="shared-confirm-delete-title" aria-hidden="true">
            <div class="modal-dialog modal-sm modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="shared-confirm-delete-title">Delete ?</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body" id="shared-confirm-delete-body">
                        <p class="mb-1" id="shared-confirm-delete-message">Are you sure?</p>
                        <p class="text-muted small mb-0" id="shared-confirm-delete-detail" style="display:none;"></p>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-danger btn-sm" id="shared-confirm-delete-confirm">
                            <i class="fa-solid fa-trash"></i> Confirm
                        </button>
                    </div>
                </div>
            </div>
        </div>`
    document.body.appendChild(wrapper.firstElementChild)
    _modal = document.getElementById('shared-confirm-delete-modal')
    _titleEl = document.getElementById('shared-confirm-delete-title')
    _msgEl = document.getElementById('shared-confirm-delete-message')
    _detailEl = document.getElementById('shared-confirm-delete-detail')
    _confirmBtn = document.getElementById('shared-confirm-delete-confirm')
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        _bs = new bootstrap.Modal(_modal)
    }
}

/**
 * Show a confirmation modal styled like the Delete Task dialog.
 *
 * @param {Object} [opts]
 * @param {string} [opts.title]   Dialog title. Defaults to "Delete ?".
 * @param {string} [opts.message] Question shown in the body.
 * @param {string} [opts.detail]  Optional secondary line (smaller, muted).
 * @param {string} [opts.confirmText] Confirm button label. Defaults to "Confirm".
 * @returns {Promise<boolean>}
 */
export function confirmDelete(opts = {}) {
    _ensureModal()
    _titleEl.textContent = opts.title || 'Delete ?'
    _msgEl.textContent = opts.message || 'Are you sure you want to delete this item? This cannot be undone.'
    if (opts.detail) {
        _detailEl.textContent = opts.detail
        _detailEl.style.display = ''
    } else {
        _detailEl.textContent = ''
        _detailEl.style.display = 'none'
    }
    _confirmBtn.innerHTML = '<i class="fa-solid fa-trash"></i> ' + (opts.confirmText || 'Confirm')

    return new Promise((resolve) => {
        let settled = false
        const onConfirm = () => {
            if (settled) return
            settled = true
            cleanup()
            if (_bs) _bs.hide()
            resolve(true)
        }
        const onHidden = () => {
            if (settled) return
            settled = true
            cleanup()
            resolve(false)
        }
        function cleanup() {
            _confirmBtn.removeEventListener('click', onConfirm)
            _modal.removeEventListener('hidden.bs.modal', onHidden)
        }
        _confirmBtn.addEventListener('click', onConfirm)
        _modal.addEventListener('hidden.bs.modal', onHidden)
        if (_bs) {
            _bs.show()
        } else if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
            _bs = new bootstrap.Modal(_modal)
            _bs.show()
        }
    })
}
