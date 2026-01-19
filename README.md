![Bandit the Gamer](./bandit.jpeg)  

# Bridging Natural Language Understanding and Symbolic Planning for Adaptive Robot Control

This repository contains the full implementation of my minor thesis project for the Master of Artificial Intelligence, RMIT University.  
The project presents a complete Neural–Symbolic robot control pipeline that converts free-form natural language commands into safe, deterministic, and explainable robot actions using:

- BERT-based multi-head NLU  
- Dynamic PDDL problem generation  
- Fast Downward symbolic planning  
- ROS execution layer with online replanning  

The system is evaluated on the TIAGo service robot (simulation + hardware) across eight scenarios, demonstrating dynamic correction, safety guarantees, and deterministic plan generation.

---

## Repository Structure

    bandit_nlp/
    │
    ├── build/                      
    ├── devel/                      
    ├── downward/                   
    │
    ├── src/
    │   ├── nlp/
    │   │   └── bert_grounded_model/    
    │   │
    │   └── src/
    │       ├── pddl/
    │       │   ├── domain_base.pddl           
    │       │   ├── domain_base_old*.pddl      
    │       │
    │       ├── bert_grounding_node.py         
    │       ├── grounding_planner.py           
    │       ├── multi_head_model.py            
    │       ├── pddl_integration.py            
    │       ├── symbolic_executor.py           
    │       ├── cmd_vel_publish.py             
    │       ├── trial_logger.py                
    │       │
    │       ├── CMakeLists.txt
    │       └── package.xml
    │
    ├── .catkin_workspace
    └── sas_plan                       

---

## System Overview

1. Natural Language Input  
   User provides any free-form instruction:  
   “move forward fast”, “wave left hand”, “go backward then stop”.

2. NLU Grounding (BERT)  
   - Command chunking  
   - Slot prediction: intent, speed, region, hand, direction, ordering  
   - Correction detection (“actually”, “instead”)  

3. Symbolic Planning (PDDL + Fast Downward)  
   - Dynamic problem file  
   - Safety rules (STOP insertion)  
   - Deterministic planning (A* + LM-Cut)  

4. ROS Execution  
   - Publishes to /cmd_vel  
   - Executes wave gestures  
   - Automatic braking  

5. Online Replanning  
   - New commands interrupt  
   - System re-grounds → replans → continues safely  

---

## Key Features

- Free-form natural language support  
- Safety-aware symbolic reasoning  
- Online replanning  
- Deterministic robot behavior  
- Works in Gazebo + real TIAGo robot  
- Fully interpretable pipeline  

---

## Connecting to TIAGo / Bandit Robot

This project supports both simulation and real robot execution on PAL Robotics TIAGo (Bandit).

---

### 1. SSH Into the Robot

    ssh pal@bandit

On your laptop:

    export ROS_MASTER_URI=http://bandit:11311
    export ROS_IP=<your_laptop_ip>

---

### 2. Sync Your Code to TIAGo/Bandit

Run from your local machine:

    ./sync.sh

---

### 3. Navigate on the Robot

    ssh pal@bandit
    cd ~/catkin_ws/src/bandit_nlp/

or for tutorial workspace:

    cd ~/tutorial/

---

### 4. Build on the Robot

    catkin_make
    source ./devel/setup.bash

---

### 5. Verify Motion Controller Exists

    rostopic list

Look for:

    /mobile_base_controller/cmd_vel

---

### 6. Run a Motion Test

    rosrun nlp cmd_vel_publish.py

If TIAGo moves → connection successful.

---

### 7. Run the Full NL→PDDL→Execution Pipeline

Start the hybrid controller:

    rosrun nlp bert_grounding_node.py

Now speak or type commands:

    move forward slow
    turn right then stop
    wave your right hand
    actually go backward instead

The robot will:
- Ground the language  
- Build a symbolic plan  
- Execute via /cmd_vel  
- Replan if interrupted  

---

### 8. Additional Documentation

PAL Robotics SDK:  
https://docs.pal-robotics.com/sdk/23.12/

Bandit In-Person Tutorial Repo:  
https://github.com/JimmieMitty/Bandit_in_person_tutorial

---

## Evaluation Summary

The system was evaluated across 8 scenarios × 10 trials:

| Scenario                  | TSR |
|--------------------------|-----|
| Direction Control        | 100% |
| Nominal Navigation      | 90%  |
| Noise-Robust Commands   | 90%  |
| Correction/Replanning   | 90%  |
| Ambiguity Handling      | 80%  |
| Speed Compliance        | 80%  |
| Long-Horizon Planning   | 70%  |
| Concurrent Tasks        | 40% (limitation) |

Safety remained 100%.

---

## Thesis Reference

Bridging Natural Language Understanding and Symbolic Planning for Adaptive Robot Control  
s4076159_sheikh_abdul_munim.pdf

---

## Contact

Sheikh Abdul Munim  
Master of Artificial Intelligence — RMIT University  
GitHub: https://github.com/sheikhmunim  
Email: s4076159@student.rmit.edu.au

---

## License

This project is intended for academic and research use.  
Please cite the thesis when referencing the system.



If you wish to see the documentation provided by Pal Robotics, please follow this link:  
[Pal Robotics SDK Documentation](https://docs.pal-robotics.com/sdk/23.12/)
