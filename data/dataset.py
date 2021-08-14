import torch
from datasets import load_dataset, list_datasets # huggingface library
from data.tokenizer import Tokenizer
import random
from torch.utils.data import Dataset

class PretrainDataset(Dataset):
    def __init__(self, language, max_len, 
                dataset_name, dataset_type, split_type, category_type, next_sent_prob, masking_prob,
                percentage=None):
        
        if dataset_name not in list_datasets():
            assert('Not available in HuggingFace datasets')
        
        if dataset_type is None:
            if percentage is None:
                data = load_dataset(dataset_name, split=split_type)
            else:
                data = load_dataset(dataset_name, split=f'{split_type}[:{percentage}%]')
        else:
            if percentage is None:
                data = load_dataset(dataset_name, dataset_type, split=split_type)
            else:
                data = load_dataset(dataset_name, dataset_type, split=f'{split_type}[:{percentage}%]')
        
        self.data_len = len(data)
        self.next_sent_prob = next_sent_prob
        self.data = data[category_type]
        self.tokenizer = Tokenizer(language, max_len)
        self.mask_token = self.tokenizer.mask_token
        self.max_len = max_len
        if self.max_len != self.tokenizer.max_len:
            assert "The max len you gave to Dataset does not match with tokenizer's max len!"
        
    def __len__(self):
        return self.data_len
    
    def __getitem__(self, index):
        # sampling first sentence
        data1 = self.data[index].strip()

        # choosing idx of second sentence
        data2_idx = index+1
        is_next = True

        # rechoosing idx of second sentence if it shouldn't be consecutive or is same with the first sentence
        if random.random() > self.next_sent_prob:
            is_next=False
            while (data2_idx==index+1) or (data2_idx==index):
                data2_idx = random.randint(0,self.data_len)
        
        # sampling second sentence
        data2 = self.data[data2_idx].strip()

        # masking function : original sentence -> masked sentence
        def masking(data):
            # "ENCODE" = "tokenize" + "convert token to id" + "truncation & padding" + "Transform to Tensor"
            # tokenize sentence 
            tokenized_data = self.tokenizer.tokenize(data)
            tokenized_data_len = len(tokenized_data)
            
            input_ids = []          # masked data
            label_ids = []          # original data => IMPORTANT : should set UNMASKED token to 0(to support MLM Loss function ignore_index)

            # convert tokenized sentence into id & corrupt for MLM
            for idx, token in enumerate(tokenized_data):
                prob = random.random()
                tmp_token_idx = self.tokenizer.convert_tokens_to_ids(token)
                
                # corrupt the original sentence for the Language Model to reconstruct throughout Pretraining phase
                # With 15% probability, we corrupt the current token
                if prob < 0.15:
                    prob /= 0.15
                    # With 80% probability, convert the token into [MASK]
                    if prob < 0.8:
                        input_ids.append(self.tokenizer.get_mask_token_idx())
                    # with 10% probability, convert into a random token
                    elif prob < 0.9:
                        tmp_rand_idx = random.randrange(self.tokenizer.get_vocab_size())
                        input_ids.append(tmp_rand_idx)
                    # With 10% probability, we do not change the token at all
                    else:
                        input_ids.append(tmp_token_idx)
                    
                    # Case of masked token, we put the original token to label_ids
                    # In other words, Save the original uncorrupted data into label_ids
                    label_ids.append(tmp_token_idx)
                    
                # With 85% probability, we do not corrupt the current token
                else:
                    input_ids.append(tmp_token_idx)
                    # Case of UNMASKED token, we put the pad token to label_ids
                    # THIS IS TO SUPPORT THE MLM LOSS FUNCTION'S ignore_index!!!!!!!!
                    label_ids.append(self.tokenizer.get_pad_token_idx())

            return input_ids, label_ids
        
        # transformation function : masked sentence 1 & 2 -> torch Tensor
        def Transformation_into_Tensor(input_ids1, input_ids2, label_ids1, label_ids2):
            
            input_ids1_length = len(input_ids1)
            input_ids2_length = len(input_ids2)
            label_ids1_length = len(label_ids1)
            label_ids2_length = len(label_ids2)

            if input_ids1_length != label_ids1_length:
                assert "Something wrong with input_ids1"
            if input_ids2_length != label_ids2_length:
                assert "Something wrong with input_ids2"

            # truncation
            total_length = input_ids1_length + input_ids2_length + 3
            if total_length > self.max_len:
                max_len_per_input_ids = int((self.max_len-3) / 2)
                if input_ids1_length > max_len_per_input_ids:
                    input_ids1 = input_ids1[:max_len_per_input_ids]
                    label_ids1 = label_ids1[:max_len_per_input_ids]
                if input_ids2_length > max_len_per_input_ids:
                    input_ids2 = input_ids2[:max_len_per_input_ids]
                    label_ids2 = label_ids2[:max_len_per_input_ids]
                # update input_ids1_length and input_ids2_length
                input_ids1_length = len(input_ids1)
                input_ids2_length = len(input_ids2)
                label_ids1_length = len(label_ids1)
                label_ids2_length = len(label_ids2)
                if input_ids1_length != label_ids1_length:
                    assert "Something wrong with input_ids1"
                if input_ids2_length != label_ids2_length:
                    assert "Something wrong with input_ids2"
            
            # padding
            # should perform padding even after truncation because 1 or 2 spaces might be shorter than max length
            input_ids = [self.tokenizer.convert_tokens_to_ids(self.tokenizer.cls_token)] + input_ids1 + \
                        [self.tokenizer.convert_tokens_to_ids(self.tokenizer.sep_token)] + input_ids2 + \
                        [self.tokenizer.convert_tokens_to_ids(self.tokenizer.sep_token)]
            
            label_ids = [self.tokenizer.convert_tokens_to_ids(self.tokenizer.cls_token)] + label_ids1 + \
                        [self.tokenizer.convert_tokens_to_ids(self.tokenizer.sep_token)] + label_ids2 + \
                        [self.tokenizer.convert_tokens_to_ids(self.tokenizer.sep_token)]

            total_length = len(input_ids)
            pad_length = self.max_len - total_length
            input_ids = input_ids + [self.tokenizer.convert_tokens_to_ids(self.tokenizer.pad_token)] * pad_length
            label_ids = label_ids + [self.tokenizer.convert_tokens_to_ids(self.tokenizer.pad_token)] * pad_length
            
            # transform to tensor
            input_ids = torch.Tensor(input_ids)
            label_ids = torch.Tensor(label_ids)

            return input_ids, label_ids

        # "ENCODE" = "tokenize" + "convert token to id" + "truncation & padding" + "Transform to Tensor"
        masked_data1, data1= masking(data1)
        masked_data2, data2= masking(data2)
        encoded_input_ids, encoded_label_ids= Transformation_into_Tensor(
            masked_data1, masked_data2, data1, data2
        )

        # build batch
        batch = {}
        batch['input_ids'] = encoded_input_ids.to(torch.long)
        batch['label_ids'] = encoded_label_ids.to(torch.long)

        return batch

class PretrainDataset_total():
    def __init__(self, language, max_len, 
                dataset_name, dataset_type, category_type, next_sent_prob, masking_prob,
                training_ratio, validation_ratio, test_ratio, percentage=None):
        self.data = PretrainDataset( language, max_len, 
                dataset_name, dataset_type, 'train', category_type, next_sent_prob, masking_prob,
                percentage)
        self.total_length = len(self.data)
        if training_ratio+validation_ratio+test_ratio>1.0:
            assert "Unproper split of training, validation, test ratio!"
        
        train_len = int(self.total_length*training_ratio)
        val_len = int(self.total_length*validation_ratio)
        test_len = self.total_length - train_len - val_len
        self.traindata, self.valdata, self.testdata = torch.utils.data.random_split(self.data, 
            [train_len, val_len, test_len]
        )
    def getTrainData(self):
        return self.traindata
    
    def getValData(self):
        return self.valdata
    
    def getTestData(self):
        return self.testdata

class FineTuneDataset(Dataset):
    def __init__(self, language, max_len, 
                dataset_name, dataset_type, split_type, category_type, 
                x_name, y_name, percentage=None):
        
        if dataset_name not in list_datasets():
            assert('Not available in HuggingFace datasets')
        
        if percentage is None:
            data = load_dataset(dataset_name, dataset_type, split=split_type)
        else:
            data = load_dataset(dataset_name, dataset_type, split=f'{split_type}[:{percentage}%]')

        self.x_name = x_name
        self.y_name = y_name
        self.data_len = len(data) # number of data

        self.data = data[category_type]
        self.dataX = self.data[x_name]
        self.dataY = self.data[y_name]
        
        self.tokenizer = Tokenizer(language, max_len)
        
    def __len__(self):
        return self.data_len
    
    def __getitem__(self, index):
        encoded_datax = self.tokenizer.encode(self.dataX[index])
        encoded_datay = self.tokneizer.encode(self.dataY[index])

        batch ={}
        batch['encoder_input_ids'] = encoded_datax.input_ids
        batch['encoder_attention_mask'] = encoded_datax.attention_mask # will be generated in model as well
        batch['decoder_input_ids'] = encoded_datay.input_ids
        batch['labels'] = encoded_datay.input_ids.clone()
        batch['decoder_attention_mask'] = encoded_datay.attention_mask # will be generated in model as well
        
        return batch


class FineTuneDataset_total():
    def __init__(self, language, max_len, 
                dataset_name, dataset_type, category_type, 
                x_name, y_name, percentage=None):
        self.traindata = FineTuneDataset(language, max_len, 
                        dataset_name, dataset_type, 'train', category_type, 
                        x_name, y_name, percentage)
        self.valdata = FineTuneDataset(language, max_len, 
                        dataset_name, dataset_type, 'validation', category_type, 
                        x_name, y_name, percentage)
        self.testdata = FineTuneDataset(language, max_len, 
                        dataset_name, dataset_type, 'test', category_type, 
                        x_name, y_name, percentage)
    
    def getTrainData(self):
        return self.traindata
    
    def getValData(self):
        return self.valdata
    
    def getTestData(self):
        return self.testdata