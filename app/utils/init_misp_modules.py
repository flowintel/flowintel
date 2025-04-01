import json
from ..db_class.db import db
from ..db_class.db import Misp_Module, Configurable_Fields, Misp_Module_Config
from .utils import query_get_module


def create_modules_db():
    modules = query_get_module()
    if not "message" in modules:
        for module in modules:
            if "expansion" in module["meta"]["module-type"] or "hover" in module["meta"]["module-type"]:
                m = Misp_Module.query.filter_by(name=module["name"]).first()
                input_attr = ""
                if "input" in module["mispattributes"]:
                    input_attr = json.dumps(module["mispattributes"]["input"])
                if not m:
                    m = Misp_Module(
                        name=module["name"],
                        description=module["meta"]["description"],
                        input_attr=input_attr,
                        version=module["meta"]["version"]
                    )
                    db.session.add(m)
                    db.session.commit()


                    if "config" in module["meta"]:
                        for conf in module["meta"]["config"]:
                            c = Configurable_Fields.query.filter_by(name=conf).first()
                            if not c:
                                c = Configurable_Fields(
                                    name = conf
                                )
                                db.session.add(c)
                                db.session.commit()

                            mc = Misp_Module_Config(
                                module_id=m.id,
                                config_id=c.id
                            )
                            db.session.add(mc)
                            db.session.commit()
    else:
        print("[-] Error in misp-modules. It might not running.")