import numpy

from lazyflow.graph import Operators, Operator, InputSlot, OutputSlot, MultiInputSlot, MultiOutputSlot
from lazyflow.roi import sliceToRoi, roiToSlice, block_view
from Queue import Empty
from collections import deque
import greenlet, threading
import vigra
import copy



class OpTrainRandomForest(Operator):
    name = "TrainRandomForest"
    description = "Train a random forest on multiple images"
    
    inputSlots = [MultiInputSlot("Images"),MultiInputSlot("Labels")]
    outputSlots = [OutputSlot("Classifier")]
    
    def notifyConnectAll(self):
        self.outputs["Classifier"]._dtype = object
        self.outputs["Classifier"]._shape = (1,)
        self.outputs["Classifier"]._axistags  = "classifier"
        
    def notifySubConnect(self, slots, indexes):
        print "OpClassifier notifySubConnect"
        self.notifyConnectAll()                 
    
        
    def getOutSlot(self, slot, key, result):
        
        featMatrix=[]
        labelsMatrix=[]
        
        for i,labels in enumerate(self.inputs["Labels"]):
            
            labels=labels[:].allocate().wait()
            print "hsahfjkhfjhfsaj", labels.max()
            
            
            print "ajhajkfhjkafhjfhaj",labels.min()
            indexes=numpy.nonzero(labels[...,0].view(numpy.ndarray))
            print "kjshajvjhvajhv", len(indexes[0])
            #Maybe later request only part of the region?
            image=self.inputs["Images"][i][:].allocate().wait()
            print image.shape, labels.shape
            
            features=image[indexes]
            labels=labels[indexes]
            
            print "GANG",features.shape, labels.shape
            featMatrix.append(features)
            labelsMatrix.append(labels)
        
        print features.shape
        featMatrix=numpy.concatenate(featMatrix,axis=0)
        labelsMatrix=numpy.concatenate(labelsMatrix,axis=0)
        
        RF=vigra.learning.RandomForest(100)        
        try:
            RF.learnRF(featMatrix.astype(numpy.float32),labelsMatrix.astype(numpy.uint32))
        except:
            print "ERROR: couldnt learn classifier"
            print featMatrix, labelsMatrix
            print featMatrix.shape, featMatrix.dtype
            print labelsMatrix.shape, labelsMatrix.dtype            
            
        result[0]=RF
        
        


class OpPredictRandomForest(Operator):
    name = "PredictRandomForest"
    description = "Predict on multiple images"
    
    inputSlots = [InputSlot("Image"),InputSlot("Classifier"),InputSlot("LabelsCount",stype='integer')]
    outputSlots = [OutputSlot("PMaps")]
    
    def notifyConnectAll(self):
        inputSlot = self.inputs["Image"]    
        nlabels=self.inputs["LabelsCount"].value        
        
        """
        self.outputs["PMaps"].resize(len(inputSlot)) #clearAllSlots()
        for i,islot in enumerate(self.inputs["Images"]):
            oslot = self.outputs["PMaps"][i]
            if islot.partner is not None:
                oslot._dtype = numpy.float32
                oslot._shape = islot.shape[:-1]+(nlabels,)
                oslot._axistags = islot.axistags
        
        """
        oslot = self.outputs["PMaps"]
        islot=self.inputs["Image"]
        oslot._dtype = numpy.float32
        oslot._shape = islot.shape[:-1]+(nlabels,)
        oslot._axistags = islot.axistags
    """    
    def notifySubConnect(self, slots, indexes):
        print "OpClassifier notifySubConnect"
        self.notifyConnectAll()                 
    """
        
        

    def getOutSlot(self,slot, key, result):
        nlabels=self.inputs["LabelsCount"].value

        RF=self.inputs["Classifier"].value
        assert RF.labelCount() == nlabels, "ERROR: OpPredictRandomForest, labelCount differs from true labelCount!"        
                
        newKey = key[:-1]
        newKey += (slice(0,self.inputs["Image"].shape[-1],None),)
        
        res = self.inputs["Image"][newKey].allocate().wait()
               
        shape=res.shape
        prod = 1
        for i,e in enumerate(shape):
            if i < len(shape) - 1:
                prod *= e            

        features=res.reshape(prod, shape[-1])
        

        prediction=RF.predictProbabilities(features.astype(numpy.float32))        
        
        prediction = prediction.reshape(*(shape[:-1] + (RF.labelCount(),)))
                
        result[:]=prediction[...,key[-1]]

            
            
            
            
            
            

        