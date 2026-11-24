import { timestamp } from '../vendor/vitrine/flowtime.js'

/** Map the response of /case/:id/get_timeline_events. Undated records are reported, never silently placed. */
export function fromFlowintel(payload) {
  const records = Array.isArray(payload) ? payload : payload?.events;
  if (!Array.isArray(records))
    throw new TypeError("Expected a Flowintel event array or { events: [] }.");
  const events = [],
    rejected = [];
  for (const record of records) {
    const start = timestamp(record.date_parsed);
    const fallback = Number.isFinite(start)
      ? start
      : timestamp(record.date_text);
    if (!Number.isFinite(fallback)) {
      rejected.push({
        record,
        reason: "Missing or invalid ISO date; supply date_parsed from the API.",
      });
      continue;
    }
    const object = Number(record.misp_object_id);
    const group =
      object > 0
        ? "objects"
        : object < 0
          ? "attributes"
          : record.file_id
            ? "files"
            : "analysis";
    events.push({
      id: record.id,
      start: fallback,
      title: record.description || "Untitled event",
      description: record.additional_note || "",
      group,
      metadata: {
        "Event ID": record.id,
        ...(record.misp_object_id ? { "MISP ID": record.misp_object_id } : {}),
        ...(record.file_id ? { "File ID": record.file_id } : {}),
      },
      source: record,
    });
  }
  return { events, rejected };
}
