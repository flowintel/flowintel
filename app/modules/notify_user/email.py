import conf.config_module as Config
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


module_config = {
    "case_task": "task"
}

def handler(task, case, current_user, user):
    """
    task: id, uuid, title, description, url, notes, creation_date, last_modif, case_id, status_id, status,
                   completed, deadline, finish_date, tags, clusters, connectors
    
    user: id, first_name, last_name, email, role_id, password_hash, api_key, org_id
    """
    

    # Destinataire et contenu de l'email
    recipient_email = user.email
    subject = 'Flowintel-cm notification'
    body = f'{current_user.first_name} {current_user.last_name} notify you on task {task.title} \n (http://{Config.ORIGIN_URL}/case/{task.case_id})'

    # Création du message
    message = MIMEMultipart()
    message['From'] = Config.SENDER_EMAIL
    message['To'] = recipient_email
    message['Subject'] = subject

    # Ajout du corps du message
    message.attach(MIMEText(body, 'plain'))

    # Connexion au serveur SMTP
    server = smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT)
    server.starttls()
    server.login(Config.SENDER_EMAIL, Config.SENDER_PASSOWRD)

    # Envoi de l'email
    server.sendmail(Config.SENDER_EMAIL, recipient_email, message.as_string())

    # Fermeture de la connexion SMTP
    server.quit()

    print("L'email a été envoyé avec succès.")



def introspection():
    return module_config