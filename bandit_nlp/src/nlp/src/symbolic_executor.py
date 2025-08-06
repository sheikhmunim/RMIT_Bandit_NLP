#!/usr/bin/env python3

import rospy
from geometry_msgs.msg import Twist

# Initialize global publisher once
cmd_pub = None

def init_executor():
    global cmd_pub
    cmd_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)

def execute_symbolic(labels):
    global cmd_pub
    twist = Twist()

    if 'STOP' in labels:
        rospy.loginfo("→ Executing STOP")
        twist.linear.x = 0.0
        cmd_pub.publish(twist)

    if 'GO_SLOW' in labels:
        rospy.loginfo("→ Moving slow")
        twist.linear.x = 0.1
        cmd_pub.publish(twist)

    if 'GO_FAST' in labels:
        rospy.loginfo("→ Moving fast")
        twist.linear.x = 0.5
        cmd_pub.publish(twist)

    if 'WAVE_RIGHT' in labels:
        rospy.loginfo("→ Waving right arm (stub)")
        # Add your right arm wave command here

    if 'WAVE_LEFT' in labels:
        rospy.loginfo("→ Waving left arm (stub)")
        # Add your left arm wave command here
