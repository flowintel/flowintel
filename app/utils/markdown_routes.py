from flask import Blueprint, request
from flask_login import login_required

from .markdown_renderer import render_markdown_with_mermaid


markdown_blueprint = Blueprint(
    "markdown",
    __name__,
    template_folder="templates",
    static_folder="static",
)


@markdown_blueprint.route("/render", methods=["POST"])
@login_required
def render_markdown():
    payload = request.get_json(silent=True) or {}
    markdown_text = payload.get("markdown", "") or ""
    output_format = payload.get("format", "svg") or "svg"
    try:
        html = render_markdown_with_mermaid(markdown_text, "png" if output_format == "png" else "svg")
    except RuntimeError as exc:
        return {"message": str(exc)}, 500
    return {"html": html}, 200
