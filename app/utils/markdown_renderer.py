import base64
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import bleach
from bleach.css_sanitizer import CSSSanitizer

from .. import md

# Regex to capture fenced mermaid code blocks
MERMAID_BLOCK_RE = re.compile(r"```mermaid\s+([\s\S]*?)```", re.MULTILINE)

# Conservative HTML/SVG allowlists for the rendered output
ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union(
    {
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "pre",
        "code",
        "hr",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "blockquote",
        "svg",
        "g",
        "path",
        "line",
        "rect",
        "circle",
        "ellipse",
        "polyline",
        "polygon",
        "text",
        "tspan",
        "defs",
        "style",
        "title",
        "desc",
        "clipPath",
        "marker",
        "linearGradient",
        "stop",
    }
)

ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "title", "role", "aria-label", "style"],
    "a": ["href", "name", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height", "loading"],
    "svg": ["width", "height", "viewBox", "aria-label", "role", "xmlns", "preserveAspectRatio"],
    "g": ["transform", "clip-path", "filter"],
    "path": ["d", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "line": ["x1", "y1", "x2", "y2", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "rect": ["x", "y", "width", "height", "rx", "ry", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "circle": ["cx", "cy", "r", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "ellipse": ["cx", "cy", "rx", "ry", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "polyline": ["points", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "polygon": ["points", "fill", "stroke", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "stroke-dashoffset", "stroke-opacity", "fill-opacity", "marker-end", "marker-start", "marker-mid", "transform"],
    "text": ["x", "y", "dx", "dy", "fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "font-size", "font-family", "font-weight", "font-style", "text-anchor", "dominant-baseline", "alignment-baseline", "textLength", "lengthAdjust", "transform"],
    "tspan": ["x", "y", "dx", "dy", "fill", "fill-opacity", "stroke", "stroke-width", "stroke-opacity", "font-size", "font-family", "font-weight", "font-style", "text-anchor", "dominant-baseline", "alignment-baseline", "textLength", "lengthAdjust", "transform"],
    "style": ["type"],
    "marker": ["id", "markerWidth", "markerHeight", "refX", "refY", "orient", "markerUnits", "viewBox", "preserveAspectRatio"],
    "linearGradient": ["id", "x1", "y1", "x2", "y2", "gradientUnits", "gradientTransform"],
    "stop": ["offset", "stop-color", "stop-opacity"],
}

ALLOWED_PROTOCOLS = ["http", "https", "mailto", "data"]

CSS_SANITIZER = CSSSanitizer(
    allowed_css_properties=[
        "color",
        "background",
        "background-color",
        "font-size",
        "font-family",
        "font-weight",
        "font-style",
        "text-decoration",
        "text-anchor",
        "fill",
        "stroke",
        "stroke-width",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-dasharray",
        "stroke-dashoffset",
        "stroke-opacity",
        "fill-opacity",
        "opacity",
        "border",
        "border-radius",
        "letter-spacing",
        "line-height",
        "white-space",
        "padding",
        "margin",
    ],
    allowed_svg_properties=[],
)


class MermaidCLIRenderer:
    """Render mermaid diagrams using the mermaid-cli (mmdc) binary."""

    def __init__(self, background: str = "transparent", theme: str = "default", timeout: int = 10, cmd: Optional[str] = None):
        self.background = background
        self.theme = theme
        self.timeout = timeout
        self.cmd = cmd or os.getenv("MMDC_BIN") or "mmdc"
        self._check_mmdc_installed()

    def _check_mmdc_installed(self) -> None:
        """Validate that the mermaid-cli binary is reachable and working."""
        if not shutil.which(self.cmd):
            raise RuntimeError("mmdc not found. Install with: npm install -g @mermaid-js/mermaid-cli")
        try:
            subprocess.run([self.cmd, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            raise RuntimeError("mmdc executable is not working") from exc

    def render(self, mermaid_code: str, output_format: str = "svg"):
        if output_format not in {"svg", "png"}:
            raise ValueError("output_format must be 'svg' or 'png'")

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = Path(temp_dir) / "diagram.mmd"
            output_path = Path(temp_dir) / f"diagram.{output_format}"
            input_path.write_text(mermaid_code, encoding="utf-8")

            cmd = [
                self.cmd,
                "-i",
                str(input_path),
                "-o",
                str(output_path),
                "-b",
                self.background,
                "-t",
                self.theme,
                "--quiet",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=temp_dir,
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "mmdc failed"
                raise ValueError(f"Mermaid rendering failed: {error_msg}")

            if output_format == "svg":
                return output_path.read_text(encoding="utf-8")
            return output_path.read_bytes()


def sanitize_markdown_input(raw_text: str) -> str:
    """Strip any embedded HTML from markdown input before storing it."""
    if not raw_text:
        return ""
    return bleach.clean(raw_text, tags=[], attributes={}, protocols=[], strip=True)


def _sanitize_mermaid_source(source: str) -> str:
    """Remove any HTML or script from mermaid code blocks."""
    return bleach.clean(source, tags=[], attributes={}, protocols=[], strip=True)


def _sanitize_svg(svg_text: str) -> str:
    return bleach.clean(
        svg_text,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )


def _ensure_svg_style(svg_text: str, extra_css: str) -> str:
    """Insert or append extra CSS into the first <style> block of the SVG, or create one.

    This avoids touching the root <svg> attributes while ensuring specific rules
    (like hiding `.domain`) are present in the SVG's stylesheet.
    """
    if not svg_text or '<svg' not in svg_text:
        return svg_text

    # If there is a <style>...</style>, append the extra_css before the first </style>
    if '<style' in svg_text:
        return svg_text.replace('</style>', f'\n{extra_css}\n</style>', 1)

    # No existing style block: add one right after the opening <svg ...> tag
    m = re.search(r'<svg(\s[^>]*)?>', svg_text)
    if m:
        insert_pos = m.end()
        return svg_text[:insert_pos] + f'<style>{extra_css}</style>' + svg_text[insert_pos:]

    return svg_text


# Note: background forcing was removed per user request.


def render_markdown_with_mermaid(markdown_text: str, output_format: str = "svg") -> str:
    """Render markdown to safe HTML and convert mermaid blocks with mmdc.

    Args:
        markdown_text: Raw markdown text.
        output_format: "svg" or "png" for mermaid diagrams.

    Returns:
        Sanitized HTML string safe to inject in templates.
    """

    markdown_text = markdown_text or ""
    if isinstance(markdown_text, dict):
        # Prefer an explicit markdown field if present; otherwise serialize
        if "markdown" in markdown_text:
            markdown_text = markdown_text.get("markdown") or ""
        else:
            try:
                markdown_text = json.dumps(markdown_text, ensure_ascii=False)
            except Exception:
                markdown_text = str(markdown_text)
    elif not isinstance(markdown_text, str):
        try:
            markdown_text = json.dumps(markdown_text, ensure_ascii=False)
        except Exception:
            markdown_text = str(markdown_text)
    renderer: Optional[MermaidCLIRenderer] = None

    def replace_mermaid(match: re.Match) -> str:
        nonlocal renderer
        mermaid_code = _sanitize_mermaid_source(match.group(1))

        # avoid wasting cycles on oversized inputs
        if len(mermaid_code) > 50000:
            return "<pre class=\"mermaid-error\">Diagram too large to render.</pre>"

        try:
            if renderer is None:
                renderer = MermaidCLIRenderer()
            if output_format == "svg":
                svg = renderer.render(mermaid_code, "svg")
                safe_svg = _sanitize_svg(svg)
                # Hide the domain path that some renderers include as a background
                safe_svg = _ensure_svg_style(safe_svg, ".domain{display:none!important;}")
                return f"\n<div class=\"mermaid-graph\">{safe_svg}</div>\n"
            png_bytes = renderer.render(mermaid_code, "png")
            b64 = base64.b64encode(png_bytes).decode("ascii")
            return f"\n<img class=\"mermaid-graph\" src=\"data:image/png;base64,{b64}\" alt=\"Mermaid diagram\" loading=\"lazy\"/>\n"
        except Exception as exc:  # noqa: BLE001 - surface error to the caller
            safe_error = bleach.clean(str(exc))
            return f"<pre class=\"mermaid-error\">Mermaid render error: {safe_error}</pre>"

    processed = MERMAID_BLOCK_RE.sub(replace_mermaid, markdown_text)

    # md = markdown.Markdown(extensions=["fenced_code", "tables", "nl2br", "sane_lists"], output_format="html5")
    html = md.convert(processed)

    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
