[app]

# (str) Title of your application
title = Clean Slate

# (str) Package name
package.name = cleanslate

# (str) Package domain (needed for android/ios packaging)
package.domain = org.cleanslate

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (leave empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas

# (list) List of directory to exclude (leave empty to not exclude anything)
source.exclude_dirs = .venv, .buildozer, __pycache__, dev, bin, docs

# (str) Application versioning (method 1)
version = 1.0.0

# (list) Application requirements
# charset-normalizer is a dependency of Kivy's requests. p4a's resolver picks
# the Android-tagged binary wheel, then installs it with the host pip, which
# rejects that platform tag. Pin the pure-Python wheel instead.
requirements = python3,kivy==2.3.1,charset-normalizer@https://files.pythonhosted.org/packages/fc/ad/d07d7862a62ffa6d79d68074d14823243dd235a77c45262acbf6adeb28bf/charset_normalizer-3.5.2-py3-none-any.whl

# (str) Presplash of the application
presplash.filename = %(source.dir)s/assets/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/assets/icon.png

# (list) Supported orientations
orientation = portrait

# (str) Supported orientation
fullscreen = 0

# (string) Presplash background color (for android toolchain)
android.presplash_color = #0f1115

# (list) Permissions
# (Clean Slate does not need any Android permissions.)

# (int) Target Android API. API 34 avoids Android 15's forced edge-to-edge
# layout, which SDL2 2.30 does not inset for. Sideloaded apps are unaffected
# by Play's newer target requirements.
android.api = 34

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (int) Android NDK API to use. This is the minimum API your app will support.
android.ndk_api = 24

# (bool) If True, then automatically accept SDK license
# agreements. This is intended for automation only.
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) Keep the app data local: no Android cloud backup.
android.allow_backup = False

# (str) Author name
author = burtonwill055-hash

# (str) Author email
author.email =

# (str) License
license = MIT

# (str) The URL of your website
#website =

# (str) Release artifact type
android.release_artifact = apk

# (str) Debug artifact type
android.debug_artifact = apk
