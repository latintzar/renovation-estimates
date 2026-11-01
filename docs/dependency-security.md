# Dependency review

`tools/check-npm-audit.mjs` runs the current npm audit and blocks every advisory except the exact development-only minimatch3.1.5 graph for [GHSA-g3hv-75wg-m249](https://github.com/advisories/GHSA-g3hv-75wg-m249). The advisory describes optimizationLevel>=2 preprocessing introduced in newer APIs; the pinned3.1.5 implementation has that machinery absent. Its original CommonJS function API is preserved for ESLint.

The exception requires the exact package, installed version, advisory URL and development-only lock provenance. Modern affected versions, runtime use, other advisories and missing provenance remain blocking. New glob/minimatch consumers use patched modern versions. The policy has offline regression tests.
