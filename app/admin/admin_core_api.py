from ..db_class.db import User, Role, Org


def verif_add_user(data_dict):
    if "first_name" not in data_dict:
        return {"message": "Please give a fist name for the user"}

    if "last_name" not in data_dict:
        return {"message": "Please give a last name for the user"}

    if "email" not in data_dict:
        return {"message": "Please give an email for the user"}
    elif User.query.filter_by(email=data_dict["email"]).first():
        return {"message": "Email already exist"}

    if "password" not in data_dict:
        return {"message": "Please give a password for the user"}

    if "role" not in data_dict:
        return {"message": "Please give a role for the user"}
    elif not Role.query.get(data_dict["role"]):
        if not Role.query.filter_by(name=data_dict["role"]):
            return {"message": "Role not identified"}
    
    if "org" not in data_dict:
        data_dict["org"] = "None"

    return data_dict

def verif_edit_user(data_dict, user_id):
    user = User.query.get(user_id)
    if "first_name" not in data_dict:
        data_dict["first_name"] = user.first_name

    if "last_name" not in data_dict:
        data_dict["last_name"] = user.last_name

    if "role" not in data_dict:
        data_dict["role"] = user.role
    
    if "org" not in data_dict:
        data_dict["org"] = user.org_id

    return data_dict


def verif_add_org(data_dict):
    if "name" not in data_dict:
        return {"message": "Please give a name for the org"}
    elif Org.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}

    if "description" not in data_dict:
        data_dict["description"] = ""

    if "uuid" not in data_dict:
        data_dict["uuid"] = ""

    return data_dict


def verif_edit_org(data_dict, org_id):
    org = Org.query.get(org_id)
    if "name" not in data_dict or data_dict["name"] == org.name :
        data_dict["name"] = org.name
    elif Org.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}

    if "description" not in data_dict:
        data_dict["description"] = org.description

    if "uuid" not in data_dict:
        data_dict["uuid"] = org.uuid

    return data_dict


def verif_add_role(data_dict):
    if "name" not in data_dict:
        return {"message": "Please give a name for the org"}
    elif Role.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}

    if "description" not in data_dict:
        data_dict["description"] = ""

    if "admin" not in data_dict:
        data_dict["admin"] = False

    if "read_only" not in data_dict or "admin" not in data_dict:
        data_dict["read_only"] = True

    return data_dict


def verif_edit_role(data_dict, role_id):
    role = Role.query.get(role_id)
    if "name" not in data_dict or data_dict["name"] == role.name :
        data_dict["name"] = role.name
    elif Role.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exist"}

    if "description" not in data_dict:
        data_dict["description"] = role.description

    if "admin" not in data_dict:
        data_dict["admin"] = role.admin

    if "read_only" not in data_dict and "admin" not in data_dict:
        data_dict["read_only"] = role.read_only

    return data_dict