.PHONY: test lint build-ros2 run-simulation run-orchestrator index-rag

test:
	pytest

lint:
	ruff check .

build-ros2:
	./scripts/build_ros2.sh

run-simulation:
	./scripts/run_simulation.sh

run-orchestrator:
	./scripts/run_orchestrator.sh

index-rag:
	./scripts/index_rag_kb.sh
