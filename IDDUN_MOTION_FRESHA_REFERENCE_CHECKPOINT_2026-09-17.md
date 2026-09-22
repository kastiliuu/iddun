# IDDUN — Motion & Fresha Homepage Reference Checkpoint
**Data:** 2026-09-17

## 1. Motion reference — CashMe video
Use as motion inspiration, not as a literal visual copy.

### Behaviors worth reusing
- Hero assembled progressively rather than appearing all at once.
- Strong sense of continuity between sections.
- Sticky/pinned moments where the composition remains on screen while scroll changes the scene.
- Scroll-linked transforms: translate, scale, opacity and subtle depth.
- Previous section continues moving while the next enters.
- Layered overlaps rather than hard section cuts.
- Large text and visual elements enter at different moments.
- Subtle luminous gradients and light trails make static elements feel alive.
- Reversible behavior when scrolling back upward.
- Motion should explain hierarchy and continuity, never delay interaction.

### IDDUN translation
For the IDDUN hero and premium pages:
- subtle model parallax;
- gold/champagne light trails;
- slow glow pulses;
- sticky story sections;
- section-to-section continuity;
- image mask/reveal;
- headline fade/translate linked to scroll;
- layered transitions;
- minimal particles;
- `prefers-reduced-motion` support;
- mobile receives a simpler, lighter motion system.

### Implementation candidates
Prefer:
- CSS transforms / opacity;
- `position: sticky`;
- IntersectionObserver;
- requestAnimationFrame only when necessary;
- native scroll-driven animation APIs where support is acceptable.

Use GSAP + ScrollTrigger only for sequences that are genuinely too complex for the native stack.

---

## 2. Fresha homepage — current structural study

The current Fresha homepage is conversion-first rather than editorial-first.

### Hero
Primary headline:
- "Book local selfcare services" / Portuguese equivalent "Agende serviços de autocuidado".

Supporting message:
- discovery of top-rated salons, barbers, medspas, wellness studios and beauty experts.

The main action is a large multi-field search:
- treatment;
- location;
- time;
- search.

### Immediate trust / activity
Fresha surfaces a live-style count of appointments booked today.
This creates:
- social proof;
- activity;
- sense of marketplace liquidity.

### App promotion
A dedicated section promotes the Fresha mobile app with QR/download CTA.

### Reviews
Large testimonial/review section showing repeated 5-star user experiences around:
- discovery;
- convenience;
- reminders;
- booking;
- local salons/barbers;
- payment.

### Scale / authority
A strong proof section communicates:
- 1B+ appointments;
- 130K+ partner businesses;
- 120+ countries;
- 450K+ professionals.

### Business acquisition
The consumer homepage also contains a clear "Fresha for business" block, feeding supply acquisition from the same domain.

### SEO / city discovery
The lower homepage has a massive location/category directory:
- countries;
- major cities;
- hair;
- nails;
- brows/lashes;
- beauty salons;
- barbers;
- massages;
- spas;
- waxing;
- medspas;
- tattooing/piercing and other categories.

This is heavily optimized for discoverability and search-engine landing pages.

---

## 3. Lessons for IDDUN

### What we should borrow conceptually
1. Search/action must be obvious very early.
2. Marketplace liquidity should be visible when we have real data.
3. Strong proof metrics increase trust.
4. Consumer and professional acquisition can coexist on the same homepage.
5. City/category landing pages can become an important SEO channel.
6. Reviews should be tied to real completed appointments.
7. Mobile-app promotion only becomes valuable when the product gives users a reason to return.

### What IDDUN should NOT copy
- Fresha is heavily transactional and utilitarian.
- IDDUN should keep the stronger editorial/premium identity.
- IDDUN should not become only a search form + directory.
- IDDUN's differentiation remains:
  - professional identity;
  - portfolios;
  - verified results;
  - followers/feed;
  - recommendations;
  - certifications;
  - professional ↔ establishment graph;
  - normal slots + IDDUN opportunities;
  - client status / belonging;
  - content that creates demand before the user is actively searching.

### Strategic combination
Use:
- Fresha for marketplace clarity, search, proof and SEO;
- Stripe for system clarity;
- Frans Hals for editorial composition;
- Lando Norris / CashMe for cinematic motion and continuity;
- IDDUN's own social/status layer for differentiation.

---

## 4. Motion rule for future IDDUN work
Desktop may use richer motion.
Mobile must prioritize:
- speed;
- readability;
- thumb reach;
- no oversized empty bands;
- low GPU/battery cost;
- fewer simultaneous effects;
- no scroll-jacking.

The mobile experience must remain first-class, not a squeezed desktop version.
