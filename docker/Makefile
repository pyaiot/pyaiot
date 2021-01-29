CONTAINERS = base broker coap-gw dashboard
BUILD_TARGETS = $(addprefix build-,$(CONTAINERS))
PUSH_TARGETS = $(addprefix push-,$(CONTAINERS))
BUILD_PUSH_TARGETS = $(addprefix buildx-push-,$(CONTAINERS))

VERSION ?= latest
DOCKERHUB ?= pyaiot

.PHONY: all build build-% push push-% buildx buildx%

all: build

build: $(BUILD_TARGETS)

build-%:
	@echo "**** Build container $(DOCKERHUB)/$* ****"
	@docker build $* -t $(DOCKERHUB)/$*
	@echo "**** Done ****"
	@echo

push: $(PUSH_TARGETS)

push-%:
	@echo "**** Push container $(DOCKERHUB)/$* ****"
	docker push $(DOCKERHUB)/$*:$(VERSION)
	@echo "**** Done ****"
	@echo

buildx-push: $(BUILD_PUSH_TARGETS)

$(filter-out %base,$(BUILD_PUSH_TARGETS)): buildx-push-base
buildx-push-%:
	@echo "**** Build and push container $(DOCKERHUB)/$* ****"
	@docker buildx build $* \
		--platform linux/arm64/v8,linux/amd64 \
		-t $(DOCKERHUB)/$*:$(VERSION) --push
	@echo "**** Done ****"
	@echo
