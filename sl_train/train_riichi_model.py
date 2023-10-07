import os
import torch
from torch.optim import Adam
import wandb
import argparse
from torch.nn import CrossEntropyLoss, BCEWithLogitsLoss
from sklearn.metrics import roc_curve, auc, accuracy_score, precision_recall_fscore_support
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import sys
sys.path.append(os.path.dirname(os.path.abspath(os.path.dirname(__file__))))
from model.models import RiichiModel
from dataset.data import TenhouDataset, process_data


@torch.no_grad()
def model_test(model, dataset: TenhouDataset, epoch):
    length = len(dataset)
    y_true = []
    y_score = []
    while len(dataset) > 0:
        data = dataset()
        if len(data) == 0:
            break
        features, labels = process_data(data, label_trans=lambda x: x.float())
        features, labels = features.to(device), labels.to(device)
        output = model(features).sigmoid().flatten()
        y_true.extend(labels.tolist())
        y_score.extend(output.tolist())
        print(f"Testing {length - len(dataset)} / {length}".center(50, '-'), end='\r')
    dataset.reset()
    fpr, tpr, thresholds = roc_curve(y_true, y_score)
    roc_auc = auc(fpr, tpr)
    maxindex = (tpr - fpr).tolist().index(max(tpr - fpr))
    threshold = thresholds[maxindex]
    plt.figure()
    plt.plot(fpr, tpr, color='darkorange', lw=1, label='ROC curve (area = %0.2f)' % roc_auc)
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig(f'{mode}_model_roc_epoch{epoch}.png')
    plt.close()

    y_pred = list(map(lambda x: int(x > 0.6), y_score))
    acc = accuracy_score(y_true=y_true, y_pred=y_pred)
    precision, recall, f_score, _ = precision_recall_fscore_support(y_true=y_true, y_pred=y_pred, average='binary')
    return recall, precision, acc, f_score, threshold

parser = argparse.ArgumentParser()
parser.add_argument('--num_layers', '-n', default=20, type=int)
parser.add_argument('--epochs', '-e', default=10, type=int)
parser.add_argument('--pos_weight', '-w', default=None, type=int)
args = parser.parse_args()
mode = 'riichi'
experiment = wandb.init(project='Mahjong', resume='allow', anonymous='must', name=f'train-{mode}-sl')
train_set = TenhouDataset(data_dir='data', batch_size=128, mode=mode, target_length=2)
test_set = TenhouDataset(data_dir='data', batch_size=128, mode=mode, target_length=2)
length = len(train_set)
len_train = int(0.8 * length)
train_set.data_files, test_set.data_files = train_set.data_files[:len_train], train_set.data_files[len_train:]


num_layers = args.num_layers
in_channels = 291
model = RiichiModel(num_layers=num_layers, in_channels=in_channels)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)
optim = Adam(model.parameters())
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optim, mode='max', patience=1)
if args.pos_weight is not None:
    loss_fcn = BCEWithLogitsLoss(pos_weight=torch.tensor(args.pos_weight, device=device))
else:
    loss_fcn = BCEWithLogitsLoss()
epochs = args.epochs

os.makedirs(f'output/{mode}-model/checkpoints', exist_ok=True)
max_f1 = 0
global_step = 0
for epoch in range(epochs):
    while len(train_set) > 0:
        data = train_set()
        if len(data) == 0:
            break
        features, labels = process_data(data, label_trans=lambda x: x.float())
        features, labels = features.to(device), labels.to(device)
        output = model(features).flatten()
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

    model.eval()
    recall, precision, acc, f_score, threshold = model_test(model, test_set, epoch + 1)
    torch.save({
        "state_dict": model.state_dict(),
        "num_layers": num_layers,
        "in_channels": in_channels,
        "threshold": threshold
    }, f'output/{mode}-model/checkpoints/epoch_{epoch + 1}.pt')
    if f_score > max_f1:
        max_f1 = f_score
        torch.save({
            "state_dict": model.state_dict(),
            "num_layers": num_layers,
            "in_channels": in_channels,
            "threshold": threshold
        }, f'output/{mode}-model/checkpoints/best.pt')
    model.train()

    experiment.log({
        'epoch': epoch + 1,
        'test_f1': f_score,
        'test_recall': recall,
        'test_precision': precision,
        'test_acc': acc,
        'lr': optim.param_groups[0]['lr'],
        'threshold': threshold
    })
    scheduler.step(f_score)
