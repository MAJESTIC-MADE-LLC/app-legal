# Pricing and consolidation validation — November 4, 2026

Approved targets are in [PRICING.md](PRICING.md). No app billing/store setup, hosted-data migration,
publishing, CI run, commit or push is performed by this change.

- Hub: Node **24.22.1**, all **156 tests / 20 files**, ESLint, TypeScript and production static build pass.
- Legal site: structure/status/link validator and all **29 Python tests** pass.
- Former Claim Crate Hub route renders a consolidation notice with a What We Own link and no form;
  the catalog excludes Claim Crate. The static export preserves the old URL without relying on a server redirect.
- Legal Claim Crate and Convoy landing/privacy/terms/support aliases point directly to What We Own;
  their fixed refreshes, canonicals and visible links are checked by the validator and regression tests.
- Quiet Arcade now displays only subscription paid choices ($1.99 monthly / $14.99 yearly); prior
  one-time survey identifiers remain accepted/readable as historical data, without new UI offerings.
- Native subscription migration, transaction/renewal/offline-grace/device qualification and final legal
  review remain pending. The checks above validate documentation/website changes, not consumer-app readiness.
