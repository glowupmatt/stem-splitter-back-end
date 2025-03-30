import os
import sagemaker
from sagemaker.pytorch import PyTorchModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor import Predictor

def deploy_endpoint() -> Predictor:
    sagemaker.Session()
    model = PyTorchModel(
        role = "arn:aws:iam::593793052722:role/splitter-saas-role",
        model_uri = "s3://splitter-saas/inference/model.tar.gz",
        framework_version="2.5.1",
        py_version="py311",
        entry_point="inference.py",
        source_dir=".",
        name="splitter-saas-endpoint"
    )
    
    predictor = model.deploy(
        initial_instance_count=1,
        instance_type="ml.g5.xlarge",
        endpoint_name="splitter-saas-endpoint",
    )
    
    
    
    
if __name__ == "__main__": 
    deploy_endpoint()
    