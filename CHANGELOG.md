# Changelog

## [0.2.0](https://github.com/shano/auric/compare/auric-v0.1.0...auric-v0.2.0) (2026-05-30)


### Features

* add AutoDetector — finds Claude via settings.json + key resolution ([41d40c2](https://github.com/shano/auric/commit/41d40c2f35984de44b9eeb08c49860b4f4373d9a))
* add ClaudeProvider API pinger — extracts live rate limits from response headers ([2c3b1dc](https://github.com/shano/auric/commit/2c3b1dcecfa417d8b0b2dababe7308ff38e0ad73))
* add ClaudeProvider file poller — reads stats-cache.json for daily usage ([ef7288e](https://github.com/shano/auric/commit/ef7288e20ae985f6ac06aaccf5f57ae0d66a57cd))
* add ConfigManager — reads/writes ~/.config/auric/config.toml ([c9d4491](https://github.com/shano/auric/commit/c9d449110ce0413034394d8e37c8c64af9da0639))
* add models — Provider, UsageSnapshot, RateLimitState, AppConfig ([f745c2b](https://github.com/shano/auric/commit/f745c2bb29fc41b6b5535bff666b10a1a6cf5d4b))
* add SQLiteStorage — persists usage snapshots and rate limit history ([d20048a](https://github.com/shano/auric/commit/d20048a14188ccb0899e02b9962a70b0780955d6))
* add tray UI, DI container, entry point — Auric is launchable ([080fd31](https://github.com/shano/auric/commit/080fd319b2f5e1409fb896cf8b27ac773b48085c))
* add UsageCollector — orchestrates poll/ping, persists results, thread-safe state ([2e7dc59](https://github.com/shano/auric/commit/2e7dc59538ebe8a9ab45c053d43b09728aaffd1f))
* show 5h and 7d rate limit windows in tray menu ([#2](https://github.com/shano/auric/issues/2)) ([faaa365](https://github.com/shano/auric/commit/faaa36583273882f661b3ce669186acce19ad9a6))


### Bug Fixes

* add permissions and uv install to build workflow ([274b827](https://github.com/shano/auric/commit/274b8274de3dd08655d6a3a56e8370cd4d0c10f1))
