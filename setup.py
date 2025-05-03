from setuptools import setup, find_packages

setup(
    name="window-capture-reading",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "opencv-python",
        "numpy",
        "Pillow",
    ],
    python_requires=">=3.11",
    author="suittizihou",
    description="ウィンドウキャプチャと画面差分検知を行うアプリケーション",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
    ],
)