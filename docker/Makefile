CONTAINERS = base broker dashboard coap-gw
BUILD_TARGETS = $(addprefix build-,$(CONTAINERS))
PUSH_TARGETS = $(addprefix push-,$(CONTAINERS))

.PHONY: all build build-% push push-%

all: build

build: $(BUILD_TARGETS)

build-%:
	@echo "**** Build container pyaiot/$* ****"
	@docker build $* -t pyaiot/$*
	@echo "**** Done ****"
	@echo

push: $(PUSH_TARGETS)

push-%:
	@echo "**** Push container pyaiot/$* ****"
	docker push pyaiot/$*:latest
	@echo "**** Done ****"
	@echo
