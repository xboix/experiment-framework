'''ResNet in PyTorch.

For Pre-activation ResNet, see 'preact_resnet.py'.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Deep Residual Learning for Image Recognition. arXiv:1512.03385
'''
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import OrderedDict


class BasicBlock(nn.Module):
    expansion = 1

    def __init__(self, in_planes, planes, stride=1):
        super(BasicBlock, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*planes)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class Bottleneck(nn.Module):
    expansion = 4

    def __init__(self, in_planes, planes, stride=1):
        super(Bottleneck, self).__init__()
        self.conv1 = nn.Conv2d(in_planes, planes, kernel_size=1, bias=False)
        self.bn1 = nn.BatchNorm2d(planes)
        self.conv2 = nn.Conv2d(planes, planes, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = nn.BatchNorm2d(planes)
        self.conv3 = nn.Conv2d(planes, self.expansion*planes, kernel_size=1, bias=False)
        self.bn3 = nn.BatchNorm2d(self.expansion*planes)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_planes != self.expansion*planes:
            self.shortcut = nn.Sequential(
                nn.Conv2d(in_planes, self.expansion*planes, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm2d(self.expansion*planes)
            )

    def forward(self, x):
        # x.requires_grad = True
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.conv2(out)))
        out = self.bn3(self.conv3(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out


class ResNet(nn.Module):
    def __init__(self, block, num_blocks, fine_tune=False, classes=(10, 10), pool=True, pretrained=False, in_planes=64, size_factor=1):
        print("In Planes", in_planes)
        # print("Fine tune? ", fine_tune)
        super(ResNet, self).__init__()
        self.in_planes = in_planes
        self.pool = pool
        self.classes = classes
        self.conv1 = nn.Conv2d(3, self.in_planes, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(self.in_planes)
        self.layer1 = self._make_layer(block, self.in_planes, num_blocks[0], stride=1)
        self.layer2 = self._make_layer(block, 128, num_blocks[1], stride=2)
        self.layer3 = self._make_layer(block, 256, num_blocks[2], stride=2)
        self.layer4 = self._make_layer(block, 512, num_blocks[3], stride=2)
        self.pool_fc = nn.Linear(8192, 512 * block.expansion)
        self.fc2_number = nn.Linear(512 * block.expansion, classes[0])
        self.fc2_color = nn.Linear(512 * block.expansion, classes[1])
        if len(classes) >= 3:
            self.fc2_loc = nn.Linear(512 * block.expansion, classes[2])
        if len(classes) == 4:
            self.fc2_scale = nn.Linear(512 * block.expansion, classes[3])

        if pool:
            if not pretrained:
                self.name = "resnet"
            else:
                if fine_tune:
                    self.name = "resnet_pretrained"
                else:
                    self.name = "resnet_pretrained_embeddings"
        else:
            self.name = "resnet_no_pool"

        if not fine_tune:
            for p in self.conv1.parameters():
                p.requires_grad = False
            for p in self.bn1.parameters():
                p.requires_grad = False
            for p in self.layer1.parameters():
                p.requires_grad = False
            for p in self.layer2.parameters():
                p.requires_grad = False
            for p in self.layer3.parameters():
                p.requires_grad = False
            for p in self.layer4.parameters():
                p.requires_grad = False

    def _make_layer(self, block, planes, num_blocks, stride):
        strides = [stride] + [1]*(num_blocks-1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_planes, planes, stride))
            self.in_planes = planes * block.expansion
        return nn.Sequential(*layers)

    def forward(self, x):
        # print("1", x.shape)
        out = F.relu(self.bn1(self.conv1(x)))
        # print("2", out.shape)
        out = self.layer1(out)
        # print("3", out.shape)
        out = self.layer2(out)
        # print("4", out.shape)
        out = self.layer3(out)
        # print("5", out.shape)
        out = self.layer4(out)
        # print("6", out.shape)
        if self.pool:
            if len(self.classes) == 4:
                out = F.avg_pool2d(out, 12)
            else:
                out = F.avg_pool2d(out, 4)
            out = F.relu(out)   # todo simplify code
        else:
            out = out.view(out.size(0), -1)
            out = self.pool_fc(out)
            out = F.relu(out)
        # print("7", out.shape)
        out = out.view(out.size(0), -1)
        # print("8", out.shape)
        # out = self.linear(out)

        num = self.fc2_number(out)
        col = self.fc2_color(out)
        if len(self.classes) == 4:
            loc = self.fc2_loc(out)
            scale = self.fc2_scale(out)
            return F.log_softmax(num, dim=1), F.log_softmax(col, dim=1), F.log_softmax(loc, dim=1), F.log_softmax(scale, dim=1)

        elif len(self.classes) == 3:
            loc = self.fc2_loc(out)
            return F.log_softmax(num, dim=1), F.log_softmax(col, dim=1), F.log_softmax(loc, dim=1)

        else:
            return F.log_softmax(num, dim=1), F.log_softmax(col, dim=1)


def ResNet18(pretrained=False, fine_tune=False, classes=(10, 10), in_planes=64, pool=True):
    # print("Pretrained? ", pretrained)
    model = ResNet(BasicBlock, [2, 2, 2, 2], fine_tune=fine_tune, classes=classes, in_planes=in_planes, pool=pool, pretrained=pretrained)

    if not pretrained:
        return model

    model_dict = model.state_dict()

    # original saved file with DataParallel
    state_dict = torch.load('models/st_dict_epoch71.pt', map_location="cpu")
    # create new OrderedDict that does not contain `module.`
    new_state_dict = OrderedDict()
    for k, v in state_dict.items():
        name = k[7:]  # remove `module.`
        # print(name, type(name))
        if name in model_dict:
            new_state_dict[name] = v

    # overwrite entries in the existing state dict
    model_dict.update(new_state_dict)
    # load the new state dict
    model.load_state_dict(model_dict)
    return model


def ResNet50(pretrained=False, fine_tune=False, classes=(10, 10), pool=True):
    if pretrained:
        raise Exception("Pretrained weights not yet available for ResNet-50")

    model = ResNet(Bottleneck, [3, 4, 6, 3], fine_tune=fine_tune, classes=classes, pool=pool, pretrained=pretrained)

    return model


def test():
    net = ResNet18()
    y = net(torch.randn(1, 3, 32, 32))
    print(y.size())
