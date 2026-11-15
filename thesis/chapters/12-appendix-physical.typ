#import "../lib.typ": *

= Physical Testbed Configuration <sec:app-physical>

#show raw.where(block: true): set text(size: 7.5pt)

This appendix records the communication setup of the physical demonstration (@sec:impl-physical) so that it can be reproduced. The values are as recorded in the team's testbed notes of 15 November 2026, which describe the 12 November 2026 runs and are not in the repository #ev("4.41"). The laptop's IP address is replaced by the placeholder `<CURRENT_HOST_IP>`, and in the client configuration `N` stands for the robot number (2 to 5).

== Zenoh Router on the Laptop <sec:app-physical-router>

The laptop runs one bridge in router mode, configured by the file `zenoh_host_tb25.json5`. It forwards the four velocity-command topics to the robots and receives the four odometry topics; every pattern is anchored with `^` and `$`. The two allowlist arrays are wrapped over several lines here; the entries are unchanged #ev("4.41").

```json5
{
  mode: "router",
  listen: { endpoints: ["tcp/<CURRENT_HOST_IP>:7447"] },
  scouting: { multicast: { enabled: false }, gossip: { enabled: false } },
  plugins: {
    ros2dds: {
      nodename: "zenoh_bridge_laptop_tb25",
      domain: 0,
      ros_automatic_discovery_range: "LOCALHOST",
      allow: {
        publishers: [
          "^/tb3_2/cmd_vel$", "^/tb3_3/cmd_vel$",
          "^/tb3_4/cmd_vel$", "^/tb3_5/cmd_vel$"
        ],
        subscribers: [
          "^/tb3_2/odom$", "^/tb3_3/odom$",
          "^/tb3_4/odom$", "^/tb3_5/odom$"
        ],
        service_servers: [], service_clients: [], action_servers: [], action_clients: []
      },
      reliable_routes_blocking: true
    }
  }
}
```

== Zenoh Client on Each Robot <sec:app-physical-client>

Each robot runs one client bridge from `$HOME/zenoh_config.json5`, which allows only that robot's own two topics (@tab:app-physical-routing) #ev("4.41").

```json5
{
  mode: "client",
  connect: { endpoints: ["tcp/<CURRENT_HOST_IP>:7447"] },
  scouting: { multicast: { enabled: false }, gossip: { enabled: false } },
  plugins: {
    ros2dds: {
      nodename: "zenoh_bridge_tb3_N",
      domain: 0,
      ros_automatic_discovery_range: "LOCALHOST",
      allow: {
        publishers: ["^/tb3_N/odom$"],
        subscribers: ["^/tb3_N/cmd_vel$"],
        service_servers: [], service_clients: [], action_servers: [], action_clients: []
      },
      reliable_routes_blocking: true
    }
  }
}
```

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, left, left, left),
    stroke: 0.4pt + luma(160),
    fill: (_, y) => if y == 0 { luma(235) },
    table.header([*Robot*], [*Bridge node*], [*Publishes to the laptop*], [*Receives from the laptop*]),
    [TurtleBot3 2], [`zenoh_bridge_tb3_2`], [`/tb3_2/odom`], [`/tb3_2/cmd_vel`],
    [TurtleBot3 3], [`zenoh_bridge_tb3_3`], [`/tb3_3/odom`], [`/tb3_3/cmd_vel`],
    [TurtleBot3 4], [`zenoh_bridge_tb3_4`], [`/tb3_4/odom`], [`/tb3_4/cmd_vel`],
    [TurtleBot3 5], [`zenoh_bridge_tb3_5`], [`/tb3_5/odom`], [`/tb3_5/cmd_vel`],
  ),
  caption: flex-caption([Zenoh routing table of the physical testbed.], [Zenoh routing table of the physical testbed. No services or actions are bridged.#fig-source("4.41")]),
) <tab:app-physical-routing>

== Bring-Up and Validation Commands <sec:app-physical-commands>

The commands below start the router, bring up each robot with its client bridge, and check communication before execution #ev("4.41").

```bash
# all machines
source /opt/ros/jazzy/setup.bash
export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST

# laptop: check for old processes, then start the router
pgrep -af 'zenohd|zenoh-bridge-ros2dds'
zenoh-bridge-ros2dds -c zenoh_host_tb25.json5

# each robot (N = 2..5): bring-up, then the client bridge
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_bringup robot.launch.py namespace:=/tb3_N
/usr/local/bin/zenoh-bridge-ros2dds -c "$HOME/zenoh_config.json5"

# laptop: communication check before execution
for id in 2 3 4 5; do
  timeout 6 ros2 topic hz "/tb3_${id}/odom"
  ros2 topic info "/tb3_${id}/cmd_vel" -v
done
```

The team's procedure required, for each robot, before execution #ev("4.41"):

- odometry (`/tb3_N/odom`) arrives continuously on the laptop;
- the velocity-command topic (`/tb3_N/cmd_vel`) has a subscriber on the robot;
- the robot's allowlist contains no other robot's topics;
- exactly one client bridge runs on the robot and one router on the laptop;
- node names are unique.

Only one router may listen on port 7447: a second router, or a bridge connecting to the same endpoint, causes `CONNECTION_TO_SELF`, duplicate routes or multiple ROS 2 publishers #ev("4.41").
