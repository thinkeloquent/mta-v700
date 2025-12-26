; TypeScript fold queries for synfold
; Extends JavaScript queries with TypeScript-specific constructs

; Include all JavaScript folds (TypeScript is a superset)
; (see javascript/folds.scm)

; Interface declarations
(interface_declaration
  body: (object_type) @fold.class)

; Type alias declarations with object types
(type_alias_declaration
  value: (object_type) @fold.class)

; Enum declarations
(enum_declaration
  body: (enum_body) @fold.class)

; Namespace declarations
(namespace_declaration
  body: (statement_block) @fold.block)

; Module declarations
(module_declaration
  body: (statement_block) @fold.block)

; Abstract class declarations
(abstract_class_declaration
  body: (class_body) @fold.class)

; Function declarations with type annotations
(function_declaration
  body: (statement_block) @fold.block)

; Arrow functions
(arrow_function
  body: (statement_block) @fold.block)

; Method signatures in interfaces
(method_signature
  parameters: (formal_parameters) @fold.arglist)

; Call signatures
(call_signature
  parameters: (formal_parameters) @fold.arglist)

; Type parameters (generics)
(type_parameters) @fold.arglist

; Mapped types
(mapped_type_clause) @fold.object

; Conditional types (complex)
(conditional_type) @fold.literal
