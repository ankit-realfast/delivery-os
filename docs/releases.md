# Release process

delivery-os uses semantic versioning. `delivery_os/version.py` is the single source
of the product version; package metadata reads it dynamically. Hatchling builds the
package without writing `delivery_os.egg-info` into the source checkout.

Before tagging:

1. Update `delivery_os/version.py`.
2. Replace `Unreleased` with the release date in `CHANGELOG.md`.
3. Run the non-test quality gates documented in `CONTRIBUTING.md`.
4. Build the wheel and source distribution from a clean temporary checkout.
5. Confirm the tag is exactly `v` followed by the product version.

Pushing that tag runs `.github/workflows/release.yml`, which:

- Builds and publishes the wheel and source distribution through PyPI trusted
  publishing.
- Produces GitHub build-provenance attestations.

Repository setup required before the first release:

- Create a protected GitHub environment named `pypi`.
- Configure the PyPI project `delivery-os` to trust that environment and workflow.

Users install released versions with `pipx install delivery-os`.
