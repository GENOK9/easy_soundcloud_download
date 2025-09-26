# ESC for Android and Linux
#### Adrian Friedrich Jaeschke

### Optimal Requirements:
#### flet 0.28.3
#### python 3.13.5
#### webview_flutter_android: 3.16.9 !! No Higher version supported by flet

## Run the app

###

Run as a desktop app:

```
flet run src/app.py
```

For more details on running the app, refer to the [Getting Started Guide](https://flet.dev/docs/getting-started/).

## Build the app

### Android
```
cd src/
flet build apk --module-name app.py 
```

For more details on building and signing `.apk` or `.aab`, refer to the [Android Packaging Guide](https://flet.dev/docs/publish/android/).


### Linux (Forces webview_flutter_android ^4.0.0)
#### flet supports webview_flutter_android 3.16.9 or Lower
#### the build command changes flutteres pubslec.yamls webview_flutter_android ^3.16.9 entry to webview_flutter_android = ^4.0.0 which can not build
#### to run on Linux please refer to the run command:

```
flet run src/app.py
```
building Windows package, refer to the [Windows Packaging Guide](https://flet.dev/docs/publish/windows/).