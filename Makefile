.PHONY: test lint build-ros2 run-perception run-simulation run-orchestrator index-rag

test:
	pytest

lint:
	ruff check .

build-ros2:
	./scripts/build_ros2.sh

run-perception:
	./scripts/run_perception.sh

run-perception-isaac:
	./scripts/run_perception.sh --isaac-sim

run-simulation:
	./scripts/run_simulation.sh

run-orchestrator:
	./scripts/run_orchestrator.sh

index-rag:
	./scripts/index_rag_kb.sh
