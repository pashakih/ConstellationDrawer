from setuptools import setup

# Target the main script
APP = ['constellation_drawer.py']
DATA_FILES = ['hip_main.dat', 'de421.bsp'] 

OPTIONS = {
    'argv_emulation': False, # Disabled to prevent crash on Apple Silicon
    'packages': ['matplotlib', 'skyfield', 'numpy', 'pandas'],
    'includes': ['cmath'],   # Explicitly include the cmath stdlib module to prevent virtualenv packaging errors
    'plist': {
        'CFBundleName': 'Constellation Drawer',
        'CFBundleDisplayName': 'Constellation Drawer',
        'CFBundleIdentifier': 'com.paul.constellationdrawer',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeName': 'Star Map Project',
                'CFBundleTypeExtensions': ['strmp'],
                'CFBundleTypeRole': 'Editor',
                'LSHandlerRank': 'Owner',
            }
        ]
    }
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)