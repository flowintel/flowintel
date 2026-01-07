import datetime
import json
from queue import Queue
from threading import Thread
from uuid import uuid4
from ..utils.utils import query_post_query, query_get_module, get_object
from . import misp_modules_core as MispModuleModel
from .. import db
from ..db_class.db import Misp_Module_Result, User

sessions = list()

class SessionClass:
    def __init__(self, request_json, user: User) -> None:
        self.uuid = str(uuid4())
        self.thread_count = 4
        self.jobs = Queue(maxsize=0)
        self.threads = []
        self.stopped = False
        self.result_stopped = dict()
        self.result = dict()
        self.query = request_json["query"]
        self.input_query = request_json["input"]
        self.modules_list = request_json["modules"]
        self.nb_errors = 0
        self.query_date = datetime.datetime.now(tz=datetime.timezone.utc)
        self.current_user = user
        self.config_module = self.config_module_setter(request_json)

    
    def config_module_setter(self, request_json):
        """Setter for config for all modules used"""
        for query in self.modules_list:
            request_json["config"] = {}
            request_json["config"][query] = {}
            module = MispModuleModel.get_module_by_name(query)
            mcs = MispModuleModel.get_module_config_module(module.id, self.current_user)
            for mc in mcs:
                config_db = MispModuleModel.get_configurable_fields(mc.config_id)
                request_json["config"][query][config_db.name] = mc.value
        return request_json["config"]

    def start(self):
        """Start all worker"""
        cp = 0
        for i in self.query:
            for j in self.modules_list:
                self.jobs.put((cp, i, j))
                cp += 1
        #need the index and the url in each queue item.
        for _ in range(self.thread_count):
            worker = Thread(target=self.process)
            worker.daemon = True
            worker.start()
            self.threads.append(worker)

    def status(self):
        """Status of the current queue"""
        if self.jobs.empty():
            self.stop()

        total = len(self.modules_list)
        remaining = max(self.jobs.qsize(), len(self.threads))
        complete = total - remaining
        registered = len(self.result)

        return {
            'id': self.uuid,
            'total': total,
            'complete': complete,
            'remaining': remaining,
            'registered': registered,
            'stopped' : self.stopped,
            "nb_errors": self.nb_errors
            }

    def status_for_test(self):
        return {
            'id': self.uuid,
            'total': 10,
            'complete': 5,
            'remaining': 5,
            'registered': 5,
            "nb_errors": 0
            }

    def stop(self):
        """Stop the current queue and worker"""
        self.jobs.queue.clear()

        for worker in self.threads:
            worker.join(3.5)

        self.threads.clear()
        self.save_info()
        sessions.remove(self)
        del self

    def process(self):
        """Threaded function for queue processing."""
        while not self.jobs.empty():
            work = self.jobs.get()

            modules = query_get_module()
            loc_query = {}
            self.result[work[1]] = dict()
            # If Misp format
            for module in modules:
                if module["name"] == work[2]:
                    if "format" in module["mispattributes"]:
                        loc_query = {
                            "type": self.input_query,
                            "value": work[1],
                            "uuid": str(uuid4())
                        }
                    break
            
            loc_config = {}
            if work[2] in self.config_module:
                loc_config = self.config_module[work[2]]
                
            if loc_query:
                send_to = {"module": work[2], "attribute": loc_query, "config": loc_config}
            else:
                send_to = {"module": work[2], self.input_query: work[1], "config": loc_config}
            res = query_post_query(send_to)

            ## Sort attr in object by ui-priority
            if res and "results" in res and "Object" in res["results"]:
                for obj in res["results"]["Object"]:
                    loc_obj = get_object(obj["name"])
                    if loc_obj:
                        for attr in obj["Attribute"]:
                            attr["ui-priority"] = loc_obj["attributes"][attr["object_relation"]]["ui-priority"]
                        
                        # After adding 'ui-priority'
                        obj["Attribute"].sort(key=lambda x: x["ui-priority"], reverse=True)
                    
            if res and "error" in res:
                self.nb_errors += 1
            self.result[work[1]][work[2]] = res

            self.jobs.task_done()
        return True
    
    def get_result(self):
        return self.result
    
    def save_info(self):
        """Save info in the db"""
        s = Misp_Module_Result(
            uuid=str(self.uuid),
            modules_list=json.dumps(self.modules_list),
            query_enter=json.dumps(self.query),
            input_query=self.input_query,
            result=json.dumps(self.result),
            nb_errors=self.nb_errors,
            query_date=self.query_date,
            user_id=self.current_user.id
        )
        db.session.add(s)
        db.session.commit()