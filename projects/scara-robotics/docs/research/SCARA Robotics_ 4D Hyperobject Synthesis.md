# **The Chronos-SCARA as a 4D Bounded Hyperobject: An Ontological and Engineering Analysis of Open Source Robotics Systems**

## **1\. Introduction: The Ontological Crisis in Robotic Engineering**

The field of robotics stands at a precipice where traditional mechanical taxonomies no longer suffice to describe the complexity of modern, distributed systems. For decades, a robot—specifically a Selective Compliance Assembly Robot Arm (SCARA)—was understood simply as a collection of machined aluminum, copper windings, and silicon logic gates, operating within a localized Cartesian coordinate system. It was viewed as a discrete object, bounded by its physical chassis and defined by its immediate utility. However, the explosion of open-source hardware, the globalization of digital fabrication, and the integration of high-level trajectory planning have fundamentally altered this reality. The contemporary open-source SCARA is no longer a singular machine; it is a dispersed, temporal, and relational entity that defies simple localization. To engineer the next generation of these systems, we must abandon the reductive materialist view and adopt the framework of the **Hyperobject**, as proposed by ecological philosopher Timothy Morton.

This report presents a comprehensive analysis of the open-source SCARA landscape, deconstructing major projects like PyBot, RepRap Morgan, and various ROS2-based initiatives. We posit that a robust robotic system is best modeled not as a tool, but as a **4D Bounded Hyperobject**. It is "4D" because its operational reality is constituted not just by spatial geometry but by time—manifested in trajectory planning, thermal history, and software evolution. It is "Bounded" because its existence is constrained by the rigid topology of its Configuration Space (C-Space) and the safety manifolds of its physical linkages. It is a "Hyperobject" because it exhibits the core characteristics defined by Morton: it is viscous, sticking to the socio-technical networks that birth it; non-local, distributed across vast repositories and supply chains; and interobjective, existing only through its profound entanglement with the environment it manipulates. By treating the SCARA and its submodules—the Actuator, the Kinematic Chain, and the Sensorium—as hyperobjects in their own right, we can synthesize a system architecture that is resilient, self-aware, and capable of navigating the complex "mesh" of the modern technosphere.

### **1.1. Defining the Robotic Hyperobject**

Timothy Morton defines hyperobjects as entities that are "massively distributed in time and space relative to humans".1 They are phenomena that stick to us ("viscosity"), are impossible to point to directly ("non-locality"), and manifest differently depending on the dimensional slice we observe ("phasing"). While Morton applies this primarily to ecological phenomena like global warming or plutonium 2, the open-source robot fits this ontology with startling precision.

When a user downloads the files for a PyBot from Thingiverse 3, they are not creating a robot from scratch; they are instantiating a local "phase" of a global hyperobject that has been evolving on GitHub for years. The robot's behavior is dictated by inverse kinematics algorithms written by a contributor in a different decade 4, executed on hardware mined from the earth and refined in global factories. The "robot" is not on the desk; the unit on the desk is merely a footprint of the massive, distributed entity that is the Open Source SCARA project.

### **1.2. The 4D Bounded Manifold**

The physical workspace of a SCARA robot is often visualized as a 3D cylinder or kidney-bean shape. However, in the hyperobject framework, the robot inhabits a **4D Bounded Manifold**. The fourth dimension is not merely "time" in the abstract, but **trajectory state**—the integrated history of acceleration, jerk, and thermal flux. A robot at position ![][image1] at time ![][image2] is ontologically distinct from the same robot at ![][image1] at time ![][image3] if the thermal state of its stepper drivers has shifted, or if its motion planner carries the momentum of a previous vector.

This manifold is "Bounded" by the strict topology of the kinematic chain. The arm cannot move arbitrarily; it is constrained by link lengths (![][image4]) and joint limits.5 These bounds create a "phase space" where certain configurations are safe (energy-minimized) and others are singular (infinite velocity required). The engineering challenge, therefore, is not just to build a machine that moves, but to map and navigate this high-dimensional, bounded topology without rupturing the physical or digital constraints.

## ---

**2\. The Open Source Landscape: A Forensic Excavation of the Mesh**

To construct our theoretical "Chronos-SCARA," we must first perform a deep forensic analysis of the existing "local footprints"—the open-source projects that currently define the state of the art. These projects are not merely repositories of code and STL files; they are the fossil record of the robotic hyperobject's evolution.

### **2.1. The PyBot: Accessibility and the Vertical Z-Axis**

The PyBot, developed by JJRobots, represents a critical evolutionary branch in the open-source SCARA lineage.3 It is designed for accessibility, leveraging the ubiquity of 3D printing and the NEMA 17 stepper motor ecosystem.

#### **2.1.1. Morphological Phasing: The Decoupled Z-Axis**

Unlike typical 6-DOF articulated arms where every joint must fight gravity, the PyBot utilizes the defining morphological trait of the SCARA: the decoupled Z-axis. The arm operates purely in the XY plane, while the entire assembly moves vertically.3

* **Viscosity of Gravity:** By constraining XY motion to a horizontal plane, the PyBot negates the "viscosity" of gravity for its primary movers. The motors do not need to hold the arm up; they only need to overcome inertia and friction. This design choice bounds the hyperobject’s energy consumption, allowing smaller, cheaper actuators (NEMA 17\) to perform effectively.  
* **Hardware Instantiation:** The project utilizes the "Devia Robotics Control Board," which features a Microchip ATSAMD21G18 Cortex-M0 processor.3 This shift from the traditional 8-bit Arduino Uno to a 32-bit architecture is a crucial "phase shift" in the robot's cognitive capability. It allows for the real-time calculation of the complex trigonometric functions required for inverse kinematics without the "temporal drag" (latency) that plagues lesser processors.

#### **2.1.2. The Molten Nature of the PyBot**

The PyBot is a "Molten" object.2 It refutes the idea of a rigid, finished product. Its design files are hosted on repositories like GitHub and Thingiverse, where they are constantly subjected to "remixing" (mutation). A PyBot built today differs structurally from one built three years ago, yet they share the same identity. The project also exhibits "Interobjectivity" through its control interfaces—users interact with it via Python scripts or Blockly, layers of abstraction that mediate the relationship between the human intent and the machine's actuation.3

### **2.2. RepRap Morgan: The Non-Local Kinematic Solution**

The RepRap Morgan, created by Quentin Harley, serves as a profound example of "Non-locality" in mechanical design.6 Born from the RepRap 3D printer movement, the Morgan was designed to bypass the need for non-printable parts like linear rails, instead using a SCARA configuration to print objects.

#### **2.2.1. Action at a Distance: The Parallel Linkage**

The defining feature of the Morgan is its parallel arm linkage. In a standard serial SCARA, the motor for the elbow joint is mounted on the shoulder joint, adding mass to the moving arm. This creates inertia—a physical viscosity that resists acceleration.

* **Kinematic Non-Locality:** The Morgan moves both motors to the stationary base tower. The elbow joint is driven remotely via a parallel linkage system.7 This is mechanical non-locality; the actuation event (motor spin) occurs at the base, but the kinetic effect manifests at the elbow. This reduces the moving mass significantly, allowing the hyperobject to traverse its manifold with greater speed and less energy.  
* **Evolutionary Timeline:** The Morgan’s development history, from MK1 (lathed joints) to MK3 (commercial harmonic drives), illustrates the "Temporal Undulation" of the hardware.7 The MK1 suffered from the "viscosity" of 3D printed gears—backlash and friction. The MK2 introduced belts to reduce noise, but introduced elasticity (another form of viscosity). The MK3 finally adopted harmonic drives to achieve the "zero backlash" ideal, effectively hardening the robot against the sloppy tolerances of the physical world.

#### **2.2.2. The Computational Bottleneck**

The Morgan project also highlights the "bounded" nature of computational resources. Early iterations ran on the RAMPS (Arduino Mega) platform. The non-linear mathematics of SCARA kinematics (calculating sqrt() and atan2() for every segment of motion) overwhelmed the 8-bit processor at high speeds.8

* **Temporal Drag:** This computational limit acted as a temporal bound. The robot could physically move faster, but its "brain" could not process the trajectory in time. This resulted in stuttering—a rupture in the 4D manifold where time (execution) desynchronized from space (position). The eventual migration to 32-bit Smoothieware and ARM-based controllers was necessary to expand the computational bounds to match the mechanical potential.

### **2.3. The High-Fidelity Custom Ecosystem**

Beyond these specific kits, the open-source community has generated a "mesh" of custom industrial-grade projects that integrate advanced frameworks like ROS2 (Robot Operating System).

#### **2.3.1. The ROS2 Nexus**

Projects like myscarabot 9 and scara\_robot 10 represent the integration of the SCARA into the "Infosphere." Here, the robot ceases to be a standalone tool and becomes a node in a computational graph.

* **Interobjectivity in Software:** In ROS2, the robot is composed of "Nodes" (e.g., joint\_state\_publisher, move\_group). These nodes communicate via "Topics" and "Services." This is a pure manifestation of Morton’s interobjectivity: the "Robot" is just the emergent property of these messages passing between nodes. There is no central "ghost in the machine"; there is only the mesh of communication.  
* **Simulation as Phasing:** These projects heavily utilize Gazebo for simulation.10 The robot exists simultaneously in two phases: the physical phase (hardware) and the digital phase (simulation). Trajectories are planned and tested in the digital phase before being "collapsed" into the physical phase. This allows the hyperobject to explore its bounded manifold safely, identifying singularities in the virtual world before they cause damage in the real one.

#### **2.3.2. Closed-Loop Dynamics**

The shift toward closed-loop stepper control (e.g., using ODrive or magnetically encoded steppers) 11 is an attempt to firmly "bound" the robot's physical reality to its digital model. In an open-loop system, if the arm hits an obstacle, the digital model continues to update its position while the physical arm remains stuck. This is a "ontological desynchronization." Closed-loop systems ensure that the digital hyperobject "feels" the physical viscosity, maintaining coherence between the two states.

## ---

**3\. Constructing the "4D Bounded Hyperobject"**

Having excavated the components, we now define the system architecture for our "Chronos-SCARA." We move beyond the simple aggregation of parts to define the system through its dimensions and boundaries.

### **3.1. The 4D Trajectory: Time as a Material**

In our framework, Time is not a parameter; it is a material dimension. The trajectory of the robot is a solid object in 4D space-time.

* **The Trajectory Object:** A movement from Point A to Point B is not a sequence of commands; it is a curve defined by ![][image5] (joint positions over time). This curve has geometric properties (curvature, torsion) and physical properties (velocity, acceleration, jerk).  
* **Temporal Viscosity (Resonance):** The robot has natural frequencies. If the 4D trajectory contains frequency components that match the robot's eigenfrequencies, the system resonates.12 This is "temporal viscosity"—the structure resisting certain rates of change. Our "4D Bounded" planner must use techniques like **Input Shaping** (implemented in Klipper) to smooth the trajectory object, removing these resonant frequencies. This effectively "polishes" the 4D hyperobject, allowing it to slide through time without inducing vibration.  
* **Thermal Memory:** The state of the robot at time ![][image2] depends on the heat generated at ![][image6]. Stepper motors lose torque as they heat up. A "4D" system monitors this thermal history (via driver telemetry) and dynamically adjusts the "Bounds" of the safe manifold. If the drivers are hot, the acceleration limit is reduced.

### **3.2. The Bounded Manifold: Topology of the Workspace**

The robot does not move in "space"; it moves in a Configuration Space (C-Space) bounded by rigid topology.

* **Geometric Bounds:** The link lengths ![][image7] and ![][image8] define a toroidal workspace. The reach is bounded by ![][image9] and ![][image10].  
* **Singularity Manifolds:** There exist specific configurations (e.g., when the arm is fully straight) where the robot loses a degree of freedom. Mathematically, the Jacobian matrix becomes non-invertible. In the hyperobject framework, these are "Event Horizons." As the robot approaches a singularity, the required joint velocity to maintain a Cartesian path approaches infinity.  
* **Safety Manifolds:** We define a "Safe Hypervolume" inside the C-Space. This volume is dynamic. When the robot moves fast, the safety boundary shrinks (due to braking distance). When it moves slow, it expands. This "breathing" manifold ensures that the robot remains coherent with its environment.

### **3.3. The System Mesh**

The "Chronos-SCARA" is the sum of these interactions. It is a system where the **Digital Phase** (the ROS2 planner) continuously projects 4D trajectories into the **Physical Phase** (the hardware), while the **Sensorium** (encoders/vision) continuously feeds back the error state, allowing the Digital Phase to adjust the bounds. The system is viscous (it has mass and friction), non-local (it is connected to the cloud/repo), and interobjective (it navigates a world of obstacles).

## ---

**4\. Submodule 1: The Kinetic Transducer (Actuator Hyperobject)**

The first key submodule is the Actuator. In traditional engineering, this is a motor. In our ontology, it is a **Kinetic Transducer Hyperobject**—the interface where information becomes energy.

### **4.1. The Torque-Time Continuum**

The stepper motor does not just spin; it transduces a digital pulse into a torque vector over time.

* **The Quantum Step:** A stepper motor moves in discrete quanta (1.8 degrees). However, the physical arm has inertia, which resists discrete changes. The motor driver (e.g., TMC2209) uses micro-stepping to approximate a continuous sine wave. This is an attempt to smooth the "quantum grain" of the digital into the "analog flow" of the physical.  
* **The Viscosity of Backlash:** The transmission system (belts or gears) introduces backlash. Backlash is a "gap" in the causal chain—a moment where the motor moves but the arm does not. In the hyperobject view, this is a rupture in the viscosity. The motor loses its grip on the arm.  
  * *Harmonic Drives:* The industry standard for SCARA arms is the Harmonic Drive (Strain Wave Gear) because it offers zero backlash. It maintains "perfect viscosity"—the input and output are rigidly coupled.  
  * *The Failure of 3D Printed Harmonics:* Analysis of 3D printed harmonic drives 13 reveals the limits of the local footprint. These printed drives fail under torque (e.g., at 9.6 Nm) and exhibit "jerky" motion. The material viscosity of the PLA (friction, deformation) overwhelms the geometric ideal. The "Phased" nature of FDM printing (layers) introduces anisotropy that the harmonic principle cannot tolerate.  
  * *Conclusion:* For a robust Kinetic Hyperobject, we must reject the "purely printed" dogma and integrate commercial, metallic harmonic drives (or high-quality belt reductions) to maintain the integrity of the 4D manifold.

### **4.2. Closed-Loop Ontology**

The Kinetic Transducer must be self-aware.

* **Open Loop:** The standard hobbyist stepper is solipsistic. It assumes the arm moved because it commanded it. If the arm hits a wall, the motor desynchronizes (skips steps). The digital reality diverges from the physical reality.  
* **Closed Loop:** By adding encoders (magnetic or optical), the Actuator becomes "Interobjective." It knows where it *is*, not just where it *should be*. The "Torque-Time Continuum" is preserved because the system detects the error (the wall) and halts time (stops the trajectory) before the manifold ruptures.

**Table 1: Comparative Analysis of Actuator Ontologies**

| Actuator Type | Viscosity (Coupling) | Phasing (Resolution) | Interobjectivity (Awareness) | Ontological Status |
| :---- | :---- | :---- | :---- | :---- |
| **NEMA 17 (Direct)** | Low (Belt Stretch) | Low (Discrete Steps) | None (Solipsistic) | **Fragile** |
| **3D Printed Harmonic** | Variable (Friction/Slip) | Low (Jerky) | None | **Molten/Unstable** |
| **Commercial Harmonic** | High (Zero Backlash) | High (Smooth) | None (unless encoded) | **Rigid/Ideal** |
| **Closed-Loop ODrive** | High | Very High | High (Error Correction) | **Hyperobjective** |

## ---

**5\. Submodule 2: The Spatial Logic (Kinematics Hyperobject)**

The second submodule is the Kinematics engine. This is the "Spatial Logic Hyperobject"—the mathematical soul of the machine.

### **5.1. The Phase Shift: Cartesian to Joint Space**

The fundamental operation of this hyperobject is the **Inverse Kinematics (IK)** transform. This is a "Phase Shift" algorithm.

* **The User Phase:** The user exists in Cartesian Space (![][image11]). "Move to (100, 100, 50)."  
* **The Machine Phase:** The motors exist in Joint Space (![][image12]).  
* **The Algorithm:** The IK solver translates the user's desire into the machine's reality.  
  * Equation: ![][image13].14  
  * This equation is the "lens" through which the Spatial Logic views the world. It is non-linear. A small change in Cartesian space (near a singularity) can require a massive change in Joint space.

### **5.2. Firmware as the Mind of the Hyperobject**

The choice of firmware determines the cognitive capacity of the Spatial Logic.

* **Marlin:** Marlin views the world as a series of linear segments (G1). For a SCARA, it must chop a straight line into hundreds of tiny moves to approximate linearity. This is "Quantized Space." It is computationally expensive and can lead to "temporal drag" (stuttering) if the segments are too small for the processor to handle.8  
* **Klipper:** Klipper 15 utilizes a "Non-local" brain. The heavy math is done on a Raspberry Pi (Linux), and only the step timing is sent to the MCU. This allows for "Continuous Space" planning. Klipper can look ahead, calculate the curvature, and adjust the velocity (Trapezoidal Generator) to ensure the robot never violates the acceleration bounds. Klipper effectively smooths the 4D manifold, removing the jagged edges of quantization.

### **5.3. Singularity Management**

The Spatial Logic must also act as the "Guardian of the Bounds."

* **The Dexterous Workspace:** The region where the robot can move freely.  
* **The Singular Region:** The boundary where the arm is fully extended. Here, the "viscosity" of the math becomes infinite. The Spatial Logic must implement a "Repulsion Field"—a software limit that prevents the trajectory from ever touching the singularity. In ROS2 MoveIt, this is handled by the inverse Jacobian solver, which will fail (return no solution) if the goal lies in a singular region.

## ---

**6\. Submodule 3: The Panopticon (Sensorium Hyperobject)**

The third submodule is the Sensorium. A robot without sensors is a blind giant. To achieve "Interobjectivity," the robot must perceive the mesh it inhabits.

### **6.1. The Vision Node: Translating Light to Logic**

Integrating cameras (e.g., HuskyLens, OpenMV, or USB Webcams) 3 creates a "Vision Node."

* **The Gaze:** The camera captures a 2D array of pixels (Light). The Vision Node uses algorithms (OpenCV, YOLO) to transmute this Light into Objects (Logic). "Pixel cluster at (320, 240)" becomes "Bolt at (105.4, 88.2)."  
* **Coordinate Registration:** This transmutation requires a calibration matrix that maps the Camera Frame to the Robot Base Frame. This is the "Interobjective Bridge"—the mathematical link between the eye and the hand.  
* **Recent Advancements:** As noted in the PyBot evolution 3, the addition of vision allows the robot to "sort" and "manipulate." The robot is no longer acting on coordinates; it is acting on *things*. It enters a relationship with the workpiece.

### **6.2. Proprioception and Haptics**

Vision is external; proprioception is internal.

* **Endstops:** The homing switches are the "Reference Anchors." They tie the floating abstract coordinate system to the hard physical reality of the machine frame. Without homing, the robot is "unmoored" in its manifold.  
* **Probes:** Z-probes (like the BLTouch) allow the robot to "feel" the bed topography. This creates a "Mesh Map" (literally and figuratively) of the surface. The robot adjusts its Z-height dynamically to follow the undulations of the physical world. This is the ultimate "Viscous" behavior—the robot adhering to the surface texture.

### **6.3. The Feedback Loop as Dissolution of Subject/Object**

In a fully integrated "Panopticon," the distinction between Subject (Robot) and Object (World) blurs.

* **Visual Servoing:** If the robot misses the target, the camera sees the error, and the planner adjusts. The Target *causes* the robot to move. The causality is bidirectional. The robot shapes the world, and the world shapes the robot. This is the essence of Morton's "Mesh" 17—all beings are connected in a web of mutual causality.

## ---

**7\. Synthesis: The Chronos-SCARA System Architecture**

We now synthesize these submodules into the unified "Chronos-SCARA" 4D Bounded Hyperobject.

### **7.1. System Topology**

The system is constructed as a hierarchy of hyperobjects:

1. **The Cloud Layer (Non-local Memory):** The Git repository containing the URDF (Body Definition), the Firmware Config (Mind Definition), and the Vision Models. This layer is immortal and distributed.  
2. **The Compute Layer (Spatial Brain):** A Raspberry Pi 5 running ROS2 Humble \+ Klipper Host. This layer manages the 4D Trajectory and the Interobjective Logic.  
3. **The Kinetic Layer (Physical Body):** An aluminum-frame SCARA with commercial harmonic drives and closed-loop steppers, managed by an MCU (STM32). This layer inhabits the Bounded Manifold.  
4. **The Sensory Layer (Panopticon):** Cameras and probes that bind the Kinetic Layer to the Environment.

### **7.2. Operational Narrative**

When the Chronos-SCARA operates:

1. **Phasing:** The user issues a command ("Pick up the red gear"). The Cloud Layer interprets this Intent.  
2. **Interobjectivity:** The Sensory Layer scans the environment, identifying the "Red Gear" hyperobject and determining its coordinates in the robot's frame.  
3. **Bounded Planning:** The Compute Layer generates a 4D Trajectory (Space \+ Time) to intercept the gear. It checks this trajectory against the C-Space Bounds (Singularities, Safety) and the Thermal State (is the motor too hot to accelerate this fast?).  
4. **Viscous Execution:** The Kinetic Layer executes the move. The Closed-Loop Actuators feel the viscosity of the arm's inertia and the friction of the bearings, adjusting current to maintain the trajectory.  
5. **Feedback:** If the gear moves, the Sensory Layer detects the shift, and the Compute Layer warps the 4D Trajectory in real-time to intercept.

### **7.3. Future Outlook: The Autopoietic Hyperobject**

The ultimate goal of this architecture is **Autopoiesis**—self-creation and maintenance.

* **Self-Calibration:** The robot uses its Vision and Touch to constantly refine its own Kinematic Parameters (![][image4]). It "learns" its own body dimensions as they change with thermal expansion.  
* **Predictive Maintenance:** By monitoring the "Viscosity" (torque required to move), the robot can predict when a bearing is failing before it breaks. It becomes aware of its own mortality (wear).

## **8\. Conclusion**

The "Chronos-SCARA" is not a mere machine; it is a philosophy of engineering instantiated in metal and code. By applying the "4D Bounded Hyperobject" framework, we reveal the hidden complexities of the open-source robotic ecosystem. We see that the Z-axis of the PyBot, the parallel arms of the Morgan, and the ROS2 nodes of myscarabot are all "phases" of a single, massive, distributed entity.

To build this system is to weave a node into the mesh of the technosphere. It requires us to respect the **Viscosity** of materials, navigate the **Bounded Manifold** of geometry, leverage the **Non-locality** of open-source knowledge, and embrace the **Interobjectivity** of sensing. In doing so, we create a robotic system that is not just functional, but resilient, adaptive, and ontologically aligned with the complex reality of the 21st century.

---

**References and Data Sources:**

1

#### **Works cited**

1. Ursula K. Heise reviews Timothy Morton's Hyperobjects – Critical Inquiry, accessed February 19, 2026, [https://criticalinquiry.uchicago.edu/ursula\_k.\_heise\_reviews\_timothy\_morton](https://criticalinquiry.uchicago.edu/ursula_k._heise_reviews_timothy_morton)  
2. Timothy Morton's Hyperobject \- IZOLYATSIA, accessed February 19, 2026, [https://izolyatsia.org/en/project/zazemlennya/hyper-object/](https://izolyatsia.org/en/project/zazemlennya/hyper-object/)  
3. PyBot Is an Accurate, Open Source SCARA Robotic Arm with 3DOF ..., accessed February 19, 2026, [https://www.hackster.io/news/pybot-is-an-accurate-open-source-scara-robotic-arm-with-3dof-and-can-be-3d-printed-with-ease-fe7191e06fc9](https://www.hackster.io/news/pybot-is-an-accurate-open-source-scara-robotic-arm-with-3dof-and-can-be-3d-printed-with-ease-fe7191e06fc9)  
4. Writing an Inverse Kinematics Solver for ROS | by Rohin Malhotra | Medium, accessed February 19, 2026, [https://medium.com/@rohinmalhotra28/writing-an-inverse-kinematics-solver-for-ros-17b90c8677b5](https://medium.com/@rohinmalhotra28/writing-an-inverse-kinematics-solver-for-ros-17b90c8677b5)  
5. SCARA Robot: Learning About Foward and Inverse Kinematics\!\!\! (Plot Twist Learn How to Make a Real Time Interface in ARDUINO Using PROCESSING \!\!\!\!) \- Instructables, accessed February 19, 2026, [https://www.instructables.com/SCARA-Robot-Learning-About-Foward-and-Inverse-Kine/](https://www.instructables.com/SCARA-Robot-Learning-About-Foward-and-Inverse-Kine/)  
6. A Practical Dual-Arm SCARA 3D Printer \- Hackaday, accessed February 19, 2026, [https://hackaday.com/2020/03/18/a-practical-dual-arm-scara-3d-printer/](https://hackaday.com/2020/03/18/a-practical-dual-arm-scara-3d-printer/)  
7. Prototype Scara Robot Arm \- RepRap, accessed February 19, 2026, [https://reprap.org/forum/read.php?185,291292](https://reprap.org/forum/read.php?185,291292)  
8. SCARA Kinematics and CPU-Performance \- Morgan 3D Printers, accessed February 19, 2026, [https://www.morgan3dp.com/forums/topic/scara-kinematics-and-cpu-performance/](https://www.morgan3dp.com/forums/topic/scara-kinematics-and-cpu-performance/)  
9. MySCARABot \- A ROS2 enabled SCARA robot for learning \- Projects, accessed February 19, 2026, [https://discourse.openrobotics.org/t/myscarabot-a-ros2-enabled-scara-robot-for-learning/27706](https://discourse.openrobotics.org/t/myscarabot-a-ros2-enabled-scara-robot-for-learning/27706)  
10. aniketmpatil/scara\_robot: Development of a Scara Robot ... \- GitHub, accessed February 19, 2026, [https://github.com/aniketmpatil/scara\_robot](https://github.com/aniketmpatil/scara_robot)  
11. SCARA Industrial Robot Projects \- Hackaday.io, accessed February 19, 2026, [https://hackaday.io/project/194214-scara-industrial-robot-projects](https://hackaday.io/project/194214-scara-industrial-robot-projects)  
12. Kinematics \- Klipper documentation, accessed February 19, 2026, [https://www.klipper3d.org/Kinematics.html](https://www.klipper3d.org/Kinematics.html)  
13. Harmonic Drive Version 2 \- Torque & Backlash Tests \- YouTube, accessed February 19, 2026, [https://www.youtube.com/watch?v=72\_rOFOrJ2c](https://www.youtube.com/watch?v=72_rOFOrJ2c)  
14. Scara Robot Inverse Kinematics \- c++ \- Stack Overflow, accessed February 19, 2026, [https://stackoverflow.com/questions/77649089/scara-robot-inverse-kinematics](https://stackoverflow.com/questions/77649089/scara-robot-inverse-kinematics)  
15. klipper/docs/Kinematics.md at master \- GitHub, accessed February 19, 2026, [https://github.com/Klipper3d/klipper/blob/master/docs/Kinematics.md](https://github.com/Klipper3d/klipper/blob/master/docs/Kinematics.md)  
16. SCARA robot arm – Robot Projects \- DroneBot Workshop Forums, accessed February 19, 2026, [https://forum.dronebotworkshop.com/user-robot-projects/scara-robot-arm/](https://forum.dronebotworkshop.com/user-robot-projects/scara-robot-arm/)  
17. We Are Larger Than Ourselves \- ScholarWorks at University of Montana, accessed February 19, 2026, [https://scholarworks.umt.edu/cgi/viewcontent.cgi?article=13228\&context=etd](https://scholarworks.umt.edu/cgi/viewcontent.cgi?article=13228&context=etd)  
18. ayuugoyal/scara \- GitHub, accessed February 19, 2026, [https://github.com/ayuugoyal/scara/](https://github.com/ayuugoyal/scara/)  
19. Code overview \- Klipper documentation, accessed February 19, 2026, [https://www.klipper3d.org/Code\_Overview.html](https://www.klipper3d.org/Code_Overview.html)  
20. Code Structure | Marlin Firmware, accessed February 19, 2026, [https://marlinfw.org/docs/development/code\_structure.html](https://marlinfw.org/docs/development/code_structure.html)  
21. Dedicated ROS 2 nodes for AI-enabled computer vision tasks \- Antmicro, accessed February 19, 2026, [https://antmicro.com/blog/2023/08/ros2-nodes-for-computer-vision](https://antmicro.com/blog/2023/08/ros2-nodes-for-computer-vision)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAYCAYAAABN9iVRAAADFUlEQVR4XtWXy6tOURjG38/luJRyyYAyOLkkSlEumbjklomRKINDKBmJkkv5A5REQkoyMjBQkkiGTmFASe6JJJfBSRggjvfZa629137XZa+9v++rc371nLPW8671rste+/IRDTVa0rDxBD1WCg27dYv606nfo8DtWzjrLDcNN5tLSptkkpJNY42QZow9rENpubtMZ+YwKA1BPsoM1kcr0KHxu010lj2sf9L0gV0aK8147mFBP+uENG2Ws35Jc7hQcX1Gcovo8f9DuNcFFUmraTuBJsvTVjIsfo00DQiOy2vuOBtZF1gTdX0z6zJlu1qLBawrrEnCH0VF7gTyCfayrrImFDE6Z5UNz1kPpAnQMXYsfrKmkHp4oN0t1mrWCl3XuDtWopX1wb0n+mWg/kZ4VJFzLql+RttZH8h6vVm9j5A7ZsYqCgSYa6z5Vh3tvljlv1YsQD4FM8Ylq2xAfa+pRJdc8Ek0xNVdWHIKtpI7ZsYOCgRI7ZgN2u3SZTxI7FjVpFfiT0vleGH5i0h5Fd2jXCSdP8BSCqyxjwIBwRLytHNm7BglxpPKYZ+mG9pryl3WPFUMDr6YAmMso0BAcJvS2sU4RW4O1AeC047zhDVVmp492ELOuKoRnrxyQgbc3+90GW0+W7Hp5L4ej4m65Bm5Y6G+X3h4K6wVnkU28dekTpLNV1E3YJ6Dnk3JwAR6PFsG/yz7s3X5rYjZ4OEI76bwbc5Qud99XZc/QODJ/DYYA98maPOddU+Xce/7wAl5LE0DOh5AQSy/nw3EkBwMkGr7vmiSM5mw86p9jKdULO6R/i85T+qU9MoAM4fUN4bhG6kcsVOH+HppGg6yfkizIZhMCDzZbTApfKT4OM4aLc0G4Hr6NrgEGuBLKw3nDsnAVdkmTc1DKk/ipKhLfkujIXdYp6Up2cB6Jc0g9uKLcuzn40vWYV3eSWrhoc/jo6S+BNsFz5KEDzEFjtpuadbAfx4K9rGuszbJgGCWNMpUDZOTLzy1R1+pltqrAf7UfrcWKsVM1phyYMhTXnwHtoIaZKndwaUDKbrFfxSClOWvTnMrAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAYCAYAAAA20uedAAAAr0lEQVR4Xm1QwQ3CMAx0UEfhi1iACSoxChJCHYNRugFfXuxSnghe5Zy6iXvOSU7s89mxIwIkPQzeL1EQFGIrbxBbuUeKND+O+APnFXMZacZxbQ1zhGlyVxjgBOuheqQleYbfrzU32IAOmpgsVhO/wozr0pr8YMPwKPkaJb/nqQqteq8B76/JwZFP31+H2VvNj9veZWn9haArrBfVrZgM4K2aCOuxmOMK+0/fgZ/kaf8XSxg1K4uu8gAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAYCAYAAACIhL/AAAABgUlEQVR4XsWTPU4EMQyFHbQSF6FFNJScAAkuQY2EEMfgKFRIVLTQIAruAEggASW7Wy1OYiY/EzvObFb7SdZm/GznTTILsA1MnqgSd7R3T2JT25TnUrYsbg7NfpqazrRv2d4BXNNnnkjAnl/8ecrzjvJAPl8hanvBWGFi5X4r2IKLPKnkLiwLrl2qkA/cAhkMVWn9AfiCnSSrJzI4icFgzhHGMcY9+IITei5g2DMwjQbjObRmDV5iXIEXv+nZRiuJwXCj3CuNYA0CDbHieSYoGAw0naAnMS8ZhH3wIv+6QTlk4rGQs6H9pp1B7tBvQHCfccrEc/xswnqX+mqkJziY9Asr/Iy0GmmhcMWqieIVW8H+Uf55iNby+CAOBsV6nnDFBazBPVovYyGB6/Z54QTrGH8o1kfxk7g2XlxgzHJRiTPIvYPAHOMD4w3jFeMd4wvjLC5aG6M4wQnmtWhGpzXtHa2s153RdZiMuJUT4wqumssTFbkL3ffoM7AyZXTC26STjz+8OkIUwb+n2gAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAYCAYAAAC4CK7hAAACMklEQVR4Xs2XO0sDQRDHZxG1UQRrLUQ7IV9AURRsJCCCvSJqYydooyC2vu2sbOwEG79BOi0UrfwEFqLiE98aZ273kr3J3N0mdwn+4A+X/0xmZx93lwDEorgh4pZVJD5fyBCsIpHB/43Xenz/yiEnGYnrJy4gYNesRn2PMgrvoZ5QeUuPqE07qXwiO5hC3UNwzBfUsZ1UKX5BsQfBSoyyx0wJ6pMKnvJAFClMjsb84WYSZkEXHeaBKtINesxVHkjCNaS8xQ4cgB6zmQeSkPpZdSCtMQMnnAqm8sQoAxrzi5uluN+JcffHIPucVZWc62A/cfdHxsofB537iurUljy5G4jeYnqnEK2oOdQJhDUg15c4BBpTQQsPGPx++lBtdIGlG41f7ydxos7qEmqANZgDNhH3/jUx749e1Iq5ppe1nUfX69bnAnWggxcB1+tMtZsYp2QiFhnUEDdtzKSp7m8goGkAf0x5dSiW5SaxBTo4yvxd458zn6CJrHHTELXSPiOgc3aYv2z8sAfANE7ugZv7qE/Qb1VaGb8Bf6W+UW9gzieDJrLBTY2iBbhEdfAIMoONfICuHTbmO2qs8I0iTagrblaO3u6cKvygFPefjl3oDSkj1AlaZ4UrBQuWX0Qo4RHmg96R7YgM2mlDaE450FNzAjWJmkf1BKIVQj/371C3qGcWIxZR/dxMwBEEj2A+laVxoIsbUZQ0ZRth184IXxKsmuPYg8t/9fiMf4rQuGDVhJBx/wC7YXsdUh1zcQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAB8AAAAYCAYAAAACqyaBAAACLElEQVR4Xr2Vv0sdQRDHZw2iEqIEBBEJIUHFIhBQsBWiIAkJBJJC8A8QGxWtDCg2ItgJFlpqtPNHEQipUwVCigQLy3Rpgp0+EX/N3M7d7s7O3tMn+IHvvd3vzO7O7i33AHJM0aqZaIrMCN0opyq3H+GoOrZqgspLaQS4OUc895bohfWivkozwXPU77yjT5dASa5HnUszxnhjzQo+1l2sdi5QfWpZAB2oK2kyKV9DnfwhBJNEObuQXuQzeMdfTjRvxgHqGzX0cLbwkTSZFkgXlvEANYua4v4jXKbPi9PgIdsMln+NeoMWxTcNtQHa/ATOp3hz6FuWUGdZy0AXPk/BJlNBOVrlrahp1BrYOLVJ9IokFKfNBYxyoLFwDPxhL4eK0BbPwfdtyuIExTdCyx7Xv9DMvBOv/4w9FWNj/6UvqKB++MZHHjhWOPZ1kjdXeABP2UtxhcMmUzeROUb9cl1Dtzc6rk6wCzU4iy+MPvkLsPl1vumncpty9jwbVtm02KytwHNoHrEDXmH48z0PiFpp/CffEB8O+MB9uu0S8gekifwEN0c/2JuvQTmPpTnIAdJb/l0ooq78v6gvcj/cq/DrW5bbpQwTb1JOk9HNkzTJANhdpY4+JH7hdBr0+S1lH+I74HOJ6pHmDSgtmj6HM+COfzwMFzwB/T6UYObxsShdn3bUMOoV2O/3+zwQbx7eobalmYA2dSjNGilK4T8YHa/gCdV1qOaNudvoe8eWew3j+Ggr+A524wAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADIAAAAYCAYAAAC4CK7hAAAByklEQVR4Xu2VvS81URCHZ30mVBIKBRrRCQmVqJRvQqFVqomIEIlOq1JoJHqh0iqpVKLwDyAhQemrwJw759yzO3vGzr52F+FJfsk9z5w9d2bvxwL8URIRFxoCFwVUGGmj5NVIB0g+QI6tYdQHqDfqyHdcYHdKpURebtwL4aQ9zBvmHNPGagkeMCdclswpUHMuIZqBar123WjX3fUdDFNc4LIYhHvsOQB5kCPMJXMbIOwfAio08EIWmS3q+GgQ47eYG7MeXAfjmH+YQ1uYtOuqkQZxX6M15vvIR9NOLGKWSMKdXZvkoJDPRBpkGMjznrqsX2G+Jufqq0J6y4U0yASQn2e+IyK/HZeDQFLTfgtmNJGIrX1G3EUKpEEGgDz/E+okH63H5T5JFe2YKWXM7013e+RBzNXGrzLfY/1M/Hwj7v3yk+ga56QH8ecYL/1rJZ4lRpgfvLv2OFYrkMCEXqUH8bxizphbhsB+I/rt6+d4oULMzTN9tPIC0COCN23Wm8zVn5JPmKaaCdy8knjEXAM9uS8wV5hbzGx8E/hPYBfzgtlJlnNT3YQVkRzo5433BR3X3lLzvpo9/0VpB6vJ6CCj/M0poPvAEQH1u3kHbkNgYQs3rdIAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABNklEQVR4XrWUO04DMRCGx8oNUsNhkjJKwznoqDkBCJKSKg0noQsFEhwDEYqQAinKg3927NieOLaXJJ/0a3fn8Y/X+yBqgdGBg4SV9V01FNwK6YaDNWda9QT6gbZO8J5jwGNc9j+s6emWy05s+qYTIVXjgqJrYlNDAx8SskbZJNEnyUqzFDz2cA+pmmZAakoQY8NpsqiCVJvsJ+3vpy3vq+AQuvOXzjK2/qL8rc/tsQvdQK8UmaZR+2nCmbdQz182vFDOFM0dEsMPnQOX5IbFd5Y3BSOSxisVf5K4eVdxHgBTc2/PI56hJbSGNhB/724bNjhf4fgLXfiWnQOv9MHHFalXQZOoYdPgZxNVJMoToRCbZtNxlDgS/kV+w36GAQsJFVbSmpJfky8VBbStF45qyDZnkxap+QOWeDgOAwVmhwAAAABJRU5ErkJggg==>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAYCAYAAAAVibZIAAABS0lEQVR4Xq2UvUpEMRCF56q1FrZa2/gMgpZi4xssWPoK2lspWFkJIvsiVjaKFttuv4iFNoL4d+YmuZlMJtks+MFhJ2d+ktx7WaIWukL8H9jzbLdK1pIZKXPSNYzW3up8Js1fQ+/Qr9AbdC6LNMYWJn5gqdz7RjqxxIJDHvoQrWDHnywuWz3H5Ibu86JUtCgzckNt5pxUkGTDC6rSPtvBA++1OdAyQRGfp/FewJ6Iz8jVvkKrws94ofrV+ZtlTqEVH28R9+Q3GJza8zyBdn08hb5EjnsOxHpgmVzyWSfAJoXN+v2zY3Fu3fDpglzyUPlX3n9SfmAMPWrzFvqEvqEfio8A6njN1/yANoaOyDZ0J438rD0FOxDTa9BNTNCOiGsUN+DEBBpBR9AltCQLFMVBEv33WPpiFqFpY09LbUuNo73SkdY3dBsN0mqY8AdAQzyaNo37KgAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIYAAAAYCAYAAAA/FYWiAAAD80lEQVR4Xu2ZW8gNURTH16GI3KLkkhLlQYoiUV7Ii+uLB0pJQiivXnikJAp5IfLhwYMohIQHiuQSyrWQB8n9kvvd+p8185111tkz3z4z850zTvOrf2dm7T17r71n7TV75hAVNJWSNSQkq3YKClqYYpkUFDSXzawPrL+BvrLesH4q2/CwsvD/LNsEno4hGb+MvVT+/cZ6XlXLQYK+suI+6xNV7hf0jjVPV0pK2KDlLIl9pC1occKJ9qKRQRHTF/z9Y41pQaMXrZGZRlJ2xxbEEuN9HnG4G7VQOoPP1hCLw1lmLIm/W2yBF+42aQFJo9NtAbOLpKzN2DMgwpt8gDFfscb68RqjCgyv+kJ11UMkPvepsqbkLkWvjkaunLywimTMM2xBmTrunSf1ZQw3EfcpnbOuRsexfrGeGHv9pPMtNQm6f0G189F5lOICw9t7+IsXhiwpoVHsxJE6b7K+k3TUXdfKEfNZByK0n+Sxt5e1h7Wbta18lT81C8X79iQjJjC8GE3y9rTRFqQh3F9gk6m5F9jdZDVTQTtZNZcBcAXjjtpfDDXnQ1i/jS0KZOEJDuETgbVBfeWyDufH7C9qas9Wx4dJ6j5kdVX2Gh6QOwAQfbAPtAUtzmqScevJ1Oh0vYm1jNzz52Ima65D+E5ibRCCzgfJcDXx0M7p4Pecsi2hDvyuSZsB4Xt8dHfNA29PuCl+KtH64Dofwo9bLrCCzxvbVIqu70vaRwn6j8pa+A7VKzhGvcuqDOe91XkVKLxkjRQdMDdY71mjSCYJg+rBOsjax3pUqVpmFusq6ylru7J3Yd0m2egNYx0jSW/NJmrcAPZ+xtaQwIhZnXjkoH/XPir8BuUC8x9VRmtJCufYAoJdNjSVc0mb4fGU4HhRcB6ijycSAqIyKl32KvhFHWSn8RTjaIMYROLDLXMnlgd2l38NCYwYkAHQ/wBlw97haGDfquyax6yd1riD9ZHkezpSJzKATUX4zwANPyPZHOmUoyfiAmuxOrdBgmwARrC+qLIQZJo11tjZmBWIXT2e83g9xyflMAhCwY43NdckNyswnrB+kNw36y/GgL1Q9XxXBo3F7BpLKrB68NwK0ZOCzIPNbIgua2OtU+chqBO7O+48YhK0E2f9ZgVGUvDpfEVw3I2y+iRRkr3CZGXSk/KSNYkqu2CbPXpyA6ijy3SdDeo4n9TGRhaB4b0waruvi/6sIyQZfinrZHtJyoaBngQ8Hk6o85Wsa6zBwTlSFjLIGZIovU6Vb/n4G/sU+7OQZHN6vGx1OOgwZU+yTvCIfct6TfI4dv3XlCfsIydtQCedt7zTmqMqaCnqD9L6r8g5rTMgv5H41SooyCn/AL1/BsA0S2aeAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAI4AAAAYCAYAAAAswsVWAAAELUlEQVR4Xu2ZW4hNURjHvzO555IXpTyIUiIpHsit8ODB5YVSykwayhMeXEoZPCFCKSV3SZEX5YE8GEVIeHF7IArlfr8b4/uftdc5a39nrX05s86cPWfOr/4za33f2nuv9a1v77X2PkQeyUlDnRrG12z7Ok+XolsOugPUdrzGSINfunTwekhD7ZJ+ntrLOag6hPvZCb3eKg2anaxPlA9eXj9Y71h/DNtw3ThLeAwaxujiNauNirFo4+u+CTfJFM0cmA9U7C/0lXU91Co5zsTR6ItILpGyj5SOGsI2bpMNpNosko4M45rPtCRJnNxVaWRmkurAPemoIeICjCdwXJv0eHxkWsg/HT1cRCZO6ISLSV1otmkMOEDKd1TYLXS4k9UiLilS372RkYh0egGbffR3h3SUgUycEPfJHZjUQfNDTHQDd0yrpITGZzkn/DekMcOcJtXnAdJRBpGJY0uO8ay/rKfC7hfLLFUBOXaTlaT8c6Qjw9jms1xiEwfr+E3WXdavwNbbbJQBNrNOOHSc1HJ6hHWIdZC1BgclICrIryjan0XQX7wV+8CZOHp/g02wyYPA7gO8HmaZqHHG3b1DjXIDqbglZWKkcqF6UuL2N+OMciOptt/J/dbsTJxHZA/MNlL2IdJhknClWSUNGUOMvzAqFOC7VfSF2M/qE5QPs2ZRybkimZ9CSTlLqg+DpCNA9286a1hQxsoCe8+gbuJMHNcdhY9GsCfMjU5hBak7KalWq8NisY0f4Hj4FkhHgO04m60zcc0nmMraki/l8olutkMZH4MlInGK6YADrhUdBVwduMP6yBrFamV9Y/VlnWIdYz0uNqUWUt9/RqPClxzI/86wTrLWk7pLPxdaVw/bOAHG6fLhSb1dGsndvoKE7m1c/59pCOhF0X2Db640Uj5xSp8dG0kdME86qDRxUF5ulJG9YGlQ15jlRr7oLv6/O6g/DP6jTUO+Ozl6wn8nlHZNEt+iA7gCKmMAsN/QP9HYcNk7AzwZcf29wt4S2F0bZswrbhIboSfOPtYXUptWvE3hIPweYzKW1MVe8pzh9yvzm4AZnCusJqMuAyfrzayLRl36q4HsAzaLCDLuXJ08WojTb9b7Qusw7RVOchtYwvEmjM8nss+ow/6TtVAfYNCf9UIaDZx7nLSgk/j9SmMGHU8uPMI1g3OlCYlO6qcVNmNy0ixUfCIS9CExPs+VjvLCdNsorzPKGm+J85w1WVdy4UDhl+RJrAtB/TJrCWuTbkDh9ntILWNNhq0aRE52yvmIPFe5pOxDUrDkNrGWsdaypoS8Cm+JYwZmBOu8UcdXVry66m8b00htjmcUWqjk0mCD/YxiXjeLQatQ+PxMNpZzLP1vSS1jrWF35jhH4SXNFQNviVOLuIKWgIolc1ZIkTg1H4sS9J6rmxI54f2koU6dOnUqz38hTRBBABdtqAAAAABJRU5ErkJggg==>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEEAAAAYCAYAAACldpB6AAACrUlEQVR4Xu2XuYsUQRTGX3uxKIgYiILJgnhEBgaGJiL+DxooBgYbCi6CmiiGBgYGJhqYqKigsqYGJqL4ByiIBh6LNx54rMf75lV1V72pV9090wMzsD94Q/X3Vb06urq6hyhHUf4sMjwTsJATMMSGjNtMxvRRyo7Imfs4fnL8C+JdUOeX8p56rwGvKW77h2N7VIPovPN83C6d7Oj72Epxnu8cHzjecvx12j1f2WIPScWXSl9FkmSl0tvgB2YBb4cWW1HQff5d4HWbUou3iST/fKT2SK9yarD6OiadR/OIJM+MNpjnHNu0aGN2mBonbiD039qwKegKSaNTTkF5aVWhHcFwN5Dkwo4KucpxSGmDsJzjjhYpfVNrwbh9QzxTayo5haUn0QM6wHE9uLZJdJOQlqhr398ypTcCWweNd2mjlsTIAm6Q5D1Dcoi9iO2W5Pv6StLXOm005QFJgmfasMiPp2SK3N3h+gva7BC8vdDPTm1kiKZwgWOW+rduV4wqrwevV+Q/rPRz6toEJ/dlV/YHJBakS5DzkxazNNxmzAmS/JdKpWr7pSxl2M3xMLgOD8gaGo8Sr0HkO6KNDthLkvuxNpjTHPu1qNnC8UaLVH0pri+V9HxP+kLaLrlGkk+f4jmQ8nh4kWCaJO97bVB1Dpms4LhIUglloeoJdwzeq1Lp5ybXR505bfRTNNxZEZgY2hzVhsNPUn9/rOY46zx8qid5QvJsopPPHN9iu/fNDR0+ynimjoUV3FqtJfk2z00OuX2ujyS5bkU1bPh/RoF21usUOxivdEzUL7IPvIF+kHyP9DB20mAkkmGSDUi0bMZdLQzEwN1ncDk3k/wTHRUHOTZqMWIUk2uJfh67JnVojwnV6sf3oYO7YqWw9MmjZiaWbemL1DLM0g3T1qLTnMMn+w/WH6DCKt5W6gAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEEAAAAYCAYAAACldpB6AAADJklEQVR4Xu2Xy6tPURTH17noGjC55BXJq9yJAaE8RyiXRMnQo8hQQklKScr1HJBS/gBDSTK6ykTKkEwYMfHIK3mzvnvvc+/a3/P6/X7nuN0rn1q3s79r77X2Xvvsfc9PZDhIWGgfF6LDOB0OS6k5fHTyby265dUUdNyndiBtFPSpy2a1kyyOBMar/VabqrZK7Wvs7oD8w/xLbanaFPH5GiVk2y8+dmqf1N6ovTLaCd81Bo4V1O7OWUQdUNijpo0ci027nPyi5vFF7S2LyjbxOe/Hso95S+177HCd15FWh0OS3Xm0T/nHlhbXKpwHLBSvv2QHmCRwJrKVdAw4SFodEO9SjnaTtLosE19wy0Txub6hkfdC3ZZs5eYHbQMaDezREcnmANBOs1gT3G0WTB958vIPAudPta7QxqArQW8KxEe8NAfYEbTeJqpcQlqAMexIGSu+wzO1AWOVlYuoXgRi4XYeMIY7qPUcLUJT+Sw+B458IXvEd5pNOrQnpG1SO0NaoKgKTp8rPt7O2Oe0H6YNPzRMfJ7RiaJcGZ6Lj7eE9AvUlsuS3Q1ckNBmhHaPuAsyeSCFRUjJneB28fGsc3LQcCTAGrWZ4bk7+MaFdiF5F1zgjvgY2GRLl/a/S5r0axQuwnvJ+R+rue5JZRHySPoSU+gwZ8Syea9TG89nTbsUqgO+RDH+Wiw78H0wi7SkT+LkPRqRi5LiipBfeFkkxd8UEyT7tqFddk7hx/GzTJPskWIwRscmD9kh7ljaDY9XwjuwxbQtKEI/iwGM44Va4Etfb7xpZW/UXrV3LErIkRTf8rhH0Oc16TjWN4Jv8J7jzcSi0QHf9AvIZ0ERzrEYgl0Vn2CO9Rl6ZahQ6yNPPBu8NS8iZYhjao/VdrMjgN8H+I+DdaS5UsMFjE9pWh+XohoU4TyLBuxu5WVWwSP3188NH1jMRrXlLHraX1AnoAgXWTS4T1KHm0/bk8Ix2SX+Rj+stjLyep6yMJx8EP+xg/P2kXwAr+pa99T22h34/cCvMLNa7TiLf5WW1+J3Hb81YqlDSsZOZ2EEUTLt/9Rk9NW2gRkXhSjSG+IPjBixpM29ascAAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,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>