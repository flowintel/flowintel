from pymisp import MISPObject
from ..db_class.db import db, Case_Misp_Object, Misp_Attribute
import datetime
from dateutil.parser import parse as parse_date

def create_misp_object(case_id: int, misp_object: MISPObject):
    """
    Create a new misp object and its attributes.
    This will return a list of uuid for objects and attributes
    There are the uuid on the instance on misp of objects and attributes
    """
    object_uuid_list = {}
    loc_object = Case_Misp_Object(
        case_id=case_id,
        template_uuid=misp_object.template_uuid,
        name=misp_object.name,
        creation_date = datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
    )

    db.session.add(loc_object)
    db.session.commit()

    object_uuid_list[loc_object.id] = {"uuid": misp_object.uuid, "attributes": []}

    for object_attr in misp_object.attributes:
        first_seen = None
        last_seen = None

        if object_attr.get("first_seen"):
            val = object_attr.get("first_seen")
            if isinstance(val, datetime.datetime):
                first_seen = val
            else:
                try:
                    first_seen = parse_date(val)
                except Exception:
                    try:
                        # fallback to legacy exact format
                        first_seen = datetime.datetime.strptime(val, '%Y-%m-%dT%H:%M')
                    except Exception:
                        first_seen = None
        if object_attr.get("last_seen"):
            val = object_attr.get("last_seen")
            if isinstance(val, datetime.datetime):
                last_seen = val
            else:
                try:
                    last_seen = parse_date(val)
                except Exception:
                    try:
                        last_seen = datetime.datetime.strptime(val, '%Y-%m-%dT%H:%M')
                    except Exception:
                        last_seen = None

        attr = Misp_Attribute(
            case_misp_object_id=loc_object.id,
            value=object_attr.value,
            type=object_attr.type,
            object_relation=object_attr.object_relation,
            first_seen=first_seen,
            last_seen=last_seen,
            comment=object_attr.get("comment"),
            ids_flag=object_attr.to_ids,
            creation_date = datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db.session.add(attr)
        db.session.commit()

        object_uuid_list[loc_object.id]["attributes"].append({"uuid": object_attr.uuid, "attribute_id": attr.id})

    return object_uuid_list
        