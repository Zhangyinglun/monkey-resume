# Recruiter-facing language

Write a coherent professional account of the candidate's real work, tailored to
the JD. The host model owns editing judgment; counts and regular expressions are
not writing-quality verdicts.

## Required writing and wrapping rules

Apply all five rules during writing and independent review. These are delivery
requirements, not optional style suggestions; judge meaning as a model and inspect
actual rendering rather than imposing a verb dictionary or word-count quota.

1. **Fill the last line.** Every bullet's final rendered line must occupy **more
   than 50%** of its available text width, including single-line bullets. Measure
   from the bullet text's left edge (the hanging-indent text edge, excluding the
   marker) to the paragraph's right text boundary, not half the page or half the
   preceding line. Check every bullet in reading order in the direct DOCX view
   and also the PDF when delivering it, not only endings with one to three words.
   At exactly 50% the rule is not met. For each sparse ending, consider both edits:
   add useful supported detail about the same contribution until the final line
   exceeds half width, or shorten the wording enough to remove the final line
   and bring its content onto the preceding line. Choose the clearer, faithful
   version; preserve the contribution, outcome and metric scope. For a sparse
   single-line bullet, consider useful supported detail; shortening cannot remove
   its only line. Keep readable fonts and normal spacing. Padding, extra unrelated
   work and forced line breaks are not fixes. Re-render after editing and check
   every bullet again, including the new final line of a shortened bullet; a
   proposed wording change alone does not establish that the ending now passes.
2. **One contribution plus its result.** Center each bullet on one action or
   coherent contribution and its supported outcome. Include mechanisms only when
   they explain that contribution. Several steps of one recovery workflow can
   belong together; separate unrelated projects, deployment work and patent work
   rather than joining them to save space. A result can be qualitative: never
   invent a metric or causal improvement when none is supported.
3. **Show capability without audit prose.** Keep recruiter-facing text direct and
   remove redundant qualifications. Preserve detailed denominators, exclusions
   and source explanations in evidence/review records instead of copying every
   caveat into the resume. For example, use “automatically mitigated” to distinguish
   automation from later manual work rather than appending “excluding later human
   handling.” List supported skill names such as “Kafka, RocketMQ” without routine
   parenthetical labels such as “(application integration)”; let the experience
   verb explain what the candidate did. Keep the shortest necessary qualifier
   when its removal would materially broaden a metric or responsibility. If a
   claim cannot be made both clear and faithful, choose another supported claim
   or ask for clarification; brevity never upgrades integration to administration.
4. **Lead with a precise, varied action verb.** Start every experience/project
   bullet and every additional sentence within it with a verb describing the candidate's action,
   such as “Built,” “Diagnosed” or “Led.” Attach a result as a clause of that action
   rather than a separate sentence beginning with a metric or “The platform.”
   Headers and skill labels are not experience sentences and need not
   follow this pattern. Choose the right verb, not one from a fixed approved list.
   Before finalizing, list each bullet's location and opening action verb in
   reading order. Compare repeated verbs within each job/project and across the
   whole resume, paying particular attention to adjacent bullets and clusters
   of generic openings such as “Built.” Treat capitalization or tense changes as
   the same verb; an opening modifier does not hide the action verb.
   Rewrite monotonous repetition using the specific evidenced action, such as
   diagnosing, automating or optimizing, while preserving ownership and outcome.
   Recheck the revised wording against evidence and the rendered-line rule.
   Repetition may remain when the same verb is the clearest accurate description
   of distinct work; record that reason in review. Every opening must be checked,
   but verbs need not be unique and there is no fixed frequency limit. Unjustified
   repetitive openings that admit a clear, faithful revision fail this rule;
   forced synonyms or stronger ownership claims are not fixes.
5. **Name recognizable products directly.** Use a well-known product/platform
   name when the evidence establishes it, rather than an anonymous description.
   For example, prefer “Built authentication services for Azure…” over “Built
   authentication services for a platform with millions of enterprise tenants…”
   when Azure is supported; retain scale only if it adds a distinct useful signal.
   An employer name alone does not establish a product. Explain an unfamiliar
   internal system briefly by its purpose: “Built PulseBus, a queue backend for
   authentication events…”; familiar names need no generic explanation.

Use supported scale, reliability work, design choices and technical leadership.
Metrics are useful when they communicate a real result, not obligatory decorations
on every bullet. An overall service SLA is not a component's measured uptime;
diagnostic time is not full incident recovery; evaluation/deployment is not model
training. Preserve those distinctions even when the shorter sentence sounds better.

## Technical resume voice

Retain the useful technical-register and plain-language guidance from the earlier
writing guide alongside the five required rules:

- Use an implied subject, not “I,” “my” or “we”; choose a precise ownership verb
  that distinguishes building, contributing, evaluating and leading. Keep the
  tone technical, objective and concise rather than promotional or conversational.
- Replace “responsible for,” “played a key role in” and “facilitated the
  implementation of” with the actual action. Remove empty praise such as
  “cutting-edge,” “seamless” and “successfully” when it adds no information.
- Prefer a concrete outcome or purpose to an unsupported ending such as
  “significantly enhancing performance” or “ensuring maximum efficiency.” A
  qualitative result is enough when supported; a quantified result is not a quota.
- Vary sentence construction where useful while keeping action-first openings.
  Use direct conjunctions rather than “not only ... but also,” and natural lists
  rather than artificial three-part lists. Avoid repeating the same evidence or
  result in several bullets just to strengthen the impression.
- Preserve canonical technical names and normal punctuation. Use standard
  industry shorthand when the evidence entails it (for example, embedding
  retrieval grounding LLM responses can be described as RAG). Rare synonyms,
  invented errors, slang and detector-evasion tricks do not improve a resume.

Apply these as editing guidance, not keyword bans or mechanical style quotas.
Judge whether the reader can identify the contribution, mechanism and result;
do not flag a standard technical term merely because it appears in a cliché list.

## JD-driven positioning and ordering

Communicate professional positioning through relevant contributions in experience
and supported skills. Follow the display fields in `resume-working-schema.md`.

Keep employers in chronological order; sort related contributions inside each
job. Include relevant transferable work even if its original terminology differs
from the JD. Observability, telemetry pipelines, risk triggers, technical leadership
and internal engineering tools do not become irrelevant simply because they use AI.

## Single-page editing

Remove repetition and shorten secondary detail before shrinking the layout.
Consolidate details of the same contribution, not separate contributions, and
preserve distinct work and the correct metric/project owner.
Document important omissions with specific reasons; reasonable compression need
not reproduce every source fact. There is no fixed word count, bullet count,
skill-group count or approved action-verb dictionary.

Block violations of the five required rules as well as content that changes facts,
unjustifiably loses strong relevant evidence, or prevents the reader understanding
the contribution. Other style improvements remain suggestions. Use exact locations
and explain the unmet rule or factual problem; do not fill the page with weaker
work merely to satisfy wrapping.

## Review

Review against both the original JD and complete valid evidence, including original
excerpts and current corrections. Linked evidence is not necessarily entailed
evidence. Ask for missing facts instead of guessing mechanisms, denominators,
responsibility or completion status. AI-writing detectors are not a QA criterion.
