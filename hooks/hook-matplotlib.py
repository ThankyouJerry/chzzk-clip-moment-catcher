from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Collect matplotlib submodules
hiddenimports = collect_submodules('matplotlib')
datas = collect_data_files('matplotlib')
