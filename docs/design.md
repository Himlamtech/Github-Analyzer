# Design

## Visual direction

The new frontend keeps a high-contrast editorial dashboard style with strong typography, motion, and presentation-oriented storytelling.

## Design split

- operational surfaces should reflect real backend state
- editorial framing may stay lightweight, but the underlying intelligence contract should be backend-owned

## Current implementation rule

When a panel represents current system state, it should use live backend data.
When a panel represents macro narrative or editorial framing, it should still be anchored to a named backend contract.

## Current page-to-data mapping

- `Overview` -> live operational summary from dashboard and pipeline endpoints
- `BreakoutDetector` -> live repository ranking and repo time series
- `EcosystemRotation` -> taxonomy-aware rotation intelligence using `/intelligence/rotation`
- `NewsImpact` -> computed intelligence payload from persisted official-source items plus sync/health operations
- `CompetitiveRadar` -> computed backend framework radar using repository analytics inputs
- `WeeklyBrief` -> versioned backend snapshot from `latest` plus archive metadata
