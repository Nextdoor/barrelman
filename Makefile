# Standard settings that will be used later
DOCKER := $(shell which docker)
COMPOSE := $(shell which docker-compose)
SHA1 := $(shell git rev-parse --short HEAD)
BRANCH := $(shell basename $(shell git symbolic-ref HEAD))

# DOCKER_TAG is only used in the `tag` target below. Its used when you
# take your built image, and you want to tag it prior to uploading it to a
# target repository.
DOCKER_TAG ?= $(SHA1)

# Dynamically generate the DOCKER_IMAGE name from the name of our directory.
# This can be overridden by setting the DOCKER_IMAGE environment variable in
# your shell though.
DOCKER_IMAGE ?= $(shell basename $(CURDIR) .git)
DOCKER_REGISTRY ?= hub.docker.com
DOCKER_NAMESPACE ?= nextdoor

# Create two "fully qualified" image names. One is our "local build" name --
# its used when we create, run, and stop the image locally. The second is our
# "target build" name, which is used as a final destination when uploading the
# image to a repository.
LOCAL_DOCKER_NAME ?= "$(DOCKER_IMAGE):$(SHA1)"
TARGET_DOCKER_NAME := "$(DOCKER_REGISTRY)/$(DOCKER_NAMESPACE)/$(DOCKER_IMAGE):$(DOCKER_TAG)"

DOCKER_BUILD_ARGS := -t $(LOCAL_DOCKER_NAME)

ifdef CACHE_FROM
DOCKER_BUILD_ARGS := --cache-from $(CACHE_FROM) $(DOCKER_BUILD_ARGS)
endif

DOCKER_RUN_ARGS := -it \
	--env-file envfile \
	--hostname barrelman-dev \
	--name barrelman \
	-v $$HOME/.aws:/root/.aws \
	-p 80:80

# Create envfile if it doesn't exist.
_ := $(shell [ -e envfile ] || touch envfile)

.PHONY: login populate_cache build test simulate stop run shell exec tag push venv

default: build run

login:
	@echo "Logging into $(DOCKER_REGISTRY)"
	@$(DOCKER) login \
		-u "$(DOCKER_USER)" \
		-p "$(value DOCKER_PASS)" "$(DOCKER_REGISTRY)"

populate_cache:
	@echo "Attempting to download $(DOCKER_IMAGE)"
	@$(DOCKER) pull "$(DOCKER_REGISTRY)/$(DOCKER_NAMESPACE)/$(DOCKER_IMAGE)" && \
		$(DOCKER) images -a || exit 0

build:
	@echo "Building $(LOCAL_DOCKER_NAME)"
	@$(DOCKER) build $(DOCKER_BUILD_ARGS) .

test: build stop
	@echo "Testing $(LOCAL_DOCKER_NAME)"
	@$(DOCKER) run $(DOCKER_RUN_ARGS) --entrypoint sh \
		"$(LOCAL_DOCKER_NAME)" \
		-c "cd /app/src/ && PYTHONPATH=. pytest -m 'not integration' $$TEST_ARGS --cov"

stop:
	@$(DOCKER) rm -f barrelman > /dev/null 2>&1 || true

run: build stop
	@$(DOCKER) run $(DOCKER_RUN_ARGS) \
		"$(LOCAL_DOCKER_NAME)"

shell: stop
	@$(DOCKER) run $(DOCKER_RUN_ARGS) --entrypoint sh \
		"$(LOCAL_DOCKER_NAME)"

exec:
	@$(DOCKER) exec -it barrelman bash

tag:
	@echo "Tagging $(LOCAL_DOCKER_NAME) as $(TARGET_DOCKER_NAME)"
	@$(DOCKER) tag "$(LOCAL_DOCKER_NAME)" "$(TARGET_DOCKER_NAME)"

push: tag
	@echo "Pushing $(LOCAL_DOCKER_NAME) to $(TARGET_DOCKER_NAME)"
	@$(DOCKER) push "$(TARGET_DOCKER_NAME)"

venv:
	@echo "Creating and updating venv."
	@python3.6 -m venv .venv
	@if [ "$$(cat requirements.txt | sort)" != "$$(.venv/bin/pip freeze)" ]; then \
		.venv/bin/pip install -r requirements.txt; \
	fi
