caseSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "deadline:": {"type": "string"},
        "recurring_date:": {"type": "string"},
        "recurring_type:": {"type": "string"},
        "notes:": {"type": "string"},
        "is_private:": {"type": "boolean"},
        "time_required:": {"type": "string"},
        "tasks": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "tags":{
            "type": "array",
            "items": {"type": "string"},
        },
        "clusters":{
            "type": "array",
            "items": {"type": "object"},
        },
        "misp-objects:": {
            "type": "array",
            "items": {"type": "object"}
        }
    },
    "required": ['title']
}

taskSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "deadline:": {"type": "string"},
        "time_required:": {"type": "string"},
        "urls_tools:": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "notes:": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "tags":{
            "type": "array",
            "items": {"type": "string"}
        },
        "clusters":{
            "type": "array",
            "items": {"type": "object"},
        },
        "subtasks:": {
            "type": "array",
            "items": {"type": "object"},
        }
    },
    "required": ['title']
}


mispObjectSchema = {
    "type": "object",
    "properties": {
        "template_uuid": {"type": "string"},
        "name": {"type": "string"},
        "creation_date": {"type": "string"},
        "last_modif": {"type": "string"},
        "attributes": {
            "type": "array",
            "items": {"type": "object"}
        }
    }
}

mispAttrSchema = {
    "type": "object",
    "properties": {
        "value": {"type": "string"},
        "type": {"type": "string"},
        "object_relation": {"type": "string"},
        "first_seen": {"type": "string"},
        "last_seen": {"type": "string"},
        "comment": {"type": "string"},
        "ids_flag": {"type": "boolean"},
        "creation_date": {"type": "string"},
        "last_modif": {"type": "string"},
        "disable_correlation": {"type": "boolean"}
    }
}

caseTemplateSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "notes:": {"type": "string"},
        "is_private:": {"type": "boolean"},
        "time_required:": {"type": "string"},
        "tasks_template": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "tags":{
            "type": "array",
            "items": {"type": "string"},
        },
        "clusters":{
            "type": "array",
            "items": {"type": "object"},
        },
    },
    "required": ['title']
}

taskTemplateSchema = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "description": {"type": "string"},
        "uuid": {"type": "string"},
        "time_required:": {"type": "string"},
        "urls_tools:": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "notes:": {
            "type": "array", 
            "items": {"type": "object"},
        },
        "tags":{
            "type": "array",
            "items": {"type": "string"}
        },
        "clusters":{
            "type": "array",
            "items": {"type": "object"},
        },
        "subtasks:": {
            "type": "array",
            "items": {"type": "object"},
        }
    },
    "required": ['title']
}