// Optional date picker for the free-text timeline date fields. Uses the
// flatpickr build already shipped for the calendar page. Nothing is written to
// the field until the user clicks "Validate", so it is clear when the date is
// applied. The value is written as "YYYY-MM-DD HH:MM".

function pad(n) {
    return String(n).padStart(2, '0')
}

function format_date(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate())
        + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes())
}

function parse_current(text) {
    const t = (text || '').trim()
    const m = t.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2}))?/)
    if (!m) return null
    return new Date(+m[1], +m[2] - 1, +m[3], +(m[4] || 0), +(m[5] || 0))
}

// `button` is the calendar button that was clicked; the picker is anchored to
// the text input in the same input-group. `on_apply(value)` receives the
// formatted date, or '' when the user clears it.
export function open_timeline_date_picker(button, current_text, on_apply) {
    if (typeof window.flatpickr !== 'function') return

    const group = button.closest('.input-group')
    const anchor = group ? group.querySelector('input[type="text"]') : button
    const holder = document.createElement('input')
    holder.type = 'text'
    holder.className = 'visually-hidden'
    holder.tabIndex = -1
    holder.setAttribute('aria-hidden', 'true')
    button.after(holder)

    const fp = window.flatpickr(holder, {
        enableTime: true,
        time_24hr: true,
        allowInput: false,
        clickOpens: false,
        positionElement: anchor,
        defaultDate: parse_current(current_text) || undefined,
        onReady(_dates, _str, instance) {
            const footer = document.createElement('div')
            footer.className = 'd-flex justify-content-end gap-1 p-2 border-top'

            const clear = document.createElement('button')
            clear.type = 'button'
            clear.className = 'btn btn-outline-secondary btn-sm'
            clear.textContent = 'Clear'
            clear.addEventListener('click', () => {
                on_apply('')
                instance.close()
            })

            const validate = document.createElement('button')
            validate.type = 'button'
            validate.className = 'btn btn-primary btn-sm'
            validate.innerHTML = '<i class="fa-solid fa-check me-1"></i>Validate'
            validate.addEventListener('click', () => {
                const picked = instance.selectedDates[0]
                if (picked) on_apply(format_date(picked))
                instance.close()
            })

            footer.append(clear, validate)
            instance.calendarContainer.appendChild(footer)
        },
        onClose(_dates, _str, instance) {
            // Closing without "Validate" (click outside, Escape) leaves the
            // field untouched.
            setTimeout(() => {
                instance.destroy()
                holder.remove()
            }, 0)
        }
    })
    fp.open()
}
