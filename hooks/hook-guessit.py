from PyInstaller.utils.hooks import collect_all, copy_metadata

datas, binaries, hiddenimports = collect_all('guessit')
datas += copy_metadata('guessit')
