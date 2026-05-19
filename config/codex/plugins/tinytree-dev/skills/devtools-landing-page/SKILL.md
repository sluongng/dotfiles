---
name: devtools-landing-page
description: Design and review landing pages for early-stage B2B devtools, developer infrastructure, AI developer tools, and technical SaaS startups. Use when Codex is asked to create, redesign, critique, or review changes to a startup homepage, launch page, hero section, messaging hierarchy, product-proof section, CTA strategy, visual direction, responsive implementation, or conversion-focused landing page for developers, platform teams, security teams, product engineers, or technical buyers.
---

# Devtools Landing Page

## Workflow

1. Establish the wedge: target user, technical workflow, buyer, buying motion, launch stage, available proof, and the one action the page should drive.
2. Inspect the actual artifact before judging it: source files, design system, assets, screenshots, local browser, copy, analytics hooks, and responsive behavior when available.
3. Load `references/devtools-b2b-style-notes.md` when choosing a visual direction, comparing against current devtools/B2B patterns, or reviewing whether a page feels credible and current.
4. Choose one style lane that matches the company: precision/minimal, code-native, enterprise proof, opinionated/playful, or component/product-suite.
5. Design or review top-down: first viewport, product proof, credibility, section pacing, CTAs, implementation quality, and mobile fit.
6. Validate with screenshots or a local browser when editing frontend code. Check desktop and mobile for text overflow, incoherent overlap, non-loading media, empty decorative visuals, and CTA visibility.

## Design Rules

- Lead with the specific workflow outcome, not the category. Prefer "Review agent PRs before merge" over "AI-powered review automation".
- Show real product proof in the first viewport: UI screenshot, terminal command, code sample, trace, architecture flow, eval, benchmark, or short interactive demo.
- Keep early-stage pages narrow. Use one primary persona and one primary CTA unless the startup truly supports both product-led and sales-led motions.
- Pair developer-native proof with buyer-safe reassurance: docs, SDKs, install commands, GitHub stars, changelog, security posture, compliance, integration ecosystem, cost, reliability, or customer logos.
- Use trust only when it is real. Do not invent logos, quotes, usage metrics, compliance claims, or benchmark numbers.
- Use AI language only when the page explains the concrete job AI performs, the human control point, and the failure mode it reduces.
- Make the visual system feel technical through product surfaces, dense but legible UI, code, diagrams, and measured motion. Avoid generic SaaS blobs, oversized decorative cards, and vague gradient hero art.
- Make the first viewport practical: clear H1, concrete subcopy, product visual, primary CTA, secondary docs/demo CTA, and at least a hint of the next section on common desktop and mobile viewports.

## Review Routine

When reviewing a landing page change, lead with findings ordered by severity and cite files/lines or screenshots when possible.

- **Blocker**: misleading claims, fake proof, missing actionable CTA, broken/mobile-overlapping first viewport, unreadable text, inaccessible primary action, or product media that fails to load.
- **Major**: generic positioning, unclear ICP, product not visible above the fold, too many equal-weight CTAs, unsupported enterprise/security claims, weak proof for a paid B2B buyer, or visual style copied too closely from a competitor.
- **Minor**: section rhythm, microcopy, CTA labels, logo density, animation restraint, contrast polish, image cropping, or responsive spacing.

Check these questions before signing off:

- Can a technical visitor tell what it does, who it is for, and what changes in their workflow within 5 seconds?
- Does the first screen show the product or a concrete technical artifact?
- Is there a credible next action for both an individual developer and a B2B evaluator?
- Are claims backed by visible proof close to the claim?
- Does the mobile layout preserve hierarchy without text overflow or card-on-card clutter?
- Does the page balance developer taste with the buyer's need for security, governance, reliability, and ROI?

## Output Shape

- For design work, provide a compact page plan with positioning, visual lane, first viewport composition, section sequence, CTA strategy, and key copy.
- For implementation work, make scoped code changes that follow the existing app conventions and verify the result.
- For reviews, list findings first, then open questions, then a brief summary. Avoid rewriting the whole page unless the user asks for redesign work.
