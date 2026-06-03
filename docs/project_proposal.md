VIETNAMESE - GERMAN UNIVERSITY
DEPARTMENT OF COMPUTER SCIENCE

Leveraging Vision-Language Model (VLM) and Retrieval-Augmented
Generation (RAG) for Congestion Management in Warehouse Swarm
Robotics

Instructor: Dr. Vo Bich Hien

Project Proposal

Student: Dang Dinh Tu Anh - 10422086

HO CHI MINH CITY, 03/2026

Vietnamese-German University
Department of Computer Science

Content

1 Abstract . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
2 Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
3 Literature Review . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
3.1 Multi-Agent Coordination and Path Planning . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
3.2 Vision-Language Models in Robotics . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
3.3 LLM/VLM with RAG and Tool-Use in Embodied AI . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
4 Proposed Methodology . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
4.1 System Architecture Overview . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
4.2 Perception and Robot ID Tracking . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
4.3 VLM-Based Semantic Reasoning . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
4.4 RAG-Based Action Grounding . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
4.5 Execution via ROS2 . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 8
4.6 Data Flow Summary . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
5 Experiments & Evaluation . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
5.1 Simulation Environment . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 9
5.2 Evaluation Scenarios . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
6 Expected Results & Contributions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
6.1 Expected Results . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
6.2 Contributions . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 10
References . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 12

Vietnamese-German University
Department of Computer Science

1 Abstract

Congestion  and  deadlock  remain  critical  bottlenecks  in  warehouse  swarm  robotics,  where
dense fleets of autonomous mobile robots must navigate shared, spatially constrained environ-
ments. Classical approaches, including Artificial Potential Fields (APF), Reciprocal Velocity
Obstacles  (RVO/ORCA),  and  optimal  Multi-Agent  Path  Finding  (MAPF)  solvers,  provide
mathematically  grounded  solutions  but  suffer  from  well-documented  failure  modes:  local
minima  entrapment,  the  Freezing  Robot  Problem,  and  combinatorial  intractability  at  scale.
This proposal presents a hybrid two-layer architecture that augments fast, reactive
local  controllers  with  a  slower,  semantically  rich  reasoning  layer  powered  by  a
Vision-Language  Model  (VLM)  and  a  Retrieval-Augmented  Generation  (RAG)
module.  An  overhead  RGB  camera  tracks  robots  via  ArUco  fiducial  markers  and  provides
scene frames to a centralized VLM (e.g., VILA or NVIDIA Cosmos Reasoner), which performs
high-level  semantic  analysis  of  congestion  patterns,  deadlock  topologies,  and  environmental
context. The VLM’s natural-language reasoning is then grounded into structured, executable
robot commands through a RAG pipeline built on LangChain and ChromaDB, which retrieves
contextually  appropriate  action  templates  from  a  curated  knowledge  base  of  coordination
strategies. Commands are dispatched to TurtleBot3 robots via ROS2. The proposed system is
evaluated in simulation (Gazebo/Webots) across deadlock, bottleneck, and anomaly scenarios,
benchmarked against APF, ORCA, and CBS baselines using throughput, waiting time, collision
rate, and energy consumption metrics. The primary contributions are threefold: (1) the first
integration of VLM-based semantic congestion reasoning with RAG-grounded action generation
for  swarm  robotics,  (2)  an  interpretable  and  modular  decision-making  pipeline  whose  inter-
mediate reasoning steps are human-readable, and (3) empirical evidence that semantic scene
understanding can resolve failure modes intractable to purely geometric methods.

2 Introduction

Warehouse  swarm  robotics  systems,  such  as  those  deployed  by  Amazon  Robotics  (Wurman
et  al.,  2008),  must  coordinate  thousands  of  mobile  robots  through  narrow  aisles,  shared
intersections,  and  dynamic  pick  stations.  As  fleet  sizes  grow,  congestion  events—deadlocks,
livelocks, and bottlenecks, increase nonlinearly, making coordination a first-order operational
concern  (Brambilla  et  al.,  2013).  Classical  coordination  methods  each  exhibit  characteristic
failure modes in these settings: APF (Khatib, 1986) suffers from local minima and oscillation;
ORCA (van den Berg et al., 2011) exhibits the Freezing Robot Problem in constrained corridors
(Trautman & Krause, 2010); and optimal MAPF solvers like CBS (Sharon et al., 2015) are NP-
hard and computationally intractable for real-time replanning at scale (Stern et al., 2019). Even
recent congestion-aware approaches such as Asadi et al. (2025), which demonstrated up to a
doubling of throughput via CNN-based congestion prediction, remain grounded in numerical
spatial heatmaps without semantic reasoning about why congestion is occurring. As Garg et
al. (2026) demonstrated, connected multi-robot systems are inherently prone to deadlocks that
no  smooth  low-level  control  policy  can  resolve  without  external  high-level  intervention.  The
unifying limitation across all these methods is that they operate on geometric and kinematic
abstractions alone, lacking the capacity to interpret the root cause of congestion, e.g., recog-
nizing that a deadlock involves priority-mismatched robots at a single-lane intersection, or that
a bottleneck stems from a temporarily obstructed loading bay.

This proposal argues that the combination of Vision-Language Model (VLM)-based scene
understanding and Retrieval-Augmented Generation (RAG)-based action grounding (Lewis et
al., 2021) constitutes a powerful paradigm for addressing this limitation. Congestion resolution

Page 2

Vietnamese-German University
Department of Computer Science

requires  semantic  reasoning  that  transcends  geometric  computation:  understanding  task
priorities,  recognizing  spatial  patterns  indicating  incipient  deadlocks,  and  selecting  from  a
repertoire of coordination strategies (yield, reroute, convoy, wait) based on contextual factors.
A VLM can perform this reasoning over raw visual input, while a RAG module can translate
the VLM’s decisions into precise, executable commands drawn from a validated action library.

Problem Statement: Can a hybrid architecture combining a VLM for high-level semantic
congestion analysis with a RAG module for grounded command synthesis significantly improve
congestion resolution performance, measured by throughput, deadlock recovery time, collision
avoidance, and energy efficiency, over classical geometric coordination methods in simulated
warehouse swarm robotics scenarios?

3 Literature Review

3.1 Multi-Agent Coordination and Path Planning

The multi-agent coordination literature spans reactive, deliberative, and hybrid paradigms. At
the  reactive  end,  (Khatib,  1986)  introduced  Artificial  Potential  Fields,  which  remain  widely
used  due  to  their  computational  simplicity  but  are  well  known  to  suffer  from  local  minima
and oscillation. Ge & Cui (2002) proposed modifications using virtual obstacles to escape local
minima, though these introduce additional tuning parameters.

Velocity-based methods represent a significant advance. van den Berg et al. (2008) formu-
lated Reciprocal Velocity Obstacles (RVO), later refined into the Optimal Reciprocal Collision
Avoidance (ORCA) algorithm with linear-programming-based velocity selection (van den Berg
et al., 2011). ORCA provides formal guarantees of collision-free navigation under the assumption
that all agents follow the protocol, but its performance degrades in constrained topologies where
the feasible velocity space collapses. Trautman & Krause (2010) demonstrated that indepen-
dently  planning  agents  can  exhibit  the  Freezing  Robot  Problem,  where  overly  conservative
collision avoidance causes all agents to stop simultaneously.

At  the  deliberative  end,  Multi-Agent  Path  Finding  (MAPF)  formulates  coordination  as
a  combinatorial  optimization  problem  on  a  discrete  graph.  Sharon  et  al.  (2015)  introduced
Conflict-Based Search (CBS), a two-level algorithm that is optimal and complete but whose
runtime is exponential in the worst case. Subsequent work has improved scalability through
bounded-suboptimal variants such as Enhanced CBS (Barer et al., 2014) and through learning-
based heuristics (Li et al., 2021). However, MAPF solvers typically assume a static, fully known
environment and require replanning upon any dynamic change, limiting their applicability to
highly dynamic warehouse settings.

The Lifelong MAPF (L-MAPF) variant addresses continuous task assignment (Ma et al.,
2017), but scalability and real-time replanning remain open challenges. Recent work by Stern et
al. (2019) provides a comprehensive survey and standardization of MAPF problem definitions
and benchmarks.

Addressing congestion explicitly, Asadi et al. (2025) proposed a decoupled approach to the
MAPD problem that integrates local collision detection with a CNN-based global congestion
prediction module. Their method models congestion as a spatiotemporal feature matrix using
multivariate normal distributions over planned trajectories, and broadcasts periodic congestion
messages  to  agents  who  incorporate  predicted  congestion  costs  into  a  modified  A*  planner.
The  approach  demonstrated  significant  throughput  improvements,  up  to  a  doubling  at  25
agents, while maintaining agent-count-independent computational complexity. However, their

Page 3

Vietnamese-German University
Department of Computer Science

congestion prediction operates on learned spatial heatmaps without semantic interpretation of
congestion types or causes, and their conflict resolution relies on priority-based heuristics rather
than  reasoned  coordination  strategies.  Our  proposal  builds  on  their  insight  that  congestion
prediction is essential for scalable multi-agent coordination, but replaces the purely numerical
prediction  with  semantically  rich  VLM-based  scene  analysis  that  can  distinguish  between
deadlock topologies, bottleneck geometries, and anomalous events.

3.2 Vision-Language Models in Robotics

The integration of large-scale vision-language models into robotic systems represents a rapidly
growing research frontier. A foundational contribution is SayCan (Ahn et al., 2022), which
demonstrated  that  a  large  language  model  can  propose  semantically  meaningful  high-level
actions  while  a  learned  affordance  function  grounds  these  proposals  in  the  robot’s  physical
capabilities.  This  decoupling  of  semantic  planning  from  physical  feasibility  established  a
paradigm adopted by subsequent work.

RT-2 (Brohan et al., 2023) advanced this paradigm by training a Vision-Language-Action
(VLA) model end-to-end, directly mapping visual observations and language instructions to
low-level robot actions. While powerful, RT-2 requires extensive robot-interaction data and is
designed for single-robot manipulation rather than multi-agent coordination.

PaLM-E  (Driess  et  al.,  2023)  demonstrated  that  a  single  large  embodied  multimodal
model can perform visual question answering, captioning, and robotic planning within a unified
architecture,  incorporating  continuous  sensor  inputs  as  tokens  in  a  language  model.  Inner
Monologue (Huang et al., 2023) extended LLM-based planning with closed-loop feedback from
perception modules, enabling error recovery and replanning, a capability directly relevant to
dynamic congestion scenarios.

For multi-robot coordination specifically, RoCo (Mandi et al., 2023) proposed using LLMs
for  multi-robot  collaboration  through  dialogue-based  negotiation,  where  each  robot  is  repre-
sented by an LLM agent that communicates intentions and resolves conflicts through natural
language.  COHERENT  (Liu  et  al.,  2025)  introduced  a  framework  for  collaborative  LLM-
based  task  planning  with  corrective  reasoning  across  multiple  robots.  These  works  establish
the  feasibility  of  language-model-mediated  multi-robot  coordination  but  have  not  addressed
the  specific  problem  of  congestion  management  in  dense  swarm  settings  with  visual  scene
understanding.

Most directly relevant to our proposal, Garg et al. (2026) proposed a hierarchical control
framework  in  which  VLMs  serve  as  high-level  planners  for  deadlock  resolution  in
connected multi-robot systems. Upon detecting a deadlock (defined by average speed falling
below  a  threshold  while  agents  remain  far  from  goals),  their  system  prompts  a  VLM  with
a  top-view  image  of  the  environment  to  assign  a  leader  and  a  set  of  waypoints,  while  a
distributed low-level controller maintains safety and connectivity. Extensive experiments across
environments with 5 to 50 agents demonstrated that VLM-based planners (including GPT-5
and Claude Opus 4.1) outperformed A*-based planners in reach rate while requiring constant
token budgets regardless of environment complexity. Critically, their work validated that the
vision  modality  of  foundation  models  is  superior  to  text-only  LLMs  for  spatial  reasoning  in
multi-robot planning, with VLMs achieving higher scene interpretation accuracy and feasible
waypoint generation rates. However, their framework addresses only deadlock resolution
through leader-follower reconfiguration and waypoint assignment, without conges-

Page 4

Vietnamese-German University
Department of Computer Science

tion  classification,  semantic  cause  analysis,  or  retrieval-augmented  grounding  of
commands.

Complementarily, Zafar et al. (2025) presented SwarmVLM, a heterogeneous UAV-ground
robot system that uses a VLM (Molmo-7B-D) to analyze top-down environmental views and a
RAG module (using FAISS-based similarity search over a custom scenario database) to retrieve
optimal  impedance  control  parameters  for  adaptive  navigation.  Their  VLM-RAG  pipeline
achieved 80% accuracy in obstacle detection and parameter retrieval under optimal lighting,
and the overall system demonstrated a 92% success rate across 12 real-world trials. SwarmVLM
validates the technical feasibility of the VLM-RAG pipeline for robotic coordination, but targets
a  fundamentally  different  problem,  heterogeneous  leader-follower  formation  with  impedance
control for two agents, rather than congestion management in dense homogeneous swarms. Our
work extends the VLM-RAG paradigm to the more challenging setting of multi-
robot congestion detection, classification, and resolution.

VILA (Lin et al., 2024) is particularly relevant to our proposed perception pipeline, as
it  provides  a  family  of  efficient  visual-language  models  optimized  for  real-time  visual  under-
standing tasks, offering favorable trade-offs between inference latency and reasoning quality for
robotics applications.

3.3 LLM/VLM with RAG and Tool-Use in Embodied AI

Retrieval-Augmented Generation (RAG), introduced by (Lewis et al., 2021), addresses a funda-
mental limitation of parametric language models: the tendency to hallucinate facts not grounded
in training data. By augmenting generation with retrieval from an external knowledge base at
inference time, RAG produces outputs that are both contextually appropriate and factually
grounded. This property is particularly valuable in safety-critical robotic applications where
hallucinated commands could cause physical harm.

The application of RAG principles to embodied AI remains nascent but promising. Voxposer
(Huang  et  al.,  2023)  demonstrated  how  LLMs  can  compose  3D  value  maps  from  language
instructions,  effectively  retrieving  spatial  affordance  knowledge  to  guide  robot  manipulation.
While not a RAG system in the strict sense, VoxPoser illustrates the value of grounding language
model outputs in structured, domain-specific representations.

In the tool-use paradigm, Toolformer (Schick et al., 2023) showed that language models can
learn to invoke external tools (calculators, search engines, APIs) to augment their capabilities.
Applied to robotics, this suggests architectures where an LLM/VLM reasons at a high level
and delegates execution to specialized modules, precisely the architecture this proposal adopts,
with RAG serving as the grounding and retrieval tool.

SpatialVLM  (Chen  et  al.,  2024)  contributed  methods  for  spatial  reasoning  in  vision-
language  models,  enabling  quantitative  understanding  of  distances  and  spatial  relationships
from visual input. This capability is directly relevant to congestion detection, where the spatial
configuration of robots determines whether a situation constitutes a deadlock, a bottleneck, or
merely transient crowding.

No  existing  work  combines  VLM-based  visual  scene  understanding  with  RAG-grounded
action generation specifically for multi-robot congestion management in dense, homogeneous
swarms using a top-down camera setup. Garg et al. (2026) demonstrated VLMs for deadlock
resolution but without congestion classification or RAG-based command grounding. Zafar et
al. (2025) validated the VLM-RAG pipeline but in a two-agent heterogeneous setting without

Page 5

Vietnamese-German University
Department of Computer Science

congestion semantics. Asadi et al. (2025) addressed congestion prediction but through purely
numerical deep learning models without semantic reasoning. Our proposal uniquely combines
VLM-based semantic congestion analysis with RAG-grounded command synthesis for swarm-
scale warehouse robotics, addressing this convergent gap.

4 Proposed Methodology

4.1 System Architecture Overview

The proposed system employs a two-layer hybrid architecture that separates fast reactive control
from slow semantic reasoning:

• Layer 1: Local Reactive Control (20–50 Hz): Each TurtleBot3 runs a local navi-
gation stack via ROS2 Nav2, performing obstacle avoidance and path following using the
Dynamic Window Approach (DWA) local planner. This layer operates autonomously
during normal, uncongested conditions.

• Layer  2:  Global  Semantic  Reasoning  (0.5–2  Hz):  A  centralized  VLM-RAG
orchestrator monitors the scene through an overhead camera, detects congestion events,
reasons about their causes and appropriate resolutions, and issues high-level coordina-
tion commands that override or modulate local behavior.

The key architectural principle is that Layer 2 intervenes only when Layer 1 is insufficient—
i.e., when purely reactive navigation fails to resolve congestion within a defined time threshold.
This  minimizes  the  computational  overhead  of  VLM  inference  during  normal  operation  and
reserves semantic reasoning for situations that genuinely require it.

4.2 Perception and Robot ID Tracking

The perception pipeline operates as follows:

1. Image Acquisition: An overhead RGB camera (mounted at approximately 2.5–3 m height)
captures the workspace at 15–30 FPS. The camera is calibrated using a standard checker-
board procedure, and a homography matrix 𝐻 is computed to map pixel coordinates (𝑢, 𝑣)
to world-frame coordinates (𝑥𝑤, 𝑦𝑤) on the ground plane.

2. ArUco Marker Detection: Each TurtleBot3 is fitted with a unique ArUco marker (from
the  DICT_4X4_50  dictionary)  on  its  top  surface.  OpenCV’s  cv2.aruco.detectMarkers()
function identifies markers in each frame, returning marker IDs, corner pixel coordinates, and
estimated poses. The marker corners are transformed via 𝐻 to obtain world-frame positions.

3. State Estimation: For each detected robot 𝑖, the system maintains a state vector

𝒔𝑖 = (𝑥𝑖, 𝑦𝑖, 𝜃𝑖, 𝑣𝑖, 𝜔𝑖, task𝑖, status𝑖)

(1)

, where position and heading are derived from the ArUco pose estimate, velocity from finite
differences with a low-pass filter, and task/status from the ROS2 task management node.

4. Scene Annotation: Before being passed to the VLM, the raw camera frame is annotated
with  visual  overlays:  bounding  boxes  around  each  robot  colored  by  status  (green  =
moving, yellow = slow, red = stopped), robot IDs rendered as text labels, velocity vectors
drawn  as  arrows,  and  goal  positions  marked  with  target  icons.  This  Set-of-Mark-style
annotation (Yang et al., 2023) provides the VLM with structured visual cues that improve
spatial reasoning accuracy.

Page 6

Vietnamese-German University
Department of Computer Science

4.3 VLM-Based Semantic Reasoning

The annotated scene frame is passed to the VLM along with a structured prompt that elicits
congestion analysis. The VLM operates in a Think-Act reasoning loop:

Example of Think Phase — Scene Analysis Prompt:

1 You are a warehouse traffic controller. Analyze this overhead image of a robot
fleet.
2
3 [Annotated scene image]
4
5 Current robot states:
6 - Robot 1: position (2.1, 3.4), heading 90°, status STOPPED, task: deliver to
Bay 3
7 - Robot 4: position (2.3, 3.2), heading 270°, status STOPPED, task: deliver to
Bay 7
8 - Robot 6: position (1.8, 3.6), heading 180°, status SLOW, task: return to
charging
9
10 Identify:
11 1. Is there congestion? If so, classify: {deadlock, bottleneck, crowding,
anomaly}
12 2. Which robots are involved?
13 3. What is the root cause?
14 4. What coordination strategy should resolve it? Choose from:
15    {yield, reroute, convoy, priority_override, temporary_wait, reverse}
16 5. Provide a brief justification.
17
18 Respond in the following JSON format:
19 {
20   "congestion_detected": true/false,
21   "type": "...",
22   "involved_robots": [...],
23   "root_cause": "...",
24   "strategy": "...",
25   "justification": "..."
26 }

Act Phase: The VLM’s structured output (parsed as JSON) is forwarded to the RAG module
for grounding.

The VLM selection prioritizes models with strong spatial reasoning capabilities and accept-
able inference latency. Candidate models include VILA-1.5 (Lin et al., 2024) for its efficiency,
and NVIDIA Cosmos Reasoner for its spatial understanding strengths. The system is designed
to be model-agnostic at this layer, with a standardized prompt interface that accommodates
different VLM backends.

4.4 RAG-Based Action Grounding

The RAG module translates the VLM’s semantic decisions into structured, executable robot
commands. It is implemented using LangChain as the orchestration framework and Chro-
maDB as the vector store.

Knowledge  Base  Construction:  A  curated  knowledge  base  of  coordination  action

templates is constructed, where each entry contains:

Page 7

Vietnamese-German University
Department of Computer Science

• A natural-language description of the congestion scenario (e.g., “Two robots facing

each other in a single-lane corridor, both with forward-facing goals”)

• The applicable coordination strategy (e.g., “yield”)
• A parameterized command template in structured format
• Pre-conditions and post-conditions for safe execution
• Priority rules and conflict resolution heuristics

These entries are embedded using a sentence transformer (e.g., all-MiniLM-L6-v2) and stored
as vectors in ChromaDB.

Retrieval and Generation: Given the VLM’s output (congestion type, involved robots,

recommended strategy), the RAG module:

1. Constructs a retrieval query by concatenating the congestion type, strategy, and root cause

description.

2. Retrieves  the  top-𝑘  (𝑘 = 3)  most  similar  action  templates  from  ChromaDB  via  cosine

similarity search.

3. Passes the retrieved templates, the VLM output, and the current robot states to a language
model (the same VLM or a lighter LLM) with a grounding prompt that instantiates the
template with specific robot IDs, coordinates, and parameters.

Example Output — Structured Command:

1 {
2   "command_id": "CMD-20260404-001",
3   "timestamp": "2026-04-04T14:32:01Z",
4   "actions": [
5     {
6       "robot_id": 1,
7       "action": "yield",
8       "parameters": {
9         "move_to": {"x": 1.5, "y": 3.4},
10         "wait_until": "robot_4_passed",
11         "timeout_sec": 15
12       }
13     },
14     {
15       "robot_id": 4,
16       "action": "proceed",
17       "parameters": {
18         "resume_navigation": true,
19         "speed_limit": 0.15
20       }
21     }
22   ],
23   "expected_resolution_time_sec": 12,
24   "fallback": "escalate_to_operator"
25 }

4.5 Execution via ROS2

Commands  generated  by  the  RAG  module  are  published  to  a  ROS2  topic  (/coordination/
commands) as custom messages. Each TurtleBot3 runs a coordination client node that:

1. Subscribes to /coordination/commands and filters for messages addressed to its robot ID.

Page 8

Vietnamese-German University
Department of Computer Science

2. Upon  receiving  a  command,  switches  from  autonomous  Nav2  navigation  to  coordinated
mode, executing the specified action (e.g., navigating to a yield position via a local MoveBase
action, then waiting for a condition or timeout).

3. Reports  execution  status  (success,  failure,  timeout)  back  to  the  orchestrator  via  a  /

coordination/status topic.

4. Upon command completion or timeout, returns to autonomous Nav2 navigation.

A  safety  monitor  node  enforces  invariants:  minimum  inter-robot  distance  (𝑑min = 0.3 m),
maximum velocity during coordinated maneuvers (𝑣max = 0.2 m/s), and command timeout with
graceful fallback to a stop-and-wait behavior.

4.6 Data Flow Summary

The end-to-end data flow proceeds as:

Camera

RGB frame

ArUco Detection

annotated frame + states

VLM

semantic decision (JSON)

RAG Retrieval + Grounding

structured command

ROS2 Topics

TurtleBots

5 Experiments & Evaluation

5.1 Simulation Environment

All experiments will be conducted in Gazebo (or Webots as an alternative) with a warehouse
world  featuring  narrow  aisles  (width:  1.2  m,  accommodating  single-file  robot  passage),  T-
junctions,  four-way  intersections,  and  loading  bays.  TurtleBot3  Burger  models  will  be  used,
configured  with  realistic  kinematic  constraints  (max  linear  velocity  0.22  m/s,  max  angular
velocity 2.84 rad/s). Fleet sizes of 𝑁 ∈ {4, 8, 12, 16} robots will be tested to evaluate scalability.
The  overhead  camera  will  be  simulated  as  a  fixed-pose  RGB  sensor  with  a  resolution  of
1280×960 pixels.

Page 9

Vietnamese-German University
Department of Computer Science

5.2 Evaluation Scenarios

Three primary scenarios will be used, each designed to stress-test a specific failure mode of
classical methods:

1. Head-on  Deadlock:  Two  or  more  robots  approach  each  other  in  a  single-lane  corridor
from opposite directions, with goals located behind the opposing robot. Classical methods
(APF, ORCA) often fail to resolve this without external symmetry-breaking, as both robots
simultaneously attempt to yield in the same direction.

2. Intersection Bottleneck: Multiple robots converge on a four-way intersection simultane-
ously, each heading to a different quadrant. MAPF solvers can resolve this optimally but at
high computational cost; reactive methods produce oscillation or excessive waiting.

3. Dynamic Anomaly: A robot experiences a simulated malfunction (e.g., reduced maximum
speed,  erratic  heading)  in  a  critical  corridor,  creating  a  cascading  congestion  event.  This
scenario tests the system’s ability to reason about the cause of congestion (a malfunctioning
robot, not merely a crowded area) and respond appropriately (e.g., rerouting traffic around
the affected robot rather than merely waiting).

6 Expected Results & Contributions

6.1 Expected Results

Based on the capabilities demonstrated by VLMs in related robotic reasoning tasks and the
established utility of RAG for grounding, we expect the following outcomes:

• The full VLM-RAG system will achieve significantly higher throughput (estimated
15–30% improvement) over APF and ORCA baselines in deadlock and bottleneck sce-
narios, where semantic reasoning enables resolution strategies inaccessible to geometric
methods.  We  further  expect  improvements  over  the  congestion-aware  (CA)  baseline
of (Asadi et al., 2025) in scenarios requiring qualitative congestion classification (e.g.,
distinguishing  a  deadlock  requiring  coordinated  yielding  from  a  bottleneck  requiring
rerouting), as their CNN-based prediction model lacks this semantic discriminability.
• Deadlock recovery time will be substantially reduced, as the VLM can diagnose the
deadlock topology and prescribe a coordinated resolution (e.g., designating one robot
to yield) in a single reasoning step, rather than relying on stochastic perturbation or
timeout-based recovery.

• The RAG module will reduce command hallucination compared to the VLM-
only ablation, producing more reliable and syntactically valid commands by grounding
generation in retrieved, validated templates.

6.2 Contributions

The proposed research makes the following specific contributions:

• A novel hybrid architecture that integrates Vision-Language Model-based semantic
scene reasoning with Retrieval-Augmented Generation for grounded command synthesis,
applied to multi-robot congestion management—a combination not previously explored
in the swarm robotics literature.

• An interpretable decision-making pipeline in which every coordination command
is  accompanied  by  a  natural-language  justification  from  the  VLM  and  a  traceable

Page 10

Vietnamese-German University
Department of Computer Science

retrieval provenance from the RAG module, enabling human operators to audit, under-
stand, and trust the system’s decisions.

• A  modular,  ROS2-integrated  system  design  that  cleanly  separates  perception,
reasoning, grounding, and execution into independently upgradeable components, facil-
itating adoption of future VLM advances without architectural redesign.

• Empirical evidence and ablation analysis quantifying the individual and combined
contributions of semantic visual reasoning (VLM) and retrieval-augmented grounding
(RAG)  to  congestion  resolution  performance,  providing  guidance  for  future  system
design in this space.

• A curated coordination strategy knowledge base for warehouse swarm robotics,
structured for RAG retrieval, which constitutes a reusable resource for the community.

Page 11

Vietnamese-German University
Department of Computer Science

References

Ahn,  M.,  Brohan,  A.,  Brown,  N.,  Chebotar,  Y.,  Cortes,  O.,  David,  B.,  Finn,  C.,  Fu,  C.,
Gopalakrishnan, K., Hausman, K., Herzog, A., Ho, D., Hsu, J., Ibarz, J., Ichter, B., Irpan,
A., Jang, E., Ruano, R. J., Jeffrey, K., … Zeng, A. (2022, ). Do As I Can, Not As I Say:
Grounding Language in Robotic Affordances. https://arxiv.org/abs/2204.01691

Asadi,  M.,  Nowé,  A.,  &  Ghofrani,  J.  (2025).  Congestion-Aware  Multi-Agent  Path  Planning
for Pick-Up and Delivery Tasks. Proceedings of the Genetic and Evolutionary Computation
Conference, 1523–1531. https://doi.org/10.1145/3712256.3726339

Barer, M., Sharon, G., Stern, R., & Felner, A. (2014). Suboptimal Variants of the Conflict-Based
Search  Algorithm  for  the  Multi-Agent  Pathfinding  Problem.  In  T.  Schaub,  G.  Friedrich,
& B. O'Sullivan (Eds.), ECAI 2014 - 21st European Conference on Artificial Intelligence,
18-22 August 2014, Prague, Czech Republic - Including Prestigious Applications of Intelligent
Systems  (PAIS  2014):  ECAI  2014  -  21st  European  Conference  on  Artificial  Intelligence,
18-22 August 2014, Prague, Czech Republic - Including Prestigious Applications of Intelligent
Systems (PAIS 2014). https://doi.org/10.3233/978-1-61499-419-0-961

Brambilla, M., Ferrante, E., Birattari, M., & Dorigo, M. (2013). Swarm Robotics: A Review
from the Swarm Engineering Perspective. Swarm Intelligence, 7, 1–41. https://doi.org/10.
1007/s11721-012-0075-2

Brohan, A., Brown, N., Carbajal, J., Chebotar, Y., Chen, X., Choromanski, K., Ding, T., Driess,
D.,  Dubey,  A.,  Finn,  C.,  Florence,  P.,  Fu,  C.,  Arenas,  M.  G.,  Gopalakrishnan,  K.,  Han,
K., Hausman, K., Herzog, A., Hsu, J., Ichter, B., … Zitkovich, B. (2023, ). RT-2: Vision-
Language-Action  Models  Transfer  Web  Knowledge  to  Robotic  Control.  https://arxiv.org/
abs/2307.15818

Chen, B., Xu, Z., Kirmani, S., Ichter, B., Driess, D., Florence, P., Sadigh, D., Guibas, L., &
Xia, F. (2024, ). SpatialVLM: Endowing Vision-Language Models with Spatial Reasoning
Capabilities. https://arxiv.org/abs/2401.12168

Driess, D., Xia, F., Sajjadi, M. S. M., Lynch, C., Chowdhery, A., Ichter, B., Wahid, A., Tompson,
J., Vuong, Q., Yu, T., Huang, W., Chebotar, Y., Sermanet, P., Duckworth, D., Levine, S.,
Vanhoucke, V., Hausman, K., Toussaint, M., Greff, K., … Florence, P. (2023, ). PaLM-E:
An Embodied Multimodal Language Model. https://arxiv.org/abs/2303.03378

Garg, K., Nair, D. S. K., Zhang, S., Arkin, J., & Fan, C. (2026). Online Motion Planning for
Connected Multi-Robot Systems using Vision Language Models as High-level Planners. Pro-
ceedings  of  Machine  Learning  Research,  1–21.  https://mit-realm.github.io/VLM-gcbfplus-
website/

Ge, S. S., & Cui, Y. J. (2002). Dynamic Motion Planning for Mobile Robots Using Potential
Field Method. Auton. Robots, 13(3), 207–222. https://doi.org/10.1023/A:1020564024509

Huang, W., Wang, C., Zhang, R., Li, Y., Wu, J., & Fei-Fei, L. (2023, ). VoxPoser: Composable
3D  Value  Maps  for  Robotic  Manipulation  with  Language  Models.  https://arxiv.org/abs/
2307.05973

Page 12

Vietnamese-German University
Department of Computer Science

Khatib, O. (1986). Real-Time Obstacle Avoidance for Manipulators and Mobile Robots.
The International Journal of Robotics Research, 5(1), 90–98. https://doi.org/10.1177/
027836498600500106

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M.,
Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2021, ). Retrieval-Augmented Generation
for Knowledge-Intensive NLP Tasks. https://arxiv.org/abs/2005.11401

Li, J., Ruml, W., & Koenig, S. (2021). EECBS: A Bounded-Suboptimal Search for Multi-Agent
Path Finding. Proceedings of the AAAI Conference on Artificial Intelligence, 35(14), 12353–
12362. https://doi.org/10.1609/aaai.v35i14.17466

Lin, J., Yin, H., Ping, W., Lu, Y., Molchanov, P., Tao, A., Mao, H., Kautz, J., Shoeybi, M.,
& Han, S. (2024, ). VILA: On Pre-training for Visual Language Models. https://arxiv.org/
abs/2312.07533

Liu, K., Tang, Z., Wang, D., Wang, Z., Li, X., & Zhao, B. (2025, ). COHERENT: Collaboration
of Heterogeneous Multi-Robot System with Large Language Models. https://arxiv.org/abs/
2409.15146

Ma, H., Li, J., Kumar, T. K. S., & Koenig, S. (2017, ). Lifelong Multi-Agent Path Finding for

Online Pickup and Delivery Tasks. https://arxiv.org/abs/1705.10868

Mandi, Z., Jain, S., & Song, S. (2023, ). RoCo: Dialectic Multi-Robot Collaboration with Large

Language Models. https://arxiv.org/abs/2307.04738

Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Zettlemoyer, L., Cancedda, N.,
& Scialom, T. (2023, ). Toolformer: Language Models Can Teach Themselves to Use Tools.
https://arxiv.org/abs/2302.04761

Sharon, G., Stern, R., Felner, A., & Sturtevant, N. R. (2015). Conflict-based search for optimal
multi-agent pathfinding. Artificial Intelligence, 219, 40–66. https://doi.org/https://doi.org/
10.1016/j.artint.2014.11.006

Stern,  R.,  Sturtevant,  N.,  Felner,  A.,  Koenig,  S.,  Ma,  H.,  Walker,  T.,  Li,  J.,  Atzmon,  D.,
Cohen, L., Kumar, T. K. S., Boyarski, E., & Bartak, R. (2019, ). Multi-Agent Pathfinding:
Definitions, Variants, and Benchmarks. https://arxiv.org/abs/1906.08291

Trautman,  P.,  &  Krause,  A.  (2010).  Unfreezing  the  robot:  Navigation  in  dense,  interacting
crowds. 2010 IEEE/RSJ International Conference on Intelligent Robots and Systems, 797–
803. https://api.semanticscholar.org/CorpusID:6936600

van  den  Berg,  J.,  Guy,  S.  J.,  Lin,  M.,  &  Manocha,  D.  (2011).  Reciprocal  n-Body  Collision
Avoidance. In C. Pradalier, R. Siegwart, & G. Hirzinger (Eds.), Robotics Research: Robotics
Research.

van den Berg, J., Ming Lin, & Manocha, D. (2008). Reciprocal Velocity Obstacles for real-time
multi-agent navigation. 2008 IEEE International Conference on Robotics and Automation,
320. https://doi.org/10.1109/ROBOT.2008.4543489

Wurman, P. R., D’Andrea, R., & Mountz, M. (2008). Coordinating Hundreds of Cooperative,
Autonomous Vehicles in Warehouses. AI Magazine, 29(1), 9. https://doi.org/10.1609/aimag.
v29i1.2082

Page 13

Vietnamese-German University
Department of Computer Science

Yang, J., Zhang, H., Li, F., Zou, X., Li, C., & Gao, J. (2023, ). Set-of-Mark Prompting Unleashes

Extraordinary Visual Grounding in GPT-4V. https://arxiv.org/abs/2310.11441

Zafar,  M.,  Khan,  R.  A.,  Batool,  F.,  Yaqoot,  Y.,  Guo,  Z.,  Litvinov,  M.,  Fedoseev,  A.,  &
Tsetserukou,  D.  (2025,  ).  SwarmVLM:  VLM-Guided  Impedance  Control  for  Autonomous
Navigation of Heterogeneous Robots in Dynamic Warehousing. https://arxiv.org/abs/2508.
07814

Page 14


