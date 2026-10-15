# WarpGate UI design preview

Work takes place on `feature/ui-design`. Do not merge into `master` until the user has reviewed the remote preview and explicitly confirms the merge.

The theme adapts the user-provided Nexus Compute design guide: forest surfaces, lime actions with dark text, compact borders, and readable light/dark text. WarpGate keeps its existing Vue components, routing and responsive layout. Standard text and muted metadata target a 4.5:1 contrast ratio; primary actions target 7:1.

Admin route: `/admin/ui-preview`. Four UI-only fixture sets cover users, channels, requests and orders, with 24 rows each. Search, combined status filters, sorting across all pages, pagination and details use the existing table/dialog components. Fixture balances and orders are simulated and never written to the operational database.

Preview deployment uses the existing remote test cluster and an immutable feature-branch image. While this preview is active, `release-agent` is paused so it cannot overwrite the unmerged preview with the latest master release. Branch images never update the `latest` registry tag. Restore the controller after the user approves merging and the master build succeeds, or when ending the preview.

Local application services remain stopped. Type checks, builds and tests may run locally without starting an application server or database.
