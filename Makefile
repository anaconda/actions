.PHONY: lock lock-upload-package lock-build-package lock-tests test test-build-package

## Generate all lockfiles
lock: lock-upload-package lock-build-package lock-tests

## Generate lockfile for upload-package action
lock-upload-package:
	cd upload-package && pixi lock

## Generate lockfile for build-package action
lock-build-package:
	cd build-package && pixi lock

## Generate lockfile for upload-package test environment
lock-tests:
	cd upload-package/tests && pixi lock

## Run all unit tests
test: test-build-package

## Run build-package unit tests (logic only, no conda-build invocation)
test-build-package:
	cd build-package && pixi run -e test pytest tests/test_build.py -v

## Run build-package integration tests (actually invokes conda-build)
test-build-package-integration:
	cd build-package && pixi run -e integration pytest tests/test_integration.py -v
