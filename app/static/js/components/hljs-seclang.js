/**
 * hljs-seclang.js — highlight.js language definition for ModSecurity / Coraza SecLang,
 * the language of the OWASP Core Rule Set (CRS) rules.
 *
 * highlight.js ships no SecLang grammar, and the bundled /static/js/hljs.min.js is a minimal
 * custom build: same approach as hljs-yara.js / hljs-suricata.js, registered at runtime.
 *
 *   SecRule REQUEST_HEADERS:User-Agent|!ARGS:foo "@rx (?i)nikto" \
 *       "id:913100,phase:1,block,msg:'Scanner found',tag:'attack-reputation-scanner',setvar:'tx.score=+%{tx.critical_anomaly_score}'"
 *
 * Usage:
 *   import seclangLanguage from '/static/js/components/hljs-seclang.js'
 *   hljs.registerLanguage('seclang', seclangLanguage)
 */
export default function seclangLanguage(hljs) {
    // %{tx.anomaly_score} / %{MATCHED_VAR}: macro expansion, inside strings and values
    const MACRO = { className: 'template-variable', begin: /%\{[^}\n]+\}/ }

    // inside the operator string: @rx, @pm, @lt…, with an optional leading negation
    const OPERATOR = { className: 'keyword', begin: /!?@[a-zA-Z]+/ }

    // inside the actions string: id:…, phase:…, msg:'…', setvar:'…', block / pass / deny…
    const ACTION_VALUE = {
        className: 'string', begin: /'/, end: /'/, contains: [hljs.BACKSLASH_ESCAPE, MACRO],
    }
    const ACTION_KEY = { className: 'attr', begin: /\b[a-zA-Z][a-zA-Z0-9_]*(?=\s*:)/ }
    const DISRUPTIVE = {
        className: 'built_in',
        begin: /\b(?:block|pass|deny|drop|allow|redirect|proxy|chain|nolog|log|auditlog|noauditlog|capture|multiMatch|t:none)\b/,
    }

    const STRING = {
        className: 'string', begin: /"/, end: /"/,
        contains: [hljs.BACKSLASH_ESCAPE, MACRO, OPERATOR, ACTION_VALUE, ACTION_KEY, DISRUPTIVE],
    }

    return {
        name: 'SecLang (ModSecurity / OWASP CRS)',
        aliases: ['crs', 'modsecurity', 'modsec'],
        case_insensitive: false,
        contains: [
            hljs.COMMENT('#', '$'),
            // directives: SecRule, SecAction, SecMarker, SecRuleUpdateTargetById…
            { className: 'keyword', begin: /\bSec[A-Za-z]+\b/ },
            STRING,
            MACRO,
            // collections and variables: REQUEST_HEADERS:User-Agent, TX:DETECTION_PARANOIA_LEVEL, &ARGS, !ARGS:foo
            {
                className: 'variable',
                begin: /[!&]?\b[A-Z][A-Z0-9_]+(?::[^\s|"]+)?/,
                relevance: 0,
            },
            { className: 'operator', begin: /\|/, relevance: 0 },
            // a rule continued on the next line
            { className: 'meta', begin: /\\$/, relevance: 0 },
            hljs.C_NUMBER_MODE,
        ],
    }
}
