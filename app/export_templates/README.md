# Note Export Templates

Flowintel note exports load their default rendering templates from this
directory.

## PDF

`note_pdf.html` is a full WeasyPrint HTML document. It must include one of these
placeholders where the rendered Markdown HTML should be inserted:

- `{{ content }}`
- `{{ body }}`
- `{{ html_body }}`

The renderer also replaces `{{ app_name }}` and `{{ generated_at }}` when those
tokens are present.

To use another PDF template, set `NOTE_EXPORT_PDF_TEMPLATE` in `conf/config.py`
or as an environment variable. Relative paths are resolved from the Flowintel
project root. Relative image paths in the template are resolved from the
template file's directory.

## DOCX

`note_docx_styles.json` controls the style names and rendering options used by
the HTML-to-DOCX converter. To use another style JSON file, set
`NOTE_EXPORT_DOCX_STYLE_TEMPLATE`.

To base generated DOCX files on an existing `.docx` document, set
`NOTE_EXPORT_DOCX_TEMPLATE` to that file path. This is useful for organization
headers, footers, margins, and custom Word styles. If `document_template` is set
inside the JSON file, it is used when `NOTE_EXPORT_DOCX_TEMPLATE` is empty.
