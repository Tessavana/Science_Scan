import torch
from transformers.file_utils import is_tf_available, is_torch_available, is_torch_tpu_available
from transformers import BertTokenizerFast, BertForSequenceClassification
from transformers import Trainer, TrainingArguments
import numpy as np
import random
from sklearn.datasets import fetch_20newsgroups
from sklearn.model_selection import train_test_split
import pandas as pd

x = torch.cuda.is_available() # this has to return true, nvidia cuda cores must be installed, ms visual studio C++ has to be installed

# Define the path to your Excel file within the "Data" folder
file_path_final = "15-12 final training.xlsx"


# Read the Excel file into a DataFrame
finaldataset = pd.read_excel(file_path_final)
finaldataset

label_mapping = {'Incorrect': 0, 'Correct': 1}

# Replace values in the 'Label' column
finaldataset['Label'] = finaldataset['Label'].replace(label_mapping)
finaldataset


# Get the lists of sentences and their labels.
documents = finaldataset.Sentences.values
labels = finaldataset.Label.values

# train_texts = [str(i) for i in df[‘documents’].values]


def set_seed(seed: int):
    """
    Helper function for reproducible behavior to set the seed in ``random``, ``numpy``, ``torch`` and/or ``tf`` (if
    installed).

    Args:
        seed (:obj:`int`): The seed to set.
    """
    random.seed(seed)
    np.random.seed(seed)
    if is_torch_available():
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        # ^^ safe to call this function even if cuda is not available
    if is_tf_available():
        import tensorflow as tf

        tf.random.set_seed(seed)

set_seed(1)

# the model we gonna train, base uncased BERT
# check text classification models here: https://huggingface.co/models?filter=text-classification
model_name = 'bert-base-uncased'
# max sequence length for each document/sentence sample
max_length = 512

print("till here")
# load the tokenizer
tokenizer = BertTokenizerFast.from_pretrained(model_name, do_lower_case=True)


# def read_20newsgroups(test_size=0.2):
#     # download & load 20newsgroups dataset from sklearn's repos
#     dataset = fetch_20newsgroups(subset="all", shuffle=True, remove=("headers", "footers", "quotes"))
#     documents = dataset.data[:7000]
#     labels = dataset.target[:7000]
#     # split into training & testing a return data as well as label names
#     return train_test_split(documents, labels, test_size=test_size), dataset.target_names

train_texts, valid_texts, train_labels, valid_labels = train_test_split(documents,labels, test_size=0.2)



# call the function
# save the training and validation texts and labels
# (train_texts, valid_texts, train_labels, valid_labels), target_names = read_20newsgroups()

train_labels = torch.tensor(train_labels).long()
valid_labels = torch.tensor(valid_labels).long()




# tokenize the dataset, truncate when passed `max_length`,
# and pad with 0's when less than `max_length`
train_texts = [x for x in train_texts]
valid_texts = [x for x in valid_texts]
train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=max_length)
valid_encodings = tokenizer(valid_texts, truncation=True, padding=True, max_length=max_length)

print(train_texts)


class StatMistakesDataSet(torch.utils.data.Dataset):
    def __init__(self, encodings, labels):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {k: torch.tensor(v[idx]) for k, v in self.encodings.items()}
        item["labels"] = torch.tensor([self.labels[idx]])
        return item

    def __len__(self):
        return len(self.labels)

# for all in train_labels:
#     train_labels[all] = train_labels.dtype(torch.LongTensor)
# # train_labels = train_labels.type(torch.LongTensor)
# # valid_labels = valid_labels.type(torch.LongTensor)
# train_labels = train_labels.long
# valid_labels = valid_labels.long


# convert our tokenized data into a torch Dataset
train_dataset = StatMistakesDataSet(train_encodings, train_labels)
valid_dataset = StatMistakesDataSet(valid_encodings, valid_labels)

y=1

# load the model and pass to CUDA
model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2).to("cuda")

from sklearn.metrics import accuracy_score

def compute_metrics(pred):
  labels = pred.label_ids
  preds = pred.predictions.argmax(-1)
  # calculate accuracy using sklearn's function
  acc = accuracy_score(labels, preds)
  return {
      'accuracy': acc,
  }

training_args = TrainingArguments(
    output_dir='./results',          # output directory
    num_train_epochs=3,              # total number of training epochs
    per_device_train_batch_size=8,  # batch size per device during training
    per_device_eval_batch_size=20,   # batch size for evaluation
    warmup_steps=500,                # number of warmup steps for learning rate scheduler
    weight_decay=0.01,               # strength of weight decay
    logging_dir='./logs',            # directory for storing logs
    load_best_model_at_end=True,     # load the best model when finished training (default metric is loss)
    # but you can specify `metric_for_best_model` argument to change to accuracy or other metric
    logging_steps=400,               # log & save weights each logging_steps
    save_steps=400,
    evaluation_strategy="steps",     # evaluate each `logging_steps`
)

trainer = Trainer(
    model=model,                         # the instantiated Transformers model to be trained
    args=training_args,                  # training arguments, defined above
    train_dataset=train_dataset,         # training dataset
    eval_dataset=valid_dataset,          # evaluation dataset
    compute_metrics=compute_metrics,     # the callback that computes metrics of interest
)

# train the model
# trainer.train()
# print("done")
# trainer.train("results/checkpoint-2000")
#
# # evaluate the current model after training
# trainer.evaluate()
#
# # saving the fine tuned model & tokenizer
# model_path = "20newsgroups-bert-base-uncased"
# model.save_pretrained(model_path)
# tokenizer.save_pretrained(model_path)

#Performing inference
#This thing does not work right now, because target_names is not defined
# def get_prediction(text):
#     # prepare our text into tokenized sequence
#     inputs = tokenizer(text, padding=True, truncation=True, max_length=max_length, return_tensors="pt").to("cuda")
#     # perform inference to our model
#     outputs = model(**inputs)
#     # get output probabilities by doing softmax
#     probs = outputs[0].softmax(1)
#     # executing argmax function to get the candidate label
#     return target_names[probs.argmax()]
#
# print(get_prediction("This is a spaceship"))
