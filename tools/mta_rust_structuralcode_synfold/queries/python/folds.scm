; Python fold queries for synfold
; These queries identify foldable regions in Python source code

; Function definitions - fold the body
(function_definition
  body: (block) @fold.block)

; Async function definitions
(async_function_definition
  body: (block) @fold.block)

; Class definitions - fold the body
(class_definition
  body: (block) @fold.class)

; Import statements (consecutive imports are grouped by the parser)
(import_statement) @fold.import
(import_from_statement) @fold.import

; Multi-line string literals
(string) @fold.literal

; Multi-line comments
(comment) @fold.comment

; Expression statements containing docstrings
(expression_statement
  (string) @fold.doc)

; List literals
(list) @fold.array

; Tuple literals
(tuple) @fold.array

; Dictionary literals
(dictionary) @fold.object

; Set literals
(set) @fold.object

; Function parameters
(parameters) @fold.arglist

; Chained method calls (detected algorithmically, not via query)
; (call) @fold.chain
