import pandas as pd
import torch
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import train_test_split
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
from transformers import DataCollatorWithPadding
from datasets import Dataset

# Load your dataset
df = pd.read_csv("commands.csv")
# Drop rows where labels are missing
df = df.dropna(subset=['labels'])

# Convert label string to list
df['labels'] = df['labels'].apply(lambda x: str(x).split(','))

# Define your label set
LABELS = ["GO_KITCHEN", "GO_LIVING_ROOM", "GO_TABLE", "GO_SLOW", "GO_FAST", "STOP",
          "WAVE_LEFT", "WAVE_RIGHT", "CORRECTION", "SEQUENCE", "CONCURRENT"]

# Convert labels to multi-hot vectors
mlb = MultiLabelBinarizer(classes=LABELS)
label_matrix = mlb.fit_transform(df['labels'])
df['label_vector'] = label_matrix.tolist()

# Split into train and validation sets
train_df, eval_df = train_test_split(df, test_size=0.2, random_state=42)
train_ds = Dataset.from_pandas(train_df[['text', 'label_vector']])
eval_ds = Dataset.from_pandas(eval_df[['text', 'label_vector']])

# Load tokenizer
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

# Tokenize function
def tokenize(example):
    return tokenizer(example["text"], truncation=True)

train_ds = train_ds.map(tokenize)
eval_ds = eval_ds.map(tokenize)

# Format labels for model
def format_labels(example):
    example["labels"] = torch.tensor(example["label_vector"], dtype=torch.float)
    return example

train_ds = train_ds.map(format_labels)
eval_ds = eval_ds.map(format_labels)

# Load model
model = BertForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=len(LABELS),
    problem_type="multi_label_classification"
)

# Training configuration
training_args = TrainingArguments(
    output_dir="./bert_output",
    evaluation_strategy="epoch",
    save_strategy="epoch",
    logging_strategy="epoch",
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    num_train_epochs=10,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss"
)

# Setup trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=eval_ds,
    tokenizer=tokenizer,
    data_collator=DataCollatorWithPadding(tokenizer=tokenizer, return_tensors="pt")
)

# Train
trainer.train()

# Save the model and tokenizer
model.save_pretrained("bert_grounded_model")
tokenizer.save_pretrained("bert_grounded_model")

print("Training complete. Model saved to 'bert_grounded_model/'")
