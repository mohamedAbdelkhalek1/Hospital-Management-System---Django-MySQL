import numpy as np
import matplotlib.pyplot as plt
import cv2
import tensorflow as tf
from sklearn.model_selection import train_test_split
# import pickle 


def load_trained_model(model_dir):
  model = tf.keras.models.load_model(model_dir)
  input_shape = list(model.layers[0].input_shape)
  print('input_shape',input_shape)
  return model,input_shape[1:-1]#, output_len[1:-1]

def classifier(path,model,shape)-> int:
    img=cv2.imread(path)
    img=cv2.resize(img,dsize=shape)
    img_rgb=cv2.cvtColor(img,cv2.COLOR_BGR2RGB)
    img=np.expand_dims(img,axis=0)
    pred=model.predict(img,verbose=0)
    idx=np.argmax(pred)
    print('model output: ',pred)
    plt.imshow(img_rgb)
    
    return idx,pred

model,input_layer=load_trained_model('/../../brain.h5')

classifier('/../../brain1.jpeg',model,input_layer)
idx,pred=classifier("/../../bon1.jpg",model,input_layer) 
classes=['No tumor', 'Stable tumor', 'Unstable tumor']

print('\n\n')
index = int(pred*10/3.34) # to get from 0 to 2 to choose a suitable choise
print('prediected class: ',classes[index])
print('\n\n')
print(idx,pred)
