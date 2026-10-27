---
name: plain-technical-communication
description: "Write, review, or rewrite technical communication for first-read comprehension without losing precision. Use for engineering documents, requirements, reviews, issues and PR descriptions, API documentation, code explanations, and substantive technical chat; not as a separate prose audit for routine coding tasks."
---

# Plain Technical Communication

> Put complexity in the engineering, not in the language used to describe it.

This skill follows the requested principles inspired by NASA plain-language
guidance, ECSS requirements-writing guidance, and the SpaceX-style preference
for fewer unnecessary acronyms and less internal jargon. It is a practical
writing guide, not a claim of compliance with an organizational standard.

## Scope

Apply to design docs, RFCs, implementation plans, code review comments, GitHub
issues and PR descriptions, requirements, incident reports, architecture
explanations, API documentation, comments explaining complex code, and technical
Slack or chat messages when clarity work is useful. Scale the effort to the
artifact; a chat message does not need a document-review ceremony.

Respect the requested audience, format, and repository conventions. Improve
language within the task's scope; do not change engineering decisions or turn
a writing request into permission to publish or send the result.

When editing existing repository Markdown, preserve its source formatting,
including padded tables, unless the user requests a formatting change or the
repository's formatter requires one. Identical rendered HTML is not by itself
a reason to reformat otherwise unchanged content.

## Principles

1. **Prefer common words.** Use the simplest word that preserves the technical
   meaning: `use` over `utilize`, `before` over `prior to`, and `because` over
   `due to the fact that`. Prefer `start` over `initialize` unless initialization
   has a specific technical meaning. Do not inflate a simple idea.

2. **Minimize jargon.** Use ordinary language when it is equally precise. Keep
   specialized terminology when it carries important technical meaning.

3. **Minimize acronyms.** Do not invent abbreviations merely to shorten names.
   Familiar acronyms such as HTTP, CPU, API, RPC, SQL, and TLS can help an
   engineering audience. Define unfamiliar acronyms on first use. Prefer a
   short descriptive name over a new acronym. Apply this SpaceX-style test:
   “Does this abbreviation reduce cognitive load, or does it make the reader
   decode another piece of vocabulary?” Treat this as a heuristic, not an
   attributed verbatim quotation.

4. **Avoid private vocabulary.** Do not assume readers know undocumented team
   terms. Define necessary project-specific concepts before relying on them.
   Use one consistent name for each concept rather than stylistic synonyms.

5. **Put one idea in each statement.** Separate requirements, arguments, or
   explanations that can be understood or verified independently. Preserve
   the conditions and relationships that connect them.

6. **Prefer short, direct sentences.** Reduce nested clauses and long noun
   phrases. Put important information early and split sentences when it helps
   comprehension. Do not impose a mechanical sentence-length limit.

7. **Name the actor.** Prefer “The scheduler retries the action three times” to
   “The action will be retried three times by the scheduler.” Passive voice is
   acceptable when the actor is genuinely irrelevant; do not invent an actor.

8. **Be precise, not merely simple.** Preserve scope, conditions, exceptions,
   quantities, units, guarantees, and uncertainty. “The client retries
   idempotent requests after a transport failure” must not become “The client
   tries again when something goes wrong.” Preserve code identifiers, API
   names, and literal protocol values; explain them rather than renaming them.

9. **Make requirements unambiguous.** Aim for one subject, one required
   behavior, defined conditions, and observable or verifiable success criteria.
   Avoid undefined `fast`, `efficient`, `reasonable`, `usually`, `appropriate`,
   `user-friendly`, or `robust`. Preserve the document's normative conventions
   and obligation strength: changing `should` to `must` or `shall` is not a
   stylistic edit. Never invent acceptance thresholds to fix vague prose;
   flag the missing decision or label a suggested criterion as a proposal.

10. **Make statements independently understandable.** Give an engineer outside
    the original discussion enough context to reach the same interpretation.
    Use explicit referents and useful cross-references instead of tribal
    knowledge. Independent statements need not repeat the entire document.

11. **Separate claim types.** Make existing behavior, measured results,
    decisions, assumptions, proposals, requirements, and unresolved questions
    distinguishable through wording or labels. Do not turn an assumption into
    a fact, correlation into causation, or a proposal into an accepted decision.

12. **Describe concrete mechanisms.** Prefer “Workers keep downloaded
    content-addressable storage (CAS) blobs on local SSD and evict the least
    recently used blobs when the disk reaches 80% capacity” to “Workers
    implement intelligent local cache management,” when those details are
    established. Do not supply a mechanism the source does not support.

13. **Remove unnecessary words.** Delete repetition, filler, and qualifiers
    that do not change understanding or decisions. Keep qualifications that
    limit a claim accurately.

14. **Preserve useful technical terminology.** Keep concepts such as Merkle
    tree, content-addressable storage, cgroup, inode, quorum, write-ahead log
    (WAL), and linearizability when they are correct. Explain them when the
    audience may not know them; do not replace precision with vague wording.

15. **Optimize for first-read comprehension.** Organize context so readers do
    not have to reread a sentence to understand its basic meaning. Give enough
    framing before a conclusion that depends on unfamiliar facts. A clear
    summary may still lead; do not bury the main point in supporting detail.

## Writing Mode

- Infer the audience, purpose, and required action from the task. Ask only if
  missing context materially affects the content.
- Write directly and concisely from the start. Organize from the high-level
  concept to relevant detail, with focused, single-topic paragraphs.
- For technical proposals, start with the problem and its impact before the
  proposed solution. Group related use cases and explain dependencies, then
  present the proposed change, tradeoffs, and open questions. Adapt this shape
  to the requested format; a concise summary may still lead.
- For conference proposals, keep the abstract short and focused on the
  audience's problem, mechanism, and takeaways. Put adoption evidence and
  detailed source qualifications in supporting notes. Naming the speaker's
  employer or a demonstration tool should not turn the technical pitch into
  a product pitch unless that is the requested purpose.
- Introduce terminology before using it heavily. For readers outside the
  project's ecosystem, briefly explain necessary concepts and link their
  authoritative overview or core documentation rather than assuming familiarity.
  Use concrete examples when they help explain an abstract mechanism.
- Keep setup and development guides focused on required setup, use, and
  compatibility information. Describe the fields and actions the operator
  actually controls. If a default mapping or integration manages internal IDs
  automatically, say what to retain rather than making those IDs sound like
  values to look up or enter. Keep protocol details for API documentation or
  troubleshooting when they affect the reader's task. Put experiment protocols,
  parser details, and internal benchmark procedures in a task report or
  dedicated reference unless needed to use or troubleshoot the setup.
- For commands handed to the user across hosts, label where each command runs
  (controlling machine or remote host). Verify the remote login user, SSH alias,
  and host-local paths from available configuration or user-provided facts;
  mark unresolved values as placeholders instead of guessing. Distinguish a
  one-time interactive setup step from subsequent noninteractive commands.
- Distinguish what is known from what is assumed, proposed, or unresolved.
- For external or privacy-minimized technical handoffs, omit internal
  infrastructure details and private identifiers unless the task authorizes
  sharing them with that audience. Keep relevant public code references and
  deployment guidance; do not turn internal tuning values into claimed defaults
  or universal recommendations.
- For requirements, use a shape such as: “Under [conditions], [subject] must
  [behavior] with [verifiable criterion].” Follow the document's chosen modal
  convention. Resolve or flag missing criteria rather than making them up.
- Return the requested artifact, not a narration of these internal checks.

## Review Mode

1. Read for the intended claim and audience before editing. Identify wording
   that adds cognitive load, and identify ambiguity separately from style.
2. Look specifically for unnecessary or undefined acronyms, invented terms,
   vague requirements, multiple requirements in one sentence, long noun
   phrases, excessive passive voice, unnecessary abstraction or qualifiers,
   implicit context, ambiguous `it`/`this`/`they`, excessively long sentences,
   conclusions lacking necessary context, and impressive-sounding language
   that communicates less than ordinary words.
3. Identify terminology to remove, rename, or define. Separate unfamiliar but
   necessary concepts from jargon that contributes no meaning.
4. Rewrite problematic passages while preserving every technically meaningful
   distinction and the author's intended claim. If two materially different
   interpretations remain possible, flag them and ask a focused question or
   offer explicitly conditional alternatives; do not silently choose one.
5. Compare the rewrite with the source for changed actors, conditions,
   quantities, negation, exceptions, obligation strength, and confidence.
   Flag misleading claims or contradictions separately from prose edits.

For selected passages, use this format when useful:

**Original** <text>

**Problem** <short explanation of ambiguity or unnecessary complexity>

**Rewrite** <improved text>

Do not apply the format mechanically to every sentence. For large documents,
produce a cleaned-up version and summarize the main recurring issues and any
unresolved ambiguity. If the user requests review only, provide findings and
suggested passages without editing the source artifact.

## Iterating on technical correspondence

- When the user asks for copy-pastable Markdown, or the draft is intended to be
  pasted into a Markdown editor such as GitHub's issue body, return one
  self-contained fenced Markdown artifact so copying preserves headings, lists,
  inline code, and links. Honor an explicitly requested different format or
  direct-editor workflow. Incorporate follow-up edits into the complete artifact,
  retaining accepted sections so the user does not have to combine fragments.
- When editing the user's draft, preserve their tone, vocabulary, and structure
  (such as Q&A) unless they ask for a rewrite. Make the necessary technical
  corrections without replacing their voice with a more formal one.
- Prefer short sentences to semicolon chains. Keep closely related clauses
  together when splitting them would produce choppy prose or hide the causal
  relationship.
- State a limitation where it explains the relevant claim; do not repeat the
  same "this does not fix the issue" caveat in every contextual paragraph.
  Keep qualifications that distinguish genuinely different limits.
- Before calling a provider draft the latest version, compare its read-back
  contents with the revisions agreed in the conversation. If it is stale,
  identify the mismatch rather than silently dropping agreed edits.
- Once the user moves iteration to a local file, treat that file as the working
  draft. Do not synchronize it back to the provider without instruction. Keep
  quoted history only when requested or useful to the requested artifact.
- For local Markdown correspondence, default to one sentence per source line
  with blank lines between paragraphs, unless the user chooses another format.
  This does not change commit-message wrapping or other artifact conventions.

## Examples

These rewrites assume the stated mechanisms and acronym meanings are known.
Numerical criteria illustrate a completed requirement; they are not values to
invent during an edit. In examples 2 and 3, remote build execution (RBE) and
content-addressable storage (CAS) have already been introduced to the audience.

### 1. Common words instead of inflated language

**Original** The AC subsystem utilizes a sophisticated eviction methodology in
order to facilitate the optimization of storage utilization.

**Rewrite** The action cache evicts old entries when it needs disk space.

### 2. Remove unnecessary acronyms and abstraction

**Original** The RBE GC will leverage an LRU-based methodology for the purpose
of facilitating blob reclamation.

**Rewrite** The RBE garbage collector deletes the least recently used blobs first.

This rewrite assumes established behavior. If the original describes a future
proposal, write “We propose that the RBE garbage collector delete the least
recently used blobs first.”

### 3. Explain the action directly

**Original** Upon receipt of a CAS miss notification, the BB executor will
initiate a blob retrieval operation from the upstream.

**Rewrite (if the notification represents a local miss and the upstream is a
cache)** When the executor misses a CAS blob locally, it downloads the blob
from the upstream cache.

Otherwise preserve the known mechanism: “When the executor receives a CAS miss
notification, it starts retrieving the blob from upstream.”

### 4. Define verifiable requirements

**Original** The system should efficiently support large repositories and
provide good performance.

**Proposed requirement (requires agreement on scope, threshold, and obligation)**
For repositories containing up to 5 million files, the server must return the
initial file listing within 2 seconds at the 95th percentile.

This is a requirements clarification only if the owner has chosen that scope,
threshold, and obligation. Otherwise present it as a proposed requirement and
flag the missing workload and measurement conditions. Similarly, “The server
must respond within 500 ms at the 99th percentile under a load of 1,000 requests
per second” is more verifiable than “The server should respond quickly under
heavy load,” but it needs an agreed request mix and measurement conditions.

### 5. Replace private vocabulary

**Original** The DCM communicates with the BFC to initiate PRS following an HCE.

**Rewrite** The disk manager asks the cache controller to start recovery after
a host crash.

Use this rewrite only if these are the intended meanings. If the acronyms are
established domain terminology, define them before using them instead of
guessing their expansions or deleting useful distinctions.

### 6. Expose an imprecise claim

**Original** The cache is immutable. It periodically modifies metadata
associated with entries to track access time.

**Rewrite (if blob contents are immutable, the server owns metadata updates,
and only the immutability boundary needs explanation)** Cached blob contents
are immutable. The server can still update metadata such as the last-access time.

This clarifies the scope of immutability if only blob contents are immutable.
If periodic updates are part of the intended claim, retain that behavior:
“Cached blob contents are immutable. The server periodically updates entry
metadata to track the last-access time.” Confirm the actor if it is not known.

## Guardrails

Do not blindly shorten everything, remove necessary qualifications, ban all
acronyms or passive voice, avoid sophisticated concepts, write as if engineers
were children, replace precise terms with vague everyday language, or sacrifice
correctness for readability. The goal is lower cognitive load, not fewer words
at any cost.

## Final Internal Checklist

- Can an engineer outside the immediate team understand this?
- Is every acronym useful and defined when necessary?
- Did we invent terminology we do not need?
- Could any sentence be interpreted in two materially different ways?
- Does each requirement describe one independently verifiable behavior?
- Are vague adjectives replaced with measurable properties where appropriate?
- Can any words be removed without losing meaning?
- Did simplification accidentally remove an important technical distinction?
- Can the reader understand it correctly on the first read?
