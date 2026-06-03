from setuptools import find_packages, setup

package_name = "swarm_perception"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/perception.launch.py"]),
        (f"share/{package_name}/config", ["config/camera.yaml", "config/aruco.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="VGU VLM Swarm",
    maintainer_email="maintainer@example.com",
    description="Perception nodes for warehouse swarm coordination.",
    license="Apache-2.0",
    entry_points={
        "console_scripts": [
            "camera_node = swarm_perception.camera_node:main",
            "aruco_tracker_node = swarm_perception.aruco_tracker_node:main",
        ],
    },
)
