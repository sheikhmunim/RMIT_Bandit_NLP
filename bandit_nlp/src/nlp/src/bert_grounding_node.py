#!/usr/bin/env python3


import rospy
from std_msgs.msg import String
import torch
from transformers import BertTokenizer, BertForSequenceClassification
import os
import rospkg
from symbolic_executor import execute_symbolic, init_executor

LABELS = ["GO_KITCHEN", "GO_LIVING_ROOM", "GO_TABLE", "GO_SLOW", "GO_FAST", "STOP",
          "WAVE_LEFT", "WAVE_RIGHT", "CORRECTION", "SEQUENCE", "CONCURRENT"]

def load_model():
    rospack = rospkg.RosPack()
    model_dir = os.path.join(rospack.get_path('nlp'), 'bert_grounded_model')
    tokenizer = BertTokenizer.from_pretrained(model_dir)
    model = BertForSequenceClassification.from_pretrained(model_dir)
    model.eval()
    return tokenizer, model

def predict_command(tokenizer, model, text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.sigmoid(logits)[0]

    threshold = 0.3
    predicted = [LABELS[i] for i, p in enumerate(probs) if p > threshold]
    return predicted

def main():
    rospy.init_node('bert_grounding_node')
    tokenizer, model = load_model()
    init_executor()

    rospy.loginfo("BERT grounding node ready. Type natural language commands:")

    while not rospy.is_shutdown():
        try:
            text = input(">>> ")
            labels = predict_command(tokenizer, model, text)
            rospy.loginfo(f"Predicted Labels: {labels}")
            execute_symbolic(labels)
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
