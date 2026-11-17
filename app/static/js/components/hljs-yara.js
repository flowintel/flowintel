/**
 * hljs-yara.js — highlight.js language definition for YARA rules.
 *
 * highlight.js ships no official YARA grammar (confirmed against the bundled
 * /static/js/hljs.min.js — it's a minimal custom build). This project uses
 * highlight.js exclusively (no CodeMirror anywhere in the codebase), so this
 * follows highlight.js's own language-definition API — registered at runtime
 * via hljs.registerLanguage(), not a CodeMirror mode.
 *
 * Usage:
 *   import yaraLanguage from '/static/js/components/hljs-yara.js'
 *   hljs.registerLanguage('yara', yaraLanguage)
 */
export default function yaraLanguage(hljs) {
    const KEYWORDS = {
        keyword:
            'rule private global import include meta strings condition ' +
            'all any of them for in at entrypoint filesize contains ' +
            'startswith endswith icontains istartswith iendswith matches ' +
            'wide ascii nocase fullword base64 base64wide xor and or not defined',
        literal: 'true false',
    }

    const HEX_STRING = {
        // { 4D 5A ?? ?? [4-8] E8 } — wildcard/jump bytes and nested comments
        className: 'string',
        begin: /\{/,
        end: /\}/,
        contains: [
            hljs.COMMENT('//', '$'),
            hljs.COMMENT('/\\*', '\\*/'),
        ],
        relevance: 0,
    }

    const IDENTIFIER = {
        // string/rule references: $a, $string1, #a, @a, !a, $
        className: 'variable',
        begin: /[$#@!]\w*/,
    }

    const RULE_TITLE = {
        className: 'title.function',
        begin: /(?<=\brule\s)[a-zA-Z_]\w*/,
        relevance: 0,
    }

    return {
        name: 'YARA',
        aliases: ['yar'],
        case_insensitive: false,
        keywords: KEYWORDS,
        contains: [
            hljs.COMMENT('//', '$'),
            hljs.COMMENT('/\\*', '\\*/'),
            hljs.QUOTE_STRING_MODE,
            HEX_STRING,
            IDENTIFIER,
            RULE_TITLE,
            hljs.C_NUMBER_MODE,
        ],
    }
}
