# Majestic Made App Legal Pages

## Portfolio direction — November 3, 2026

See [current implementation, approved direction, and next work](docs/PORTFOLIO_ALIGNMENT.md).
The [canonical release queue](https://github.com/MAJESTIC-MADE-LLC/.github/blob/dev/portfolio/LAUNCH_SLATE.md) governs product order after the [shared foundation prerequisite](https://github.com/MAJESTIC-MADE-LLC/.github/blob/dev/portfolio/STACK_STANDARD.md). Each product then completes its own release approval.
This documentation pass preserves existing implementations; it does not complete app fixes or authorize publication.

Public privacy, terms, and support pages for Majestic Made apps.

Custom domain: https://legal.majesticmade.dev/

## Publication paused (2026-10-24)

The founders requested that the whole Majestic website be taken offline until
app listings and submissions are ready. GitHub Pages has been disabled for this
repository; the source and branches are preserved. The custom domain's DNS is
disconnected from GitHub Pages. The portfolio's Cloudflare Pages hosting is also
unpublished. Do not re-enable publication without explicit founder approval.

The hosting instructions below describe the configuration to restore at relaunch.

## App folders

- `fine-notes/` for Fine Notes
- `skepbook/` for Skepbook
- `campsake/` for Campsake
- `kinwall/` for Kinwall
- `claim-crate/` for Claim Crate
- `tender-days/` for Tender Days
- `divefolio/` for Divefolio
- `creelmark/` for Creelmark
- `majestic-made-hub/` for Majestic-Made-Hub
- `paws/` for Paws
- `brassmark/` for Brassmark
- `namefold/` for Namefold
- `ridelore/` for Ridelore
- `turnstamp/` for Turnstamp
- `daymerit/` for Daymerit
- `what-we-own/` for What We Own
- `object-lore/` for Object Lore
- `pantry-clock/` for Pantry Clock

Each app folder contains:

- `privacy/index.html`
- `terms/index.html`
- `support/index.html`

Fine Notes, Skepbook, Paws, Namefold, Ridelore, Daymerit, and Pantry Clock have
product-specific working drafts based on their current implementations. Their pages
visibly identify that status. The Majestic-Made-Hub pages describe the portfolio implementation,
Cloudflare forms database, and private administrator dashboard. Publication remains paused.

The other ten products have pre-release information and contact pages. They do not
claim that an app is available or invent collection, account, purchase, or subscription
behavior. These pages are useful destinations for portfolio links, not final policies
for a released app. Have the founders and qualified counsel review final product
policies, then reconcile them with release builds and store disclosures before launch.

`legal-pages.json` is the canonical inventory: `active` identifies product-specific
documents (including working drafts), and `concept` identifies pre-release information.
Neither classification certifies legal approval or app-store availability.

## Existing links and hosting

When explicitly restored, GitHub Pages is configured to serve `main` at the custom domain above. No
new hosting service, paid plan, mail backend, or server is required. Work on `dev`
and obtain explicit approval before promoting changes to `main`.

`legacy-urls.json` maps the sixteen previous product slugs to their current names.
Each old landing, privacy, terms, and support URL has a static forwarding page with
a fixed immediate meta refresh, a current canonical URL, and a visible fallback link.
GitHub Pages returns those HTML pages with HTTP 200; the browser forwards visitors.
No script or query-driven redirect is used. Preserve these pages for old bookmarks.

GitHub Actions validation runs only on a push to `main`.
Run development checks locally to conserve Actions usage. Pages' managed
publication follows the configured `main` source.

## Validation

Run `./scripts/validate_legal_pages.py` and
`python3 -m unittest discover -s tests -v` before publishing. The validator rejects
missing pages, broken local links, invalid canonicals, unfinished copy, hidden-only
concept warnings, and redirects outside the fixed legacy mapping. Canonical documents
remain script-free; only mapped legacy pages may use the exact approved meta refresh.

Preview locally with `python3 -m http.server 8773 --bind 127.0.0.1`, then check the
directory, a product draft, a concept notice, website policies, and an old-name URL
on desktop and mobile. After publication, verify all 54 canonical detail URLs plus
18 product landings, the directory, and 64 legacy forwarding pages over HTTPS.
