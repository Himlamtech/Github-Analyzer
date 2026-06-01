# Design

## Visual direction

The new frontend keeps a high-contrast editorial dashboard style with strong typography, motion, and presentation-oriented storytelling.

## Design split

- operational surfaces should reflect real backend state
- research surfaces may stay curated if no trustworthy API exists yet

## Current implementation rule

When a panel represents current system state, it should use live backend data.
When a panel represents macro narrative or editorial framing, it may remain curated until a proper backend model exists.

## Current page-to-data mapping

- `Overview` -> live operational summary from dashboard and pipeline endpoints
- `BreakoutDetector` -> live repository ranking and repo time series
- `EcosystemRotation` -> transitional view using live topic rotation where possible
- `NewsImpact` -> curated until official launch/news sync exists
- `CompetitiveRadar` -> curated until framework-level marts exist
- `WeeklyBrief` -> curated editorial output
