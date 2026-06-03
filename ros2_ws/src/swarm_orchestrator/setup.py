from setuptools import find_packages, setup

package_name = "swarm_orchestrator"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/orchestrator.launch.py"]),
        (f"share/{package_name}/config", ["config/orchestrator.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="VGU VLM Swarm",
    maintainer_email="maintainer@example.com",
    description="Orchestrator node for VLM/RAG intervention lifecycle.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "orchestrator_node = swarm_orchestrator.orchestrator_node:main",
        ],
    },
)
