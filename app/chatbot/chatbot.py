from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from .chatbot_core import get_chatbot_response
from ..utils.logger import flowintel_log

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


@chatbot_blueprint.route("/ask", methods=['POST'])
@login_required
def ask():
    data = request.get_json()
    if not data or not data.get("message"):
        return jsonify({"error": "Message is required"}), 400

    message = data["message"].strip()
    if not message:
        return jsonify({"error": "Message cannot be empty"}), 400

    # Limit message length to prevent abuse
    if len(message) > 4000:
        return jsonify({"error": "Message too long (max 4000 characters)"}), 400

    try:
        response = get_chatbot_response(message)
        flowintel_log("audit", 200, "Chatbot query", User=current_user.email)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": f"Chatbot error: {str(e)}"}), 500
