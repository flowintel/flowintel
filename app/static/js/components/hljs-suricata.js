/**
 * hljs-suricata.js — highlight.js language definition for Suricata rules.
 *
 * highlight.js ships no official Suricata grammar (confirmed against the bundled
 * /static/js/hljs.min.js — it's a minimal custom build). Same approach as
 * hljs-yara.js: this project uses highlight.js exclusively, so this follows
 * highlight.js's own language-definition API — registered at runtime via
 * hljs.registerLanguage(), not a CodeMirror/Prism mode.
 *
 * Usage:
 *   import suricataLanguage from '/static/js/components/hljs-suricata.js'
 *   hljs.registerLanguage('suricata', suricataLanguage)
 */
export default function suricataLanguage(hljs) {
    const ACTIONS = ['pass', 'drop', 'reject', 'alert']

    const PROTOCOLS = [
        'any', 'tcp', 'udp', 'icmp', 'icmp4', 'icmp6', 'ip', 'ip4', 'ip6',
        'http', 'http2', 'ftp', 'tls', 'ssl', 'smb', 'dns', 'dcerpc', 'ssh',
        'smtp', 'imap', 'msn', 'modbus', 'dnp3', 'enip', 'nfs', 'ikev2',
        'krb5', 'ntp', 'dhcp', 'rdp', 'rfb', 'sip', 'snmp', 'mqtt',
    ]

    const VARIABLE = {
        // rule-var references in the header: $HOME_NET, $EXTERNAL_NET, $HTTP_PORTS
        className: 'variable',
        begin: /\$[A-Za-z_][A-Za-z0-9_]*/,
    }

    const DIRECTION = {
        // traffic direction operators: -> and <>
        className: 'operator',
        begin: /<>|->/,
    }

    const OPTION_KEY = {
        // rule-option keys, only when followed by ':' — msg: sid: rev: content: classtype:
        className: 'attr',
        begin: /[a-zA-Z_][a-zA-Z0-9_.]*(?=\s*:)/,
    }

    return {
        name: 'Suricata',
        aliases: ['suricata-rule'],
        case_insensitive: false,
        contains: [
            hljs.COMMENT('#', '$'),
            hljs.QUOTE_STRING_MODE,
            VARIABLE,
            DIRECTION,
            {
                className: 'keyword',
                begin: '\\b(?:' + ACTIONS.join('|') + ')\\b',
            },
            {
                className: 'built_in',
                begin: '\\b(?:' + PROTOCOLS.join('|') + ')\\b',
            },
            OPTION_KEY,
            hljs.C_NUMBER_MODE,
            {
                className: 'punctuation',
                begin: /[{}[\];(),.:]/,
                relevance: 0,
            },
        ],
    }
}
