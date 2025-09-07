import boto3
import json
from botocore.exceptions import ClientError

def create_agentcore_role():
    """Create IAM role with comprehensive Bedrock permissions"""
    
    role_name = "bedrock_agentcore_role"
    
    try:
        iam = boto3.client('iam')
        
        # Trust policy for bedrock-agentcore service
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "bedrock-agentcore.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        print(f" Creating IAM role: {role_name}")
        
        try:
            # Create the role
            role_response = iam.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description="IAM role for Bedrock AgentCore with full Bedrock access"
            )
            print(f" Created IAM role: {role_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f" Role {role_name} already exists")
                role_response = iam.get_role(RoleName=role_name)
            else:
                raise e
        
        # Comprehensive Bedrock policy
        bedrock_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock:Converse",
                        "bedrock:ConverseStream",
                        "bedrock:GetFoundationModel",
                        "bedrock:ListFoundationModels"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer"
                    ],
                    "Resource": "*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogGroups",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }
        
        policy_name = "BedrockAgentCorePolicy"
        
        print(f" Creating policy: {policy_name}")
        
        try:
            # Create custom policy
            iam.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(bedrock_policy),
                Description="Comprehensive Bedrock access for AgentCore"
            )
            print(f" Created policy: {policy_name}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f" Policy {policy_name} already exists")
            else:
                raise e
        
        # Attach custom policy to role
        sts = boto3.client('sts')
        account_id = sts.get_caller_identity()['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            print(f" Attached custom policy to role")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f" Custom policy already attached")
        
        # Attach AWS managed Bedrock policy
        managed_policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
        try:
            iam.attach_role_policy(
                RoleName=role_name,
                PolicyArn=managed_policy_arn
            )
            print(f" Attached AWS managed Bedrock policy")
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f" AWS managed policy already attached")
        
        # Get role ARN
        role_arn = role_response['Role']['Arn']
        
        # Save role ARN to file
        with open('iam_role_arn.txt', 'w') as f:
            f.write(role_arn)
        
        print(f"\n IAM setup complete!")
        print(f"   Role: {role_name}")
        print(f"   ARN: {role_arn}")
        print(f"   Saved to: iam_role_arn.txt")
        
        return role_arn
        
    except Exception as e:
        print(f" Error creating IAM role: {e}")
        return None

if __name__ == "__main__":
    role_arn = create_agentcore_role()
    if role_arn:
        print(f"\n Next step: Run 'python deploy_agent.py' to deploy your agent")
    else:
        print(f"\n  IAM setup failed - check the error above")
