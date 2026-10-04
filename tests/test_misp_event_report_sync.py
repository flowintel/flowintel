import uuid

from pymisp import MISPEvent, MISPEventReport, PyMISP

from app.modules.send_to import misp_object_event


EVENT_ID = "42"
EVENT_REPORT_ID = "7"


class RecordingMisp:
    """Minimal stand-in for PyMISP that runs the real ``update_event_report``
    and records the URL it would POST to."""

    global_pythonify = False

    def __init__(self, fresh_event):
        self.fresh_event = fresh_event
        self.requests = []

    def get_event(self, event_id, pythonify=False):
        return self.fresh_event

    def _prepare_request(self, method, url, data=None, **kwargs):
        self.requests.append((method, url))
        return {"EventReport": {"id": EVENT_REPORT_ID}}

    def _check_json_response(self, response):
        return response

    def update_event_report(self, *args, **kwargs):
        return PyMISP.update_event_report(self, *args, **kwargs)

    def add_event_report(self, event_id, payload):
        self.requests.append(("POST", f"eventReports/add/{event_id}"))
        return {}


def test_report_resync_edits_the_event_report_not_the_event():
    local_object = {
        "id": 3,
        "template_uuid": misp_object_event.REPORT_TEMPLATE_UUID,
        "attributes": [
            {"object_relation": "title", "value": "Report title"},
            {"object_relation": "summary", "value": "Updated summary"},
        ],
    }
    report_uuid = str(uuid.uuid5(
        misp_object_event._EVENT_REPORT_NAMESPACE,
        f"flowintel-report-object-{local_object['id']}",
    ))

    existing_report = MISPEventReport()
    existing_report.from_dict(id=EVENT_REPORT_ID, uuid=report_uuid, event_id=EVENT_ID,
                              name="Report title", content="Old summary")
    fresh_event = MISPEvent()
    fresh_event.from_dict(id=EVENT_ID, info="event", EventReport=[existing_report])

    misp = RecordingMisp(fresh_event)
    misp_object_event._sync_report_event_reports(misp, {"id": EVENT_ID}, [local_object])

    assert misp.requests == [("POST", f"eventReports/edit/{report_uuid}")]
    assert fresh_event.EventReport[0].content == "Updated summary"
