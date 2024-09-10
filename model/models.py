import torch
from torch import nn


class ResBlock(nn.Module):
    def __init__(self):
        super(ResBlock, self).__init__()
        self.layers = nn.Sequential(
            nn.Conv1d(256, 256, kernel_size=3, padding='same'),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2),
            nn.Conv1d(256, 256, kernel_size=3, padding='same'),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2)
        )

    def forward(self, x):
        return x + self.layers(x)


class DiscardModel(nn.Module):
    def __init__(self, in_channels, num_layers=20):
        super(DiscardModel, self).__init__()
        self.in_conv = nn.Sequential(
            nn.Conv1d(in_channels, 256, kernel_size=3, padding='same'),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2)
        )
        self.res_blocks = nn.Sequential(
            *(ResBlock() for _ in range(num_layers))
        )
        self.out_conv = nn.Sequential(
            nn.Conv1d(256, 1, kernel_size=1),
            nn.BatchNorm1d(1)
        )

    def forward(self, x):
        x = self.in_conv(x)
        x = self.res_blocks(x)
        x = self.out_conv(x)
        return x.squeeze(1)


class RiichiModel(nn.Module):
    def __init__(self, in_channels, num_layers=20):
        super(RiichiModel, self).__init__()
        self.in_conv = nn.Sequential(
            nn.Conv1d(in_channels, 256, kernel_size=3, padding='same'),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2)
        )
        self.res_blocks = nn.Sequential(
            *(ResBlock() for _ in range(num_layers))
        )
        self.out_conv = nn.Sequential(
            nn.Conv1d(256, 3, kernel_size=1),
            nn.BatchNorm1d(3),
            nn.LeakyReLU(0.2)
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(3 * 34, 1024),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 1)
        )

    def forward(self, x):
        x = self.in_conv(x)
        x = self.res_blocks(x)
        x = self.out_conv(x)
        x = self.fc(x)
        return x


class FuroModel(nn.Module):
    def __init__(self, in_channels, num_layers=20):
        super(FuroModel, self).__init__()
        self.in_conv = nn.Sequential(
            nn.Conv1d(in_channels, 256, kernel_size=3, padding='same'),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2)
        )
        self.res_blocks = nn.Sequential(
            *(ResBlock() for _ in range(num_layers))
        )
        self.out_conv = nn.Sequential(
            nn.Conv1d(256, 3, kernel_size=1),
            nn.BatchNorm1d(3),
            nn.LeakyReLU(0.2)
        )

        self.fc = nn.Sequential(
            nn.Flatten(),
            nn.Linear(3 * 34, 1024),
            nn.BatchNorm1d(1024),
            nn.LeakyReLU(0.2),
            nn.Linear(1024, 256),
            nn.BatchNorm1d(256),
            nn.LeakyReLU(0.2),
            nn.Linear(256, 1)
        )

    def forward(self, x):
        x = self.in_conv(x)
        x = self.res_blocks(x)
        x = self.out_conv(x)
        x = self.fc(x)
        return x


class RewardPredictor(nn.Module):
    def __init__(self, input_dims, hidden_dims, num_layers):
        super(RewardPredictor, self).__init__()
        self.gru = nn.GRU(input_dims, hidden_dims, num_layers, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dims, 10),
            nn.ReLU(inplace=True),
            nn.Linear(10, 1)
        )

    def forward(self, x):
        out, h_n = self.gru(x)
        return self.fc(out[:, -1, :])