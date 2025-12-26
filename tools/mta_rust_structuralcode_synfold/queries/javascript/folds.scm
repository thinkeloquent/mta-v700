; JavaScript fold queries for synfold
; These queries identify foldable regions in JavaScript source code

; Function declarations - fold the body
(function_declaration
  body: (statement_block) @fold.block)

; Function expressions
(function
  body: (statement_block) @fold.block)

; Arrow functions with block body
(arrow_function
  body: (statement_block) @fold.block)

; Generator functions
(generator_function_declaration
  body: (statement_block) @fold.block)

(generator_function
  body: (statement_block) @fold.block)

; Method definitions
(method_definition
  body: (statement_block) @fold.block)

; Class declarations - fold the body
(class_declaration
  body: (class_body) @fold.class)

; Class expressions
(class
  body: (class_body) @fold.class)

; Import statements
(import_statement) @fold.import

; Array literals
(array) @fold.array

; Object literals
(object) @fold.object

; Template strings
(template_string) @fold.literal

; Regular strings (multi-line)
(string) @fold.literal

; Block comments
(comment) @fold.comment

; JSDoc comments (detected by content starting with /**)
(comment) @fold.doc

; Formal parameters
(formal_parameters) @fold.arglist

; Arguments in call expressions
(arguments) @fold.arglist

; Switch statement body
(switch_body) @fold.block

; Try-catch blocks
(try_statement
  body: (statement_block) @fold.block)

(catch_clause
  body: (statement_block) @fold.block)

(finally_clause
  body: (statement_block) @fold.block)
