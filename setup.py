from setuptools import setup

setup(
    name="clipboard_google_translate",
    version="2.0.0",
    packages=["clipboard_google_translate"],
    url="",
    license="",
    author="Duong_Thanh",
    author_email="mthanh2602@gmail.com",
    description="Translate clipboard text with Google Translate",
    install_requires=[
        "deep-translator>=1.11.4",
        "pyperclip>=1.8.2",
    ],
    entry_points={
        "console_scripts": [
            "clipboard-google-translate=clipboard_google_translate.main:main",
        ],
    },
    python_requires=">=3.9",
)
