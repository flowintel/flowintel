import { timestamp } from '../vendor/vitrine/flowtime.js'

// History uses the earliest valid attribute first_seen, then the object's creation date.
export function fromMispObjects(objects) {
    const events = [], rejected = []
    for (const [index, object] of objects.entries()) {
        const attributes = object.attributes || []
        const first_seen = attributes.map(attribute => timestamp(attribute.first_seen)).filter(Number.isFinite)
        const start = first_seen.length
            ? first_seen.reduce((earliest, date) => Math.min(earliest, date), Infinity)
            : [object.object_creation_date, object.creation_date].map(timestamp).find(Number.isFinite)
        if (!Number.isFinite(start)) {
            rejected.push(object)
            continue
        }
        const description = attributes.map(attribute => [
            'Value: ' + String(attribute.value ?? ''),
            'Type: ' + String(attribute.type ?? ''),
            'Comment: ' + String(attribute.comment ?? ''),
            'First seen: ' + String(attribute.first_seen ?? ''),
            'Last seen: ' + String(attribute.last_seen ?? ''),
            'IDS: ' + String(attribute.ids_flag ?? '')
        ].join('\n')).join('\n\n')
        events.push({
            id: String(object.object_id ?? object.object_instance_uuid ?? index),
            start,
            title: object.object_name || 'MISP object',
            description,
            group: 'objects',
            metadata: { 'Object UUID': object.object_uuid },
            source: object
        })
    }
    return { events, rejected }
}
