from ..db_class.db import User, Role, Org


def verif_add_user(data_dict):
    if "first_name" not in data_dict or not data_dict["first_name"]:
        return {"message": "Please give a first name for the user"}

    if "last_name" not in data_dict or not data_dict["last_name"]:
        return {"message": "Please give a last name for the user"}
    
    if "nickname" not in data_dict or not data_dict["nickname"]:
        data_dict["nickname"] = None

    if "email" not in data_dict or not data_dict["email"]:
        return {"message": "Please give an email for the user"}
    elif User.query.filter_by(email=data_dict["email"]).first():
        return {"message": "Email already exists"}
    
    if "matrix_id" not in data_dict or not data_dict["matrix_id"]:
        data_dict["matrix_id"] = None

    if "password" not in data_dict or not data_dict["password"]:
        return {"message": "Please give a password for the user"}

    if "role" not in data_dict or not data_dict["role"]:
        return {"message": "Please give a role for the user"}
    elif not Role.query.get(data_dict["role"]):
        return {"message": "Role not identified"}
    
    if "org" not in data_dict or not data_dict["org"]:
        data_dict["org"] = None

    return data_dict

def verif_edit_user(data_dict, user_id):
    user = User.query.get(user_id)
    if "first_name" not in data_dict or not data_dict["first_name"]:
        data_dict["first_name"] = user.first_name

    if "last_name" not in data_dict or not data_dict["last_name"]:
        data_dict["last_name"] = user.last_name

    if "nickname" not in data_dict or not data_dict["nickname"]:
        data_dict["nickname"] = user.nickname

    if "email" not in data_dict or not data_dict["email"]:
        data_dict["email"] = user.email
    elif User.query.filter_by(email=data_dict["email"]).first():
        return {"message": "Email already exist"}
    
    if "matrix_id" not in data_dict or not data_dict["matrix_id"]:
        data_dict["matrix_id"] = user.matrix_id

    if "role" not in data_dict or not data_dict["role"]:
        data_dict["role"] = user.role_id
    elif not Role.query.get(data_dict["role"]):
        return {"message": "Role not identified"}
    
    if "org" not in data_dict or not data_dict["org"]:
        data_dict["org"] = user.org_id

    return data_dict


def verif_add_org(data_dict):
    if "name" not in data_dict or not data_dict["name"]:
        return {"message": "Please give a name for the org"}
    elif Org.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exists"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = ""

    if "uuid" not in data_dict or not data_dict["uuid"]:
        data_dict["uuid"] = ""

    return data_dict


def verif_edit_org(data_dict, org_id):
    org = Org.query.get(org_id)
    if "name" not in data_dict or data_dict["name"] == org.name or not data_dict["name"]:
        data_dict["name"] = org.name
    elif Org.query.filter_by(name=data_dict["name"]).first():
        return {"message": "Name already exists"}

    if "description" not in data_dict or not data_dict["description"]:
        data_dict["description"] = org.description

    if "uuid" not in data_dict or not data_dict["uuid"]:
        data_dict["uuid"] = org.uuid

    return data_dict

