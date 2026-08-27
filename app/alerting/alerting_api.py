from flask import request
from flask_restx import Namespace, Resource

from app.alerting import alerting_core as AlertingCore
from app.decorators import api_required


alerting_ns = Namespace("alerts", description="Endpoints to ingest and review external alerts")


@alerting_ns.route("/schema")
@alerting_ns.doc(description="Get the MISP event ingest JSON format example")
class AlertSchema(Resource):
    method_decorators = [api_required]

    def get(self):
        return {
            "schema": AlertingCore.FLOWINTEL_ALERT_SCHEMA,
            "description": "MISP event payload accepted as {'Event': {...}} or as a bare MISP event object.",
            "required": ["Event.info or Event.uuid", "Event.Attribute and/or Event.Object"],
            "recommended": ["Event.uuid", "Event.info", "Event.date", "Event.threat_level_id", "Event.Tag"],
            "optional": ["Event.Attribute", "Event.Object", "Event.Galaxy", "Event.GalaxyCluster", "Event.Orgc"],
            "example": AlertingCore.alert_schema_example(),
        }, 200


@alerting_ns.route("/ingest")
@alerting_ns.doc(description="Ingest a MISP event alert from an external tool using a connector instance API key")
class IngestAlert(Resource):
    @alerting_ns.doc(params={
        "X-API-KEY": "Connector instance API key. Also accepts X-FLOWINTEL-ALERT-KEY or Authorization: Bearer.",
    })
    def post(self):
        if request.content_length and request.content_length > AlertingCore.MAX_INGEST_BYTES:
            return {"message": "Alert payload is too large"}, 413

        identity = AlertingCore.connector_from_headers(request.headers)
        if not identity:
            return {"message": "Connector API key not found"}, 403

        payload = request.get_json(silent=True)
        if payload is None:
            return {"message": "Please send a JSON MISP event payload"}, 400

        alert, created, error = AlertingCore.ingest_alert(payload, identity)
        if error:
            return error, 400

        return {
            "message": "Alert created" if created else "Alert updated",
            "created": created,
            "alert_id": alert.id,
            "alert_uuid": alert.uuid,
            "review_status": alert.review_status,
            "occurrence_count": alert.occurrence_count,
        }, 201 if created else 200
