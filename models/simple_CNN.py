import torch.nn as nn
import torch.nn.functional as F


class SimpleCNN(nn.Module):
    def __init__(self, num_classes):
        super(SimpleCNN, self).__init__()
        self.conv1 = nn.Conv2d(3, 20, 5, 1)
        self.conv2 = nn.Conv2d(20, 50, 5, 1)
        self.fc1 = nn.Linear(5 * 5 * 50, 500)
        self.fc2_number = nn.Linear(500, num_classes[0])
        self.fc2_color = nn.Linear(500, num_classes[1])
        self.classes = num_classes
        if len(num_classes) == 3:
            self.fc2_loc = nn.Linear(500, num_classes[2])
        self.name = "simple_cnn"

    def forward(self, x):
        x = F.relu(self.conv1(x))
        x = F.max_pool2d(x, 2, 2)
        x = F.relu(self.conv2(x))
        x = F.max_pool2d(x, 2, 2)
        x = x.view(-1, 5 * 5 * 50)
        x = F.relu(self.fc1(x))
        num = self.fc2_number(x)
        col = self.fc2_color(x)
        if len(self.classes) == 3:
            loc = self.fc2_loc(x)
            return F.log_softmax(num, dim=1), F.log_softmax(col, dim=1), F.log_softmax(loc, dim=1)
        else:
            return F.log_softmax(num, dim=1), F.log_softmax(col, dim=1)
