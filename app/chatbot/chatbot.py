import datetime
import requests as http_requests
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import conf.config_module as ConfigModule
from .chatbot_core import get_chatbot_response
from ..utils.logger import flowintel_log
from .. import db
from ..db_class.db import ChatConversation, ChatMessage

chatbot_blueprint = Blueprint(
    'chatbot',
    __name__,
    template_folder='templates',
    static_folder='static'
)

@chatbot_blueprint.route("/", methods=['GET'])
@login_required
def index():
    flowintel_log("audit", 200, "Chatbot page accessed", User=current_user.email)
    return render_template("chatbot/chatbot.html")


@chatbot_blueprint.route("/models", methods=['GET'])
@login_required
def list_models():
    """Return available Ollama models from the configured Ollama instance."""
    base_url = getattr(ConfigModule, 'OLLAMA_URL', 'http://localhost:11434').rstrip('/')
    headers = {}
    api_key = getattr(ConfigModule, 'OLLAMA_KEY', None)
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    try:
        resp = http_requests.get(f'{base_url}/api/tags', headers=headers, timeout=5)
        resp.raise_for_status()
        models = [m['name'] for m in resp.json().get('models', [])]
        return jsonify({"models": models})
    except Exception as e:
        return jsonify({"models": [], "error": str(e)})


@chatbot_blueprint.route("/conversations", methods=['GET'])
@login_required
def list_conversations():
    convs = (ChatConversation.query
             .filter_by(user_id=current_user.id)
             .order_by(ChatConversation.updated_at.desc())
             .all())
    return jsonify([c.to_json() for c in convs])


@chatbot_blueprint.route("/conversation/new", methods=['POST'])
@login_required
def new_conversation():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "New Conversation")[:200]
    conv = ChatConversation(
        user_id=current_user.id,
        title=title,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
        updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
    )
    db.session.add(conv)
    db.session.commit()
    return jsonify(conv.to_json()), 201


@chatbot_blueprint.route("/conversation/<int:conv_id>", methods=['GET'])
@login_required
def get_conversation(conv_id):
    conv = ChatConversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    data = conv.to_json()
    data["messages"] = [m.to_json() for m in conv.messages]
    return jsonify(data)


@chatbot_blueprint.route("/conversation/<int:conv_id>", methods=['DELETE'])
@login_required
def delete_conversation(conv_id):
    conv = ChatConversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    db.session.delete(conv)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200


@chatbot_blueprint.route("/conversation/<int:conv_id>/title", methods=['PATCH'])
@login_required
def rename_conversation(conv_id):
    conv = ChatConversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
    if not conv:
        return jsonify({"error": "Conversation not found"}), 404
    data = request.get_json()
    title = (data or {}).get("title", "").strip()
    if not title:
        return jsonify({"error": "Title cannot be empty"}), 400
    conv.title = title[:200]
    conv.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()
    return jsonify(conv.to_json())


@chatbot_blueprint.route("/ask", methods=['POST'])
@login_required
def ask():
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    message = data["message"].strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    if len(message) > 4000:
        return jsonify({"error": "Message too long (max 4000 characters)"}), 400

    conv_id = data.get("conversation_id")
    conv = None

    if conv_id:
        conv = ChatConversation.query.filter_by(id=conv_id, user_id=current_user.id).first()
        if not conv:
            return jsonify({"error": "Conversation not found"}), 404
    else:
        # Auto-create a new conversation and commit immediately so the
        # write lock is released before the long AI inference call.
        conv = ChatConversation(
            user_id=current_user.id,
            title=message[:80],
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        db.session.add(conv)
        db.session.commit()

    # Collect data needed after the DB session is released
    conv_id_saved = conv.id
    history = [m.to_json() for m in conv.messages] if conv.messages else []
    model = data.get("model") or None
    # Capture plain scalars from current_user BEFORE removing the session;
    # after db.session.remove() the User instance is detached and attribute
    # access on it raises DetachedInstanceError.
    user_id_saved = current_user.id
    user_email_saved = current_user.email

    # Persist the user message NOW so it is immediately visible if the
    # conversation is loaded while the AI inference is still running.
    db.session.add(ChatMessage(
        conversation_id=conv.id,
        role="user",
        content=message,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    ))
    db.session.commit()

    # Release the DB connection back to the pool BEFORE the long AI call.
    # SQLite only allows one writer at a time; holding the session open here
    # would block every other request until inference finishes.
    db.session.remove()

    try:
        response, model_name = get_chatbot_response(message, history=history, model=model)
        flowintel_log("audit", 200, "Chatbot query", User=user_email_saved)
    except Exception as e:
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500

    # Re-acquire a session to persist the assistant reply
    conv = ChatConversation.query.filter_by(id=conv_id_saved, user_id=user_id_saved).first()
    if not conv:
        return jsonify({"error": "Conversation disappeared after AI call"}), 500

    db.session.add(ChatMessage(
        conversation_id=conv.id,
        role="assistant",
        content=response,
        model_name=model_name or None,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    ))

    # Update conversation title from first message if still default
    if conv.title == "New Conversation":
        conv.title = message[:80]
    conv.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    db.session.commit()
    return jsonify({"response": response, "model_name": model_name, "conversation_id": conv.id, "conversation_title": conv.title})
