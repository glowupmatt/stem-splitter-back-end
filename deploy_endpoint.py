import os
import sagemaker
from sagemaker.pytorch import PyTorchModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor import Predictor

def deploy_endpoint() -> Predictor:
    sagemaker.Session()
    role = ""
    
    
if __name__ == "__main__": 
    deploy_endpoint()
    