import { EditorView, basicSetup } from 'codemirror'
import { EditorState } from '@codemirror/state'
import { javascript } from '@codemirror/lang-javascript'
import { html } from '@codemirror/lang-html'
import { markdown } from '@codemirror/lang-markdown'

// Export as global variable
window.CodeMirrorBundle = {
  EditorView,
  EditorState,
  basicSetup,
  languages: {
    javascript,
    html,
    markdown
  }
}