from PyInstaller.utils.hooks import collect_data_files

hiddenimports = ["matplotlib.backends.backend_qtagg"]
datas = collect_data_files("matplotlib")
