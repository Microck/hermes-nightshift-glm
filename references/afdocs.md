# AFDocs

Source: https://github.com/agent-ecosystem/afdocs/raw/refs/heads/main/README.md

AFDocs tests documentation sites against the Agent-Friendly Documentation Spec. It runs 23 checks across 7 categories to measure how well AI coding agents can discover, navigate, and consume docs.

Status: Early development (0.x). Check IDs, CLI flags, and output formats may change between minor versions. Implements spec v0.5.0 (2026-04-25).

## Quick Start

```bash
npx afdocs check https://docs.example.com --format scorecard
```

Example output:

```text
Agent-Friendly Docs Scorecard
==============================

  Overall Score: 72 / 100 (C)

  Category Scores:
    Content Discoverability           72 / 100 (C)
    Markdown Availability             60 / 100 (C)
    Page Size and Truncation Risk     45 / 100 (D)
    ...

  Interaction Diagnostics:
    [!] Markdown support is undiscoverable
        Your site serves markdown at .md URLs, but agents have no way to
        discover this. ...

  Check Results:
    Content Discoverability
      PASS  llms-txt-exists        llms.txt found at /llms.txt
      WARN  llms-txt-size          llms.txt is 65,000 characters
            Fix: If it grows further, split into nested llms.txt files ...
      FAIL  llms-txt-directive-html No directive detected in HTML of any tested page
            Fix: Add a visually-hidden element near the top of each page ...
```

## Install

```bash
npm install -g afdocs
```

Or as a dev dependency for CI:

```bash
npm install -D afdocs
```

Requires Node.js 22 or later.

## Documentation

Full documentation is available at https://afdocs.dev:

- Understand Your Score: https://afdocs.dev/what-is-agent-score
- Improve Your Score: https://afdocs.dev/improve-your-score
- Checks Reference: https://afdocs.dev/checks/
- CLI Reference: https://afdocs.dev/reference/cli
- CI Integration: https://afdocs.dev/ci-integration
- Programmatic API: https://afdocs.dev/reference/programmatic-api

## Responsible Use

AFDocs makes HTTP requests to the sites it checks. It enforces delays between requests (200ms default), caps concurrent connections, and honors `Retry-After` headers.

## Nightshift Task Guidance

Use AFDocs only when a public documentation URL can be inferred from the repository. Check common sources first: README links, package metadata, docs config, static-site config, `docs/` setup, `llms.txt`, and deployment docs.

If no docs URL is discoverable, do not fabricate one. Report that AFDocs could not be run and list the files inspected. Still scan local documentation files for agent-friendly documentation gaps that map to AFDocs concepts: discoverability, markdown availability, page size, truncation risk, navigation clarity, and machine-readable entrypoints.

Prefer:

```bash
npx -y afdocs check <docs-url> --format scorecard
```

If the command fails, capture the exact command, exit behavior, and likely reason in the issue body.
