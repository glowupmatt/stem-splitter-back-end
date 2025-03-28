import os
from typing import Any
from sagemaker.pytorch import PyTorchModel
from sagemaker.serializers import JSONSerializer
from sagemaker.deserializers import JSONDeserializer
from sagemaker.predictor import Predictor

def create_sagemaker_model() -> Predictor:
    """
    Create and deploy a PyTorch model on SageMaker.
    
    Args:
        bucket: S3 bucket name
        model_path: Path to model artifacts in S3
        role_arn: AWS IAM role ARN with SageMaker permissions
        model_name: Name of the model to use
    
    Returns:
        SageMaker Predictor instance
    """
    try:
        model = PyTorchModel(
            model_data=f's3://{bucket}/{model_path}',
            role=role_arn,
            framework_version='1.12',
            py_version='py39',
            entry_point='inference.py',
            source_dir='source_dir',
            env={
                'MODEL_NAME': model_name,
                'NUM_WORKERS': '2',
            }
        )
        
        return model.deploy(
            initial_instance_count=1,
            instance_type='ml.m5.large',
            serializer=JSONSerializer(),
            deserializer=JSONDeserializer()
        )
    except Exception as e:
        print(f"Error deploying model: {str(e)}")
        raise