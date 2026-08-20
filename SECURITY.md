# Security policy

## Reporting a vulnerability

Open a private security advisory at
<https://github.com/ankit-realfast/delivery-os/security/advisories/new>. Do not put
credentials, client card contents, or an unpatched exploit in a public issue.

Supported security fixes target the latest released minor version.

## Trust boundary

`dos verify` intentionally executes the command stored in a card. Treat cards from
an untrusted pull request as executable code. Review the command before running it,
or inspect it safely with:

```bash
dos verify C-0001 --dry-run
```

Commands run without a shell, inside the repository, with a time limit. Requested
environment names require an allowlist. The child process still inherits the
calling process environment, so run untrusted repositories in an isolated CI job
without production secrets.

GitHub workflows use the smallest documented permissions and skip fork write-back.
Release artifacts include SHA-256 checksums and GitHub build-provenance attestations
signed through the release workflow's OpenID identity.
