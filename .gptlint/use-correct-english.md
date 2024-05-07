---
fixable: false
tags: [best practices]
---

# Docs should use correct English spelling and grammar

All comments and documentation should use correct English spelling and grammar. Obvious spelling errors should be repoted as violations.

This rule applies to code comments, JSDoc comments, and markdown documentation.

## Caveats

This rule does _not_ apply to code identifiers (variable names, function names, type names, etc) which often use shorthand.

This rule also does not apply to `TODO` comments.

### Bad

```md
This is a violation becuse it includs spelling errors.
```

```md
This example uses broken english grammar because bad.
```
