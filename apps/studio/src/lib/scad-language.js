/**
 * OpenSCAD language definition for Monaco Editor.
 * Registers syntax highlighting, keywords, builtins, and basic autocomplete.
 */

export const SCAD_LANGUAGE_ID = 'openscad'

export function registerScadLanguage(monaco) {
  if (monaco.languages.getLanguages().some(l => l.id === SCAD_LANGUAGE_ID)) {
    return // Already registered
  }

  monaco.languages.register({ id: SCAD_LANGUAGE_ID, extensions: ['.scad'] })

  monaco.languages.setMonarchTokensProvider(SCAD_LANGUAGE_ID, {
    keywords: [
      'module', 'function', 'if', 'else', 'for', 'let', 'each',
      'include', 'use', 'true', 'false', 'undef',
    ],
    builtins: [
      // 3D primitives
      'cube', 'sphere', 'cylinder', 'polyhedron',
      // 2D primitives
      'circle', 'square', 'polygon', 'text',
      // Transforms
      'translate', 'rotate', 'scale', 'mirror', 'multmatrix',
      'color', 'offset', 'hull', 'minkowski', 'resize',
      // Boolean
      'union', 'difference', 'intersection',
      // Extrusion
      'linear_extrude', 'rotate_extrude',
      // Other
      'render', 'surface', 'projection', 'import', 'children',
      // Math
      'abs', 'sign', 'sin', 'cos', 'tan', 'acos', 'asin', 'atan', 'atan2',
      'floor', 'round', 'ceil', 'ln', 'log', 'pow', 'sqrt', 'exp',
      'min', 'max', 'len', 'norm', 'cross',
      // String/list
      'str', 'chr', 'ord', 'concat', 'lookup', 'search',
      // Special variables
      '$fn', '$fa', '$fs', '$t', '$vpr', '$vpt', '$vpd', '$vpf',
      '$children', '$preview',
    ],
    operators: [
      '=', '>', '<', '!', '~', '?', ':',
      '==', '<=', '>=', '!=', '&&', '||',
      '+', '-', '*', '/', '%', '^',
    ],
    symbols: /[=><!~?:&|+\-*/^%]+/,

    tokenizer: {
      root: [
        // Comments
        [/\/\/.*$/, 'comment'],
        [/\/\*/, 'comment', '@comment'],

        // Strings
        [/"([^"\\]|\\.)*$/, 'string.invalid'],
        [/"/, 'string', '@string'],

        // Numbers
        [/\d*\.\d+([eE][-+]?\d+)?/, 'number.float'],
        [/\d+/, 'number'],

        // Special variables
        [/\$[a-zA-Z_]\w*/, 'variable.predefined'],

        // Identifiers
        [/[a-zA-Z_]\w*/, {
          cases: {
            '@keywords': 'keyword',
            '@builtins': 'type.identifier',
            '@default': 'identifier',
          },
        }],

        // Operators
        [/@symbols/, {
          cases: {
            '@operators': 'operator',
            '@default': '',
          },
        }],

        // Brackets
        [/[{}()[\]]/, '@brackets'],
        [/[;,.]/, 'delimiter'],
      ],

      comment: [
        [/[^/*]+/, 'comment'],
        [/\*\//, 'comment', '@pop'],
        [/[/*]/, 'comment'],
      ],

      string: [
        [/[^\\"]+/, 'string'],
        [/\\./, 'string.escape'],
        [/"/, 'string', '@pop'],
      ],
    },
  })

  // Basic completions
  const allKeywords = [
    'module', 'function', 'if', 'else', 'for', 'let', 'each',
    'include', 'use', 'true', 'false', 'undef',
    'cube', 'sphere', 'cylinder', 'polyhedron',
    'circle', 'square', 'polygon', 'text',
    'translate', 'rotate', 'scale', 'mirror', 'color',
    'union', 'difference', 'intersection',
    'linear_extrude', 'rotate_extrude',
    'hull', 'minkowski', 'offset', 'resize',
    'render', 'import', 'children',
  ]

  monaco.languages.registerCompletionItemProvider(SCAD_LANGUAGE_ID, {
    provideCompletionItems: (model, position) => {
      const word = model.getWordUntilPosition(position)
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      }
      return {
        suggestions: allKeywords.map(kw => ({
          label: kw,
          kind: monaco.languages.CompletionItemKind.Keyword,
          insertText: kw,
          range,
        })),
      }
    },
  })
}
