/**
 * hljs-toml.js — highlight.js language definition for TOML (Elastic
 * Security detection rules).
 *
 * highlight.js ships no TOML grammar in this project's bundled
 * /static/js/hljs.min.js (confirmed — a minimal custom build, same
 * situation as hljs-yara.js/hljs-suricata.js). Registered at runtime via
 * hljs.registerLanguage(), not a CodeMirror/Prism mode.
 *
 * Usage:
 *   import tomlLanguage from '/static/js/components/hljs-toml.js'
 *   hljs.registerLanguage('toml', tomlLanguage)
 */
export default function tomlLanguage(hljs) {
    // Triple-quoted multi-line strings (description/note/setup/query in a
    // real Elastic rule are almost always written this way) — must be
    // tried before the single-line string modes below, or the first `"`
    // of `"""` would be misread as opening (and immediately re-closing)
    // an empty single-line string.
    const MULTILINE_BASIC_STRING = {
        className: 'string',
        begin: /"""/,
        end: /"""/,
    }
    const MULTILINE_LITERAL_STRING = {
        className: 'string',
        begin: /'''/,
        end: /'''/,
    }
    const BASIC_STRING = {
        className: 'string',
        begin: /"/,
        end: /"/,
        illegal: '\\n',
        contains: [hljs.BACKSLASH_ESCAPE],
    }
    const LITERAL_STRING = {
        // TOML literal strings are single-quoted and have no escaping at all.
        className: 'string',
        begin: /'/,
        end: /'/,
        illegal: '\\n',
    }

    const DATETIME = {
        // RFC 3339 date/datetime, e.g. 2026-07-14 or 2026-07-14T10:00:00Z
        className: 'number',
        begin: /\b\d{4}-\d{2}-\d{2}(?:[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[Zz]|[+-]\d{2}:\d{2})?)?\b/,
    }

    const NUMBER = {
        className: 'number',
        begin: /\b(?:0x[0-9a-fA-F_]+|0o[0-7_]+|0b[01_]+|[+-]?\d[\d_]*(?:\.\d[\d_]*)?(?:[eE][+-]?\d+)?)\b/,
    }

    const BOOLEAN = {
        className: 'literal',
        begin: /\b(?:true|false)\b/,
    }

    // [table] and [[array.of.tables]] section headers — matched by shape
    // (bracketed bare dotted path) rather than line position, since
    // highlight.js tests `^`/`$` against the remaining unconsumed suffix of
    // the source (not each real line), which swallows the newline before
    // the next token into whichever mode matches next. A real array value
    // never looks like this — it holds quoted strings/numbers/commas, not
    // a single bare dotted identifier — so no anchoring is needed at all.
    const SECTION = {
        className: 'section',
        begin: /\[{1,2}[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*\]{1,2}/,
        relevance: 10,
    }

    // A bare/quoted key immediately followed by '=' — key = value. No
    // line-start anchor for the same reason as SECTION above; safe
    // without one since this only ever matches at the top level (any
    // "word =" sequence inside a string is already consumed whole by the
    // string modes below before this mode ever gets a chance to run).
    const KEY = {
        className: 'attr',
        begin: /[A-Za-z0-9_-]+(?=\s*=)|"[^"]+"(?=\s*=)/,
        relevance: 0,
    }

    return {
        name: 'TOML',
        aliases: ['toml', 'ini'],
        case_insensitive: false,
        contains: [
            hljs.COMMENT('#', '$'),
            SECTION,
            KEY,
            MULTILINE_BASIC_STRING,
            MULTILINE_LITERAL_STRING,
            BASIC_STRING,
            LITERAL_STRING,
            DATETIME,
            NUMBER,
            BOOLEAN,
            {
                className: 'punctuation',
                begin: /[{}\[\],.=]/,
                relevance: 0,
            },
        ],
    }
}
