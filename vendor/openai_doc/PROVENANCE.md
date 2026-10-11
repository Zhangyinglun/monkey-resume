# OpenAI public DOCX visual QA tool

Unmodified public `openai/skills` files, pinned to commit
`45d05d75363abf13f99d09e899d61e07b8010685`:

- https://github.com/openai/skills/blob/45d05d75363abf13f99d09e899d61e07b8010685/skills/.curated/doc/scripts/render_docx.py
- https://github.com/openai/skills/blob/45d05d75363abf13f99d09e899d61e07b8010685/skills/.curated/doc/LICENSE.txt

Apache-2.0; see LICENSE.txt. No NOTICE file existed in that skill tree.
This historical public script is pinned, not represented as the latest
maintained OpenAI skill.
No private host skill instructions are redistributed.

SHA-256 render_docx.py: 52b3c3158913ebcad2ada7b8193970b70453239e255054aa2d60c1683af08751
SHA-256 LICENSE.txt: 4dd13869245e356246a5b770723247bbb80a8f07a181d1d3d873a1734297cdb9

The script is available for independent DOCX visual QA. Its optional ODT
fallback and unbounded subprocess calls are not used for publication: the
package's bounded direct LibreOffice export refuses failed/stale exports.
