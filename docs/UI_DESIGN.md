# WarpGate interface design

The approved theme uses forest surfaces, lime actions with dark text, compact borders, and separate readable light/dark palettes. Standard text and muted metadata target a 4.5:1 contrast ratio; primary actions target 7:1. Table headers and pinned columns share the same surface tokens.

Administrator navigation separates operations from an explicitly entered user center. Operations pages hide personal balance/subscription summaries; account security remains in the profile dropdown. API testing aliases reuse current-account key and usage handlers, with an explicit scope notice. Personal funds and orders are never presented as platform revenue. Regular-user navigation and backend permissions are unchanged.

The user approved merging and releasing this design after remote review. The temporary interface-preview page, navigation entry, translations and all 96 demo fixtures have been removed from the released application. No fixture records were written to the database.

Releases follow master push → WarpGate CI/CD → workflow_run → WarpGate Cluster Release → in-cluster release-agent. Restore release-agent after the approved master build succeeds; local application services stay stopped.
