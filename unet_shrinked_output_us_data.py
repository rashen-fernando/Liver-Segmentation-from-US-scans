# -*- coding: utf-8 -*-
"""Unet_shrinked_output_US_Data.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1vbkjK4nkxteCcZP01LWezZU2FhTaExWU
"""

#! pip install neptune-client

#@title Import data
import numpy as np
import os
from matplotlib import pylab as plt

from skimage.transform import resize
from skimage import color

from tqdm import tqdm
import pickle
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import torchvision.transforms.functional as fn
import math
import joblib
import neptune.new as neptune
from neptune.new.types import File
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

#@title Load data
# train_dir = './Train_1.pt'
# Ground_truth_dir = './Truth_1.pt'
train_dir = '/content/drive/MyDrive/Trained models/Dataset/Train/Train1.pt'
Ground_truth_dir = '/content/drive/MyDrive/Trained models/Dataset/Label/Truth1.pt'

X = torch.load(train_dir)#, map_location=torch.device(device))
Y = torch.load(Ground_truth_dir)#, map_location=torch.device(device))
Y = torch.Tensor(np.where(Y.cpu().detach().numpy()>0, 1, 0))#.to(device)

#@title Run neptune ai 
torch.cuda.empty_cache()


run = neptune.init(
    project="rashenf/Unet-US-data",
    api_token="eyJhcGlfYWRkcmVzcyI6Imh0dHBzOi8vYXBwLm5lcHR1bmUuYWkiLCJhcGlfdXJsIjoiaHR0cHM6Ly9hcHAubmVwdHVuZS5haSIsImFwaV9rZXkiOiIwZWM3ZTRiNi0zYWU3LTRkZTgtOTJlYy1lYTE1MjkyYjcyYjMifQ==",
)  # your credentials


run["config/dataset/training_path"] = train_dir
run["config/dataset/training_data_shape"] = X.shape

run["config/dataset/ground_truth_path"] = Ground_truth_dir
run["config/dataset/ground_truth_data_shape"] = Y.shape

#@title Rearranging data
batch_size = int(input('Batch size - '))
number_of_channels = 1
IMG_Height = X.size(dim=2)
IMG_Width = X.size(dim=1)
Data_Junks = int(len(X)/batch_size)
number_of_patients = int(len(X)/130)
print('Number_of_batches = 0 -',Data_Junks)
Number_of_batches = int( input( ' Data_Junks - ') )

X_test = X[batch_size*Number_of_batches:batch_size*Data_Junks].view(-1,batch_size,number_of_channels,IMG_Height,IMG_Width)
Y_test = Y[batch_size*Number_of_batches:batch_size*Data_Junks].view(-1,batch_size,number_of_channels,IMG_Height,IMG_Width)

X = X[0*batch_size:batch_size*Number_of_batches].view(-1,batch_size,number_of_channels,IMG_Height,IMG_Width)
Y = Y[0*batch_size:batch_size*Number_of_batches].view(-1,batch_size,number_of_channels,IMG_Height,IMG_Width)

 

#@title Unet
#creating neural network

#@title Unet
#creating neural network

class Unet(nn.Module):
    def __init__(self,Input_size, batch_size,channels):
      super().__init__()
      
      self.c1 = nn.Conv2d(channels,64,3,stride = 1, padding= 0)
      self.c2 = nn.Conv2d(64,64,3,stride = 1, padding= 0)
      self.p1 = nn.MaxPool2d(2)
      self.c3 = nn.Conv2d(64,128,3,stride = 1, padding = 0)
      self.c4 = nn.Conv2d(128,128,3,stride = 1, padding = 0)
      self.p2 = nn.MaxPool2d(2)
      self.c5 = nn.Conv2d(128,256,3,stride = 1, padding = 0)
      self.c6 = nn.Conv2d(256,256,3,stride = 1, padding = 0)
      self.p3 = nn.MaxPool2d(2)
      self.c7 = nn.Conv2d(256,512,3,stride = 1, padding = 0)
      self.c8 = nn.Conv2d(512,512,3,stride = 1, padding = 0)
      self.p4 = nn.MaxPool2d(2)
      self.c9 = nn.Conv2d(512,1024,3,stride = 1, padding = 0)
      self.c10 = nn.Conv2d(1024,1024,3,stride = 1, padding = 0)

      self.u1 = nn.ConvTranspose2d(1024,512,2, stride = 2)
      self.c11 = nn.Conv2d(1024,512,3,stride = 1, padding = 0)
      self.c12 = nn.Conv2d(512,512,3,stride = 1, padding = 0)

      self.u2 = nn.ConvTranspose2d(512,256,2, stride = 2)
      self.c13 = nn.Conv2d(512,256,3,stride = 1, padding = 0)
      self.c14 = nn.Conv2d(256,256,3,stride = 1, padding = 0)

      self.u3 = nn.ConvTranspose2d(256,128,2, stride = 2)
      self.c15 = nn.Conv2d(256,128,3,stride = 1, padding = 0)
      self.c16 = nn.Conv2d(128,128,3,stride = 1, padding = 0)

      self.u4 = nn.ConvTranspose2d(128,64,2, stride = 2)
      self.c17 = nn.Conv2d(128,64,3,stride = 1, padding = 0)
      self.c18 = nn.Conv2d(64,64,3,stride = 1, padding = 0)
      self.c19 = nn.Conv2d(64,1,3,stride =1, padding =0)
      
      self.u5 = nn.ConvTranspose2d(1,1,2, stride = 3)
      self.normalize = nn.LayerNorm([1, 546, 962])
      #self.normalize = nn.LayerNorm([1, 322,322])
      #self.normalize = nn.LayerNorm([1, 512, 512])
      # self.c20 = nn.Conv2d(1,1,3,stride = 1, padding = 0)
      # self.c21 = nn.Conv2d(1,1,3,stride = 1, padding = 0)
      # self.c22 = nn.Conv2d(1,1,3,stride =1, padding =0)
      
      


    def forward(self,x):
      #Shrink
      Inp = x.size(dim=2)
      x = F.rrelu(self.c1(x))
      x = F.rrelu(self.c2(x))
      layer_1_copy = x
      x = self.p1(x)
      x = F.rrelu(self.c3(x))
      x = F.rrelu(self.c4(x))
      layer_2_copy = x
      x = self.p2(x)
      x = F.rrelu(self.c5(x))
      x = F.rrelu(self.c6(x))
      layer_3_copy = x
      x = self.p3(x)
      x = F.rrelu(self.c7(x))
      x = F.rrelu(self.c8(x))
      layer_4_copy = x
      x = self.p4(x)
      x = F.rrelu(self.c9(x))
      x = F.rrelu(self.c10(x))
      
      

      # #Expand
      x = self.u1(x)
      a1 = math.ceil((layer_4_copy.size(dim=2)-x.size(dim=2))/2)
      b1 = x.size(dim=2)
      a2 = math.ceil((layer_4_copy.size(dim=3)-x.size(dim=3))/2)
      b2 = x.size(dim=3)
      layer_4_copy = layer_4_copy[:,:,a1:a1+b1,a2:a2+b2]
      x = torch.cat((layer_4_copy,x),1)
      x = F.rrelu(self.c11(x))
      x = F.rrelu(self.c12(x))

      x = self.u2(x)
      a1 = math.ceil((layer_3_copy.size(dim=2)-x.size(dim=2))/2)
      b1 = x.size(dim=2)
      a2 = math.ceil((layer_3_copy.size(dim=3)-x.size(dim=3))/2)
      b2 = x.size(dim=3)
      layer_3_copy = layer_3_copy[:,:,a1:a1+b1,a2:a2+b2]
      x = torch.cat((layer_3_copy,x),1)
      x = F.rrelu(self.c13(x))
      x = F.rrelu(self.c14(x))

      x = self.u3(x)
      a1 = math.ceil((layer_2_copy.size(dim=2)-x.size(dim=2))/2)
      b1 = x.size(dim=2)
      a2 = math.ceil((layer_2_copy.size(dim=3)-x.size(dim=3))/2)
      b2 = x.size(dim=3)
      layer_2_copy = layer_2_copy[:,:,a1:a1+b1,a2:a2+b2]
      x = torch.cat((layer_2_copy,x),1)
      x = F.rrelu(self.c15(x))
      x = F.rrelu(self.c16(x))

      x = self.u4(x)
      a1 = math.ceil((layer_1_copy.size(dim=2)-x.size(dim=2))/2)
      b1 = x.size(dim=2)
      a2 = math.ceil((layer_1_copy.size(dim=3)-x.size(dim=3))/2)
      b2 = x.size(dim=3)
      layer_1_copy = layer_1_copy[:,:,a1:a1+b1,a2:a2+b2]
      x = torch.cat((layer_1_copy,x),1)
      x = F.rrelu(self.c17(x))
      x = F.rrelu(self.c18(x))
      #x = F.rrelu(self.c19(x))
      x = F.log_softmax(self.c19(x),dim = 3)
      x = self.normalize(x)
      # x = self.u5(x)
      # a = math.ceil((x.size(dim=1)- Inp )/2)
      # x = x[:,a:a+Inp,a:a+ Inp ]
      # x = F.log_softmax(x,dim = 2)
      # x = self.normalize(x)
      return x


#@title Define model
model = Unet(IMG_Height,batch_size,number_of_channels).to(device)
loss_vector = []

import torch.optim as optim
learning_rate = float(input('Learning Rate - '))
loss_function = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=learning_rate)
eps = int(input('Epochs - '))

def intersection_accuracy(predicted,ground_truth):
     predicted = torch.round(predicted).cpu().detach().numpy()
     ground_truth = torch.round(ground_truth).cpu().detach().numpy()
     acc_metric = np.where(predicted==ground_truth,1,-1)
     accuracy = np.sum(acc_metric)/np.prod(ground_truth.shape)
     return accuracy
#@title Training

for epoch in range(eps): # 3 full passes over the data
  #  model.train()
    for data in range(Number_of_batches):  # `data` is a batch of data
        
        model.zero_grad()  # sets gradients to 0 before loss calc. You will do this likely every step.
        output = model.forward(X[data].to(device).float())  # pass in the reshaped batch (recall they are 28x28 atm)

        a1 = math.ceil( (IMG_Height-output.size(dim=2) )/2 )
        b1 = output.size(dim=2)
        a2 = math.ceil( (IMG_Width-output.size(dim=3) )/2 )
        b2 = output.size(dim=3)

        loss =  F.mse_loss(output,Y[data].to(device)[:,:,a1:a1+b1,a2:a2+b2].float())
        run["training/batch/loss"].log(loss)
        acc = intersection_accuracy(Y[data].to(device)[:,:,a1:a1+b1,a2:a2+b2],output)
        run["training/batch/acc"].log(acc)

        loss.backward()  # apply this loss backwards thru the network's parameters
        optimizer.step()  # attempt to optimize weights to account for loss/gradients
    print(epoch,loss)
    loss_vector.append(loss) 


#@title Logging data to neptune ai
parameters = {
    "lr": learning_rate,
    "bs": batch_size,
    "input_sz": X[0][0].shape,
    "output_sz" : output.shape,
    "n_classes": 1,
    "Patient": number_of_patients,
    "Number of batches":Number_of_batches,
    "model_filename":model, "basemodel":Unet,
    "device":device,
}
run["config/hyperparameters"] = parameters

run["config/model"] = type(model).__name__
run["config/loss_function"] = type(loss_function).__name__
run["config/optimizer"] = type(optimizer).__name__

fname = 'unet'#parameters["model_filename"]

# Saving model architecture to .txt
with open(f"./{fname}_arch.txt", "w") as f:
    f.write(str(model))

# Saving model weights .pth
torch.save(model.state_dict(), f"./{fname}.pth")

run[f"io_files/artifacts/{fname}_arch"].upload(
    f"./{fname}_arch.txt"
)
run[f"io_files/artifacts/{fname}"].upload(
    f"./{fname}.pth"
)

torch.cuda.empty_cache()

#@title Plot results
import matplotlib.pyplot as plt
import matplotlib as mpl

rnd = np.random.randint(Data_Junks, size=50)
X = X_test
Y = Y_test
for ix in rnd:
  print(X[ix][1].shape)
  model.eval()
  out = model(X[ix].to(device))
  out = out*255#torch.unsqueeze(X[ix],0).to('cuda:0')[:,a:a+b,a:a+b]
  #print(torch.unsqueeze(X[ix],0).to('cuda:0')[:,a:a+b,a:a+b].shape)
  out = out[1][0].cpu().detach().numpy()

  fig = plt.figure()

  ax1 = fig.add_subplot(1,3,1)
  plt.title("Test data")
  ax1.imshow(X[ix][1][0].cpu().detach().numpy())
  #plt.show()
  ax2 = fig.add_subplot(1,3,2)
  plt.title("Ground Truth")
  ax2.imshow((Y[ix][1][0].cpu().detach().numpy()))
  #plt.show()
  ax3 = fig.add_subplot(1,3,3)
  plt.title("Predicted")
  ax3.imshow(out)
  plot = plt.show()

  run["images/predictions"].log(
        File.as_image(fig)
      )

run.stop()