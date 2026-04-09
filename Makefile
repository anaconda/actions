.PHONY: lock lock-upload-package lock-tests

## Generate all lockfiles
lock: lock-upload-package lock-tests

## Generate lockfile for upload-package action
lock-upload-package:
	cd upload-package && pixi lock

## Generate lockfile for test build environment
lock-tests:
	cd tests && pixi lock
