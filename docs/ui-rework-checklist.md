# UI simplification and premium redesign

## Completed in this worktree

- [x] Removed the Settings navigation and page for custom integrations, its
  example-server catalogue, and the generic Web API/MCP configuration form.
- [x] Removed visible Anthropic, OpenAI, and Gemini API-key controls, API-key
  model fields, and the related Settings bridge handlers.
- [x] Limited product reasoning selection to supported account-backed Claude
  subscription and ChatGPT plan routes; stale saved API selections fail closed.
- [x] Bundled Web Awesome 3.14.0 assets under `ui/vendor/webawesome` and serve
  them from a local WebView virtual host. No UI component needs a CDN.
- [x] Replaced the Settings sidebar's mixed coloured icon tiles with local
  Lucide static SVG assets and one neutral/active icon treatment.
- [x] Replaced Settings' native select elements with accessible `wa-select`
  controls and applied one dark popup treatment with viewport-aware placement.
- [x] Added shared dark-system tokens, focus treatment, reduced-motion support,
  and hidden-but-scrollable Settings content.
- [x] Reduced all explicitly declared UI weights above 500 to 500 or below.
- [x] Regression suite passed: 119 tests and 8 subtests. Release .NET build,
  Python self-test, published native self-test exit code, asset-copy assertion,
  and `git diff --check` also passed on 2026-10-18.
- [x] Final isolated output at `%TEMP%\Silly-ui-rework-release-20261018-02`
  contains `ui/vendor/webawesome/webawesome.loader.js` and the bundled Lucide
  sidebar SVGs; its native self-test returned `native selftest ok`.

## Font asset

- [x] Added the supplied `Satoshi-Variable.ttf` at
  `ui/assets/fonts/Satoshi-Variable.ttf`. The product does not download or
  substitute another font at runtime.
- [x] Verified the source, repository, and isolated release copies have the
  same SHA-256 checksum. The refreshed isolated output at
  `%TEMP%\Silly-ui-rework-release-20261018-03` contains the 127,420-byte font;
  its published native self-test returned `native selftest ok`.

## Validation to run after the font is supplied

- [ ] Launch an isolated development copy, open every Settings tab, and inspect
  `wa-select` near the top and bottom of a long page with keyboard, Escape,
  outside-click, mouse-wheel, and resize behavior.
- [ ] Capture normal-scale screenshots of the overlay, Settings, Reasoning,
  and an open selector in the WebView runtime.
