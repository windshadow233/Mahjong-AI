import argparse
import torch
from torch.nn import MSELoss
from torch.optim import Adam
import wandb
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from dataset.data import process_reward_data, TenhouDataset
from model.models import RewardPredictor


@torch.no_grad()
def model_test(model, dataset: TenhouDataset):
    total_error = 0
    total = 0
    length = len(dataset)
    while len(dataset) > 0:
        data = dataset()
        if len(data) == 0:
            break
        features, labels = process_reward_data(data)
        features, labels = features.to(device), labels.to(device)
        output = model(features)
        error = (output - labels).pow(2).sum()
        total_error += error
        total += len(labels)
        print(f"Testing {length - len(dataset)} / {length} Error: {error:.3f}".center(50, '-'), end='\r')
    dataset.reset()
    return total_error / total

mode = 'reward'
experiment = wandb.init(project='Mahjong', resume='allow', anonymous='must', name=f'train-{mode}')


train_set = TenhouDataset(data_dir='data', batch_size=128, mode=mode, target_length=4)
test_set = TenhouDataset(data_dir='data', batch_size=128, mode=mode, target_length=4)
length = len(train_set)
len_train = int(0.8 * length)
train_set.data_files, test_set.data_files = train_set.data_files[:len_train], train_set.data_files[len_train:]

parser = argparse.ArgumentParser()
parser.add_argument('--hidden_dims', '-hd', default=50, type=int)
parser.add_argument('--num_layers', '-n', default=2, type=int)
parser.add_argument('--epochs', '-e', default=10, type=int)
args = parser.parse_args()

hidden_dims = args.hidden_dims
epochs = args.epochs
num_layers = args.num_layers
model = RewardPredictor(74, hidden_dims, num_layers)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
optim = Adam(model.parameters())
loss_fcn = MSELoss()
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optim, mode='min', patience=1)

os.makedirs(f'output/{mode}-model/checkpoints', exist_ok=True)
min_mse = torch.inf
global_step = 0
for epoch in range(epochs):
    while len(train_set) > 0:
        data = train_set()
        if len(data) == 0:
            break
        features, labels = process_reward_data(data)
        features, labels = features.to(device), labels.to(device)
        output = model(features)
        loss = loss_fcn(output, labels)
        optim.zero_grad()
        loss.backward()
        optim.step()
        global_step += 1
        print(f"Epoch-{epoch + 1}: {len_train - len(train_set)} / {len_train} loss={loss.item():.3f}".center(50, '-'), end='\r')
        experiment.log({
            'train loss': loss.item(),
            'epoch': epoch + 1
        })

    train_set.reset()

    torch.save({"state_dict": model.state_dict(), "num_layers": num_layers, "hidden_dims": hidden_dims}, f'output/{mode}-model/checkpoints/epoch_{epoch + 1}.pt')
    model.eval()
    mse = model_test(model, test_set)
    if mse < min_mse:
        min_mse = mse
        torch.save({"state_dict": model.state_dict(), "num_layers": num_layers, "hidden_dims": hidden_dims}, f'output/{mode}-model/checkpoints/best.pt')
    model.train()

    experiment.log({
        'epoch': epoch + 1,
        'test_mse': mse,
        'lr': optim.param_groups[0]['lr']
    })
    scheduler.step(mse)




