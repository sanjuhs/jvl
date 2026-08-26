# Editor support

## VS Code

A TextMate grammar for `.jvl` files lives in [`vscode/`](vscode/). It highlights
keywords, statuses, standards of proof, money/date/number literals, predicates,
strings, and comments.

**Try it locally** (no publishing needed):

```bash
# copy the extension into your VS Code extensions folder
cp -r editor-support/vscode ~/.vscode/extensions/jvl-language-0.1.0
# reload VS Code — .jvl files now highlight
```

Or open `editor-support/vscode` in VS Code and press **F5** to launch an
Extension Development Host.

Packaging for the marketplace (`vsce package`) and a language server (hover
status, go-to-source, contradiction squiggles) are on the
[roadmap](../ROADMAP.md).

## Other editors

The grammar is a standard TextMate grammar (`source.jvl`), so it also works with
any editor that consumes TextMate/`tmLanguage` grammars (Sublime Text, Zed via
conversion, etc.). The website's highlighter (`site/app.js`) is a compact
JavaScript reference for the same token rules.
