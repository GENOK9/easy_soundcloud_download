# ESC
# by Adrian Friedrich Jaeschke
# Requirements:
# Flet Version: 0.28.3
# Python Version: 3.13.5
# webview_flutter_android: 3.16.9 !! No Higher version supported by flet

## Run the app

### uv

Run as a desktop app:

```
#from /src:
flet run app.py
### Poetry

Install dependencies from `pyproject.toml`:

```
poetry install
pip install yt-dlp
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Build the app

### Android

```
flet build apk -v
```

For more details on building macOS package, refer to the [macOS Packaging Guide](https://flet.dev/docs/publish/macos/).

### Linux (forces webview_flutter_android to ^4.0.0 which currently cant build with flet)

```
flet build linux -v
```

For more details on building Linux package, refer to the [Linux Packaging Guide](https://flet.dev/docs/publish/linux/).
