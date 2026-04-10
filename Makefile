.PHONY: lock lock-upload-package lock-build-conda lock-tests test test-build-conda

## Generate all lockfiles
lock: lock-upload-package lock-build-conda lock-tests

## Generate lockfile for upload-package action
lock-upload-package:
	cd upload-package && pixi lock

## Generate lockfile for build-conda action
lock-build-conda:
	cd build-conda && pixi lock

## Generate lockfile for upload-package test environment
lock-tests:
	cd upload-package/tests && pixi lock

## Run all unit tests
test: test-build-conda

## Run build-conda unit tests (logic only, no conda-build invocation)
test-build-conda:
	cd build-conda && pixi run -e test pytest tests/test_build.py -v

## Run build-conda integration tests (actually invokes conda-build)
test-build-conda-integration:
	cd build-conda && pixi run -e integration pytest tests/test_integration.py -v
