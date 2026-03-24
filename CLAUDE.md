# Idea-to-Website Generator

## How This Works

When a user messages an idea (product, service, course, coaching program, digital product, membership, etc.), automatically run the **FULL GENERATION WORKFLOW** below. Do NOT ask clarifying questions — make smart assumptions and generate everything. The user can refine later.

## FULL GENERATION WORKFLOW

Every time the user sends a new idea, generate ALL of the following in order. Create a new folder inside `generated/` named with a slugified version of the idea (e.g., `generated/90-day-fitness-transformation/`).

### Step 1: Audience Research (`audience.md`)

Identify the **single best buyer persona** — the person most likely to buy this RIGHT NOW. Include:

- **Who they are**: Age range, gender (if relevant), role/identity, income level
- **Current situation**: What they're dealing with right now that makes this relevant
- **Pain points**: The 3-5 specific frustrations they have (use their language, not marketing jargon)
- **Failed solutions**: What they've already tried that didn't work
- **Dream outcome**: What they actually want (the transformation, not the product)
- **Buying triggers**: What would make them buy TODAY vs "think about it"
- **Where they hang out online**: Specific platforms, groups, hashtags, influencers they follow
- **Objections**: The 3-5 reasons they'd hesitate to buy, and how to overcome each

### Step 2: Offer Strategy (`offer.md`)

Define the offer clearly:

- **Offer name**: A compelling name (not generic)
- **One-liner**: A single sentence that makes someone say "tell me more"
- **Price point recommendation**: With reasoning
- **What's included**: Bullet list of deliverables
- **Bonuses**: 2-3 bonuses that increase perceived value
- **Guarantee**: A specific, bold guarantee
- **Urgency/scarcity mechanism**: Why they should buy now

### Step 3: Sales Page (`sales-page.html`)

Generate a complete, styled, single-file HTML sales page. Use inline CSS and embedded styles. The page must:

- Be fully responsive (mobile-first)
- Use a modern, clean design with good typography
- Include these sections in order:
  1. **Hero**: Headline (speaks to the transformation), subheadline, CTA button
  2. **Problem agitation**: "If you're like most [audience]..." — paint the pain
  3. **Failed solutions**: "You've probably tried..." — show you understand
  4. **The shift**: Introduce the new way / mechanism
  5. **Introduce the offer**: What they get, with benefit-driven bullets
  6. **Social proof section**: Placeholder testimonial blocks (marked as [REPLACE WITH REAL TESTIMONIAL])
  7. **Bonuses**: Each bonus with perceived value
  8. **Price reveal + anchor**: Show value stack, then reveal price
  9. **Guarantee**: Risk reversal section
  10. **FAQ**: 6-8 common objections reframed as questions
  11. **Final CTA**: Urgency-driven closing section
  12. **Footer**: Simple footer

Design guidelines:
- Use a color scheme appropriate to the offer's energy (bold for high-ticket, calm for wellness, etc.)
- CTA buttons should be high contrast, large, and repeated 3+ times throughout the page
- Use proper heading hierarchy (H1, H2, H3)
- Include CSS animations for CTAs (subtle pulse or glow)
- Placeholder images using CSS gradients or colored blocks (no external image URLs)
- Use system fonts: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- CTA links should point to `#checkout`

### Step 4: Social Posts — Promotional (`social-promotional.md`)

Create **5 promotional social posts** that sell the offer directly. For each post include:

- The platform it's optimized for (Instagram, Facebook, X/Twitter, LinkedIn, TikTok)
- The full post copy
- A suggested visual/hook description
- Hashtags (if applicable)

Post styles should vary:
1. Story-based (personal narrative)
2. Problem-solution (direct response)
3. Social proof / results-based
4. Objection-handling
5. Urgency / last chance

### Step 5: Social Posts — Pre-Launch / Self-Identification (`social-prelaunch.md`)

Create **5 pre-launch posts** that do NOT mention the offer at all. These help the ideal buyer self-identify and build trust. Each post should:

- Make the reader think "that's literally me"
- Provide genuine value or a perspective shift
- Build authority in the topic area
- End with engagement-driving copy (question, hot take, or "save this")

Post styles:
1. "You might be [type of person] if..." (self-identification)
2. Myth-busting / contrarian take
3. Quick tip / framework that gets a fast win
4. Vulnerable / honest story about the topic
5. "The difference between [struggling] and [succeeding] is..." (belief shift)

### Step 6: Fulfillment Emails (`fulfillment-emails.md`)

Write **2 emails** sent after purchase:

**Email 1 — Immediate (Welcome + Access)**
- Subject line (+ 2 alternatives)
- Warm, excited tone
- Confirm what they bought
- Provide access instructions (placeholder links)
- Set expectations for what happens next
- Quick win they can get in the first 10 minutes

**Email 2 — Day 2 (Momentum + Support)**
- Subject line (+ 2 alternatives)
- Check in on their progress
- Address buyer's remorse proactively
- Share a specific tip to get started
- Remind them of the guarantee
- Invite them to reply with questions

### Step 7: Abandoned Cart Emails (`abandoned-cart-emails.md`)

Write **4 emails** for people who started checkout but didn't complete:

**Email 1 — 1 hour after abandonment (Soft reminder)**
- Subject line (+ 2 alternatives)
- Casual, helpful tone — "noticed you didn't finish"
- Restate the core benefit (1 sentence)
- Link back to checkout
- No pressure

**Email 2 — 24 hours (Objection handling)**
- Subject line (+ 2 alternatives)
- Address the #1 objection head-on
- Include a mini testimonial or proof point (placeholder)
- Restate the guarantee
- CTA to complete purchase

**Email 3 — 48 hours (Story/transformation)**
- Subject line (+ 2 alternatives)
- Tell a transformation story (of a past customer or hypothetical)
- Paint the "before and after"
- Create FOMO around what they're missing
- CTA to complete purchase

**Email 4 — 72 hours (Final + urgency)**
- Subject line (+ 2 alternatives)
- This is the last email about this
- Final urgency play (price going up, bonuses expiring, spots limited — pick what fits)
- Summarize everything they get
- Bold CTA
- P.S. line with the guarantee one more time

---

## Output Structure

```
generated/
  [idea-slug]/
    audience.md
    offer.md
    sales-page.html
    social-promotional.md
    social-prelaunch.md
    fulfillment-emails.md
    abandoned-cart-emails.md
```

## Writing Style Guidelines

- Write like a human, not a marketer. Conversational, direct, specific.
- Use the audience's language — the words they'd actually say to a friend.
- Avoid cliches: "unlock your potential", "take it to the next level", "game-changer"
- Be specific over generic: "lose 12 lbs in 8 weeks" beats "transform your body"
- Short paragraphs. Short sentences. One idea per line.
- Use power words sparingly and intentionally.
- Every sentence should earn its place — if it doesn't move the reader forward, cut it.

## Important Notes

- Generate ALL 7 files every time — never skip steps
- The sales page must be a complete, working HTML file you can open in a browser
- All copy should be consistent in voice, audience targeting, and offer details across all files
- Use [PLACEHOLDER] markers for anything the user needs to customize (testimonials, specific links, images, etc.)
- After generating, provide a brief summary of what was created and any recommendations
