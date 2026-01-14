import json
import aiohttp
import conf.config_module as Config
from nio import AsyncClient, AsyncClientConfig, SyncResponse
from nio.responses import LoginError
import asyncio
import os


module_config = {
    "case_task": "task"
}
module_path = os.path.join(os.getcwd(), "app", "modules", "notify_user")

def write_device_id(device_id, access_token):
    with open(os.path.join(module_path, "matrix_session.txt"), "w") as write_file:
        write_file.write(device_id)
        write_file.write("\n")
        write_file.write(access_token)

def read_device_id():
    loc_path = os.path.join(module_path, "matrix_session.txt")
    if os.path.isfile(loc_path):
        with open(loc_path, "r") as read_file:
            device_id = read_file.readline().rstrip()
            access_token = read_file.readline().rstrip()
        return device_id, access_token
    return "", ""

STORE_FOLDER = os.path.join(module_path, "matrix_store")

    
async def matrix(task, case, current_user, user):
    if not os.path.isdir(STORE_FOLDER):
        os.mkdir(STORE_FOLDER)

    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        encryption_enabled = True, 
        store_sync_tokens=True
    )

    device_id, access_token = read_device_id()
    # device_id == session_id, access_token == Help&about -> Access Token
    client = AsyncClient(Config.MATRIX_SERVER, config=client_config, device_id=device_id, store_path=STORE_FOLDER, user=Config.MATRIX_USER)

    try:
        # Connection to matrix server
        if access_token:
            client.access_token = access_token
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f'{Config.MATRIX_SERVER}/_matrix/client/r0/account/whoami?access_token={client.access_token}'
                ) as response:
                    if isinstance(response, LoginError):
                        raise ConnectionError(response)

                    r = json.loads((await response.text()).replace(":false,", ":\"false\","))
                    # This assumes there was an error that needs to be communicated to the user. A key error happens in
                    # the absence of an error code -> everything fine, we pass
                    try:
                        raise ConnectionError(f"{r['errcode']}: {r['error']}")
                    except KeyError:
                        pass
                    client.user_id = r['user_id']
        else:
            res = await client.login(password=Config.MATRIX_PASSWORD, device_name="flowintel")

            # print(res)
            if not device_id:
                client.device_id = res.device_id
                write_device_id(res.device_id, res.access_token)

        if client.should_upload_keys:
            await client.keys_upload()

        if client_config.encryption_enabled:
            client.load_store()

        await client.sync(timeout=65536, full_state=False)  #Ignore prior messages

        mentions = {}
        if user.matrix_id:
            user_matrix = user.matrix_id.split(":")[0]

            mentions["user_ids"] = [user.matrix_id]
        else:
            user_matrix = f"{user.first_name} {user.last_name}"
        # Message to send
        message = f"{user_matrix}, your attention is required on Task '{task.title}' for the Case '{case.title}' (http://{Config.ORIGIN_URL}/case/{task.case_id})"


        # Send message in specific room
        await client.room_send(
            Config.MATRIX_ROOM_ID,
            message_type="m.room.message",
            content={
                "msgtype": "m.text", 
                "body": message, 
                "m.mentions": mentions
            }, 
            ignore_unverified_devices=True
        )

        # print("Message envoyé avec succès!")

    except Exception as e:
        print(f"Une erreur s'est produite : {e}")

    finally:
        # Deconnect client
        await client.close()
        

def handler(task, case, current_user, user):
    """
    task: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors
    
    current_user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id

    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id
    """
    
    asyncio.run(matrix(task, case, current_user, user))
    

def introspection():
    return module_config