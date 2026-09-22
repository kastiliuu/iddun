# IDDUN — Product Direction Checkpoint
**Date:** 2026-09-17

## Core product model
IDDUN is a beauty discovery and booking marketplace connecting clients, individual professionals, and establishments.

The platform should not behave like a traditional salon ERP. The core value is discovery, professional identity, curated experiences, offers/opportunities, reputation, booking, and demand generation.

## Account/context model
Use one IDDUN account identity (`User`) with one or more contexts/roles:
- Client
- Professional
- Establishment owner/manager

A person may simultaneously be a client and a professional. A professional may work independently and also be linked to one or more establishments.

## Professional public identity
Professionals must have portable public profiles. Their profile, portfolio, reputation, followers, and reviews should remain attached to the professional, not to an employer.

Public professional pages should behave like a mix of LinkedIn profile + visual portfolio + commercial landing page:
- cover/banner
- profile photo
- name and professional title
- specialties
- about/bio
- portfolio images
- services/experiences
- upcoming availability/opportunities
- reviews/reputation
- establishments where the professional works
- CTA to book/contact/follow

## Professional onboarding
Entry point on the public site includes “Sou profissional”.

Initial onboarding should progressively collect profile data, with a profile-completion experience inspired by apps like Tinder/LinkedIn rather than a long administrative form.

Professional onboarding should include, at minimum:
- account/profile identity
- profile photo
- professional category and specialties
- about/bio
- service region/location
- portfolio photos (required minimum to complete/publish profile)
- services/experiences
- establishment relationship (independent or linked)
- availability/opportunity setup later

Use completion/progress feedback and a final public-profile preview before publishing.

## Establishment / Business onboarding
A separate context is required for establishments (salons, barbershops, tattoo studios, etc.).

Establishment public profile should include:
- logo
- cover/banner
- company name
- description/story
- category
- address/location
- opening hours
- gallery
- services/experiences
- team/professional roster
- reviews
- units/branches in the future
- booking CTA

The establishment control area should allow owners/managers to invite and manage professionals, while the professional keeps ownership of their personal public identity.

## Relationship graph
Navigation and data relationships must work bidirectionally:

`Establishment -> Team -> Professional -> Services/Experiences`

and

`Professional -> Establishments -> Establishment page`

This relationship is central to IDDUN discovery.

## Pricing direction
Initially, onboarding and platform access will be free to reduce friction and seed marketplace supply.

Later:
- Professional Free
- Professional paid tier
- Establishment Free
- Establishment paid tier

Paid plans should add tools/visibility/value without making the free profile useless.

## Public category visual direction
IDDUN keeps one design system and architecture, but category experiences may have visual skins:
- Beauty: premium/editorial/champagne
- Barber: masculine, graphite/metal/bronze, still premium
- Tattoo: darker/artistic/editorial, portfolio-first

Do not build separate products; use shared components + category/theme tokens.

## Near-term product priority
1. Define account/context architecture.
2. Build professional onboarding + IDDUN Pro control area.
3. Build establishment onboarding + IDDUN Business control area.
4. Build public professional profile pages.
5. Build public establishment profile pages.
6. Connect professional <-> establishment navigation.
7. Refine client discovery and booking flow.
8. Add category-specific visual skins (beauty/barber/tattoo).

