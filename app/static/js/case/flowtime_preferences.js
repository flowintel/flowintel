// User preferences belong to Flowintel; the reusable viewer does not use storage.
const TEXT_SCALE_KEY = 'flowintel:flowtime:text-scale'

export function savedFlowtimeTextScale() {
    try {
        const scale = Number(localStorage.getItem(TEXT_SCALE_KEY))
        return Number.isFinite(scale) && scale >= 0.5 && scale <= 1.5 ? scale : 1
    } catch {
        return 1
    }
}

export function rememberFlowtimeTextScale(event) {
    try {
        localStorage.setItem(TEXT_SCALE_KEY, String(event.detail.textScale))
    } catch {
        // The text size control still works when browser storage is unavailable.
    }
}
