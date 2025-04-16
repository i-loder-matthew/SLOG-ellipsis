from datasets import Dataset
from transformers import T5ForConditionalGeneration
from transformers import T5Tokenizer
from transformers import Seq2SeqTrainingArguments
from transformers import Seq2SeqTrainer
from transformers import DataCollatorForSeq2Seq
from datasets import load_dataset
from transformers import AutoTokenizer
import random
import numpy as np
np.random.seed(42)


# Define languages & load dataset (Example: French)
languages = ["fr", "vi", "tr", "en", "nl", "ro", "pl", "hu"]
dataset = load_dataset("allenai/c4", "pl", split="train", streaming=True)

subset = []
num_samples = 25000
for idx, example in enumerate(dataset):
    subset.append(example)
    if idx + 1 >= num_samples:
        break

dataset = Dataset.from_dict({
    "text": [item["text"] for item in subset],
    "timestamp": [item["timestamp"] for item in subset],
    "url": [item["url"] for item in subset]
})

tokenizer = T5Tokenizer.from_pretrained("t5-small")
model = T5ForConditionalGeneration.from_pretrained("t5-small")

# --------- Split dataset ---------
dataset = dataset.train_test_split(test_size=0.1)
train_dataset = dataset["train"]
eval_dataset = dataset["test"]

def t5_span_corruption(text, noise_density=0.15, mean_span_length=3):
    tokens = text.strip().split()
    num_to_mask = int(len(tokens) * noise_density)

    if num_to_mask == 0:
        return text, text  # skip short texts

    spans = []
    i = 0
    sentinel_counter = 0
    corrupted = []
    targets = []

    while i < len(tokens) and num_to_mask > 0:
        # Ensure there's enough room left in the tokens to create a span
        span_len = min(np.random.poisson(mean_span_length) + 1, num_to_mask)
        # Ensure the range is valid (start < end)
        start = random.randint(i, max(i, len(tokens) - span_len))

        corrupted.append(f"<extra_id_{sentinel_counter}>")
        targets.append(f"<extra_id_{sentinel_counter}> " + " ".join(tokens[start:start+span_len]))

        i = start + span_len
        num_to_mask -= span_len
        sentinel_counter += 1

    corrupted.append("<extra_id_{}>".format(sentinel_counter))  # end token
    targets.append("<extra_id_{}>".format(sentinel_counter))    # dummy end

    corrupted_text = " ".join(corrupted)
    target_text = " ".join(targets)

    return corrupted_text.strip(), target_text.strip()

# --------- Preprocessing ---------
def preprocess(batch):
    corrupted_texts = []
    target_texts = []

    for text in batch["text"]:
        corrupted, target = t5_span_corruption(text)
        corrupted_texts.append(corrupted)
        target_texts.append(target)

    model_inputs = tokenizer(corrupted_texts, max_length=512, truncation=True, padding="max_length")
    labels = tokenizer(target_texts, max_length=128, truncation=True, padding="max_length")

    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

# def preprocess_for_pretraining(batch):
#     inputs = [str(item) for item in batch["text"]]

#     model_inputs = tokenizer(
#         inputs,
#         padding="max_length",
#         truncation=True,
#         max_length=512,
#     )

#     model_inputs["labels"] = model_inputs["input_ids"].copy()

#     return model_inputs


# tokenized_dataset = dataset.map(preprocess, batched=True, remove_columns=["text", "timestamp", "url"])

train_dataset = train_dataset.map(preprocess, batched=True, remove_columns=["text", "timestamp", "url"])
eval_dataset = eval_dataset.map(preprocess, batched=True, remove_columns=["text", "timestamp", "url"])


data_collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)

training_args = Seq2SeqTrainingArguments(
    output_dir="./t5_pretrained",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=500,
    save_steps=1000,
    save_total_limit=2,
    predict_with_generate=True
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer,
    data_collator=data_collator
)


trainer.train()

results = trainer.evaluate()
print(results)