from PyInstaller.utils.hooks import collect_all, copy_metadata

# babelfish loads country/language data files (iso-3166-1.txt, etc.) at
# import time via pkg_resources.resource_stream. Both the data files and
# the distribution metadata must be present for it to resolve correctly.
datas, binaries, hiddenimports = collect_all('babelfish')
datas += copy_metadata('babelfish')
