from setuptools import setup, Extension

ext = Extension("hello", sources=["src/hello.c"])

setup(
    name="test-compiled",
    version="0.0.1",
    ext_modules=[ext],
)
