from setuptools import find_packages, setup

package_name = "swarm_execution"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/execution.launch.py"]),
        (f"share/{package_name}/config", ["config/safety.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="VGU VLM Swarm",
    maintainer_email="maintainer@example.com",
    description="Execution nodes for swarm coordination commands.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "coordination_client_node = swarm_execution.coordination_client_node:main",
            "command_bus_node = swarm_execution.command_bus_node:main",
            "safety_monitor_node = swarm_execution.safety_monitor_node:main",
        ],
    },
)
