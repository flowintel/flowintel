import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
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
    conv = ChatConversation(
        user_id=current_user.id,
        title="New Conversation",
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
        # Auto-create a new conversation
        conv = ChatConversation(
            user_id=current_user.id,
            title=message[:80],
            created_at=datetime.datetime.now(tz=datetime.timezone.utc),
            updated_at=datetime.datetime.now(tz=datetime.timezone.utc),
        )
        db.session.add(conv)
        db.session.flush()  # get conv.id before commit

    history = [m.to_json() for m in conv.messages] if conv.messages else []

    try:
        response = get_chatbot_response(message, history=history)
        flowintel_log("audit", 200, "Chatbot query", User=current_user.email)
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500

    # Persist user message and assistant reply
    db.session.add(ChatMessage(
        conversation_id=conv.id,
        role="user",
        content=message,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    ))
    db.session.add(ChatMessage(
        conversation_id=conv.id,
        role="assistant",
        content=response,
        created_at=datetime.datetime.now(tz=datetime.timezone.utc),
    ))

    # Update conversation title from first message if still default
    if conv.title == "New Conversation":
        conv.title = message[:80]
    conv.updated_at = datetime.datetime.now(tz=datetime.timezone.utc)

    db.session.commit()
    return jsonify({"response": response, "conversation_id": conv.id, "conversation_title": conv.title})
