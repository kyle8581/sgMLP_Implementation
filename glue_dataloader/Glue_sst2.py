from datasets import load_dataset, list_datasets
from torch.utils.data import Dataset

class Train_sst2(Dataset):
    def __init__(self, dataset_name, x_name, y_name, percentage=None):
        if dataset_name not in list_datasets():
            assert('Not available in Huggingface dataset')

        if percentage is None:
            train_data = load_dataset('glue', 'sst2', split='train')

        else:
            train_data = load_dataset('glue', 'sst2', split=f'train[:{percentage}%]')

        self.data_len = len(train_data)
        self.train_X = train_data[x_name]
        self.train_Y = train_data[y_name]

    def __len__(self):
        return self.data_len

    def __getitem__(self, index):
        return self.train_X[index], self.train_Y[index]


class Val_sst2(Dataset):
    def __init__(self, dataset_name, x_name, y_name, percentage=None):
        if dataset_name not in list_datasets():
            assert('Not available in Huggingface dataset')

        if percentage is None:
            val_data = load_dataset('glue', 'sst2', split='validation')

        else:
            val_data = load_dataset('glue', 'sst2', split=f'validation[:{percentage}%]')

        self.data_len = len(val_data)
        self.val_X = val_data[x_name]
        self.val_Y = val_data[y_name]

    def __len__(self):
        return self.data_len

    def __getitem__(self, index):
        return self.val_X[index], self.val_Y[index]


class Test_sst2(Dataset):
    def __init__(self, dataset_name, x_name, y_name, percentage=None):
        if dataset_name not in list_datasets():
            assert('Not available in Huggingface dataset')

        if percentage is None:
            test_data = load_dataset('glue', 'sst2', split='test')

        else:
            test_data = load_dataset('glue', 'sst2', split=f'test[:{percentage}%]')

        self.data_len = len(test_data)
        self.test_X = test_data[x_name]
        self.test_Y = test_data[y_name]

    def __len__(self):
        return self.data_len

    def __getitem__(self, index):
        return self.test_X[index], self.test_Y[index]


class Total_sst2(Dataset):
    def __init__(self, dataset_name, x_name, y_name, percentage=None):
        self.train_data = Train_sst2(dataset_name, x_name, y_name, percentage)
        self.val_data = Val_sst2(dataset_name, x_name, y_name, percentage)
        self.test_data = Test_sst2(dataset_name, x_name, y_name, percentage)

    def getTrainData(self):
        return self.train_data

    def getValData(self):
        return self.val_data

    def getTestData(self):
        return self.test_data