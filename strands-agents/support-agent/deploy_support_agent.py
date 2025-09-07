"""
Deploy Bedrock AgentCore agent
"""
import os
import boto3
from bedrock_agentcore_starter_toolkit import Runtime

# Force UTF-8 encoding to prevent charmap errors
os.environ['PYTHONIOENCODING'] = 'utf-8'

def deploy_agent():
    """Deploy the agent to AWS Bedrock AgentCore"""
    try:
        # Get AWS region from environment or use default
        # boto3 will automatically handle credential discovery
        region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        
        # Verify AWS credentials are available
        try:
            sts = boto3.client('sts', region_name=region)
            identity = sts.get_caller_identity()
            print(f"AWS credentials verified for account: {identity['Account']}")
        except Exception as e:
            print(f"Error: Unable to verify AWS credentials: {e}")
            print("   Please ensure AWS credentials are configured via:")
            print("   - AWS CLI: aws configure")
            print("   - IAM role (if running on EC2)")
            print("   - Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY")
            return False
        
        # Read the IAM role ARN
        iam_role_file = "iam_role_arn.txt"
        if os.path.exists(iam_role_file):
            with open(iam_role_file, 'r') as f:
                role_arn = f.read().strip()
        else:
            print(f" Error: {iam_role_file} not found.")
            print(f"   Please run 'python create_iam_role.py' first.")
            return False
        
        # Create AgentCore runtime instance
        runtime = Runtime()
        
        # Configure the runtime
        agent_name = "support_agent"
        
        print(f"Deploying agent '{agent_name}' in {region}...")
        print(f"Using IAM Role: {role_arn}")
        print(f"AWS Region: {region}")
        print(f"Configuring runtime...")
        
        runtime.configure(
            entrypoint="agentcore_strands.py",
            execution_role=role_arn,
            auto_create_ecr=True,
            requirements_file="requirements.txt",
            region=region,
            agent_name=agent_name
        )
        
        print(f"Runtime configured successfully")
        
        print("Building and launching agent...")
        launch_response = runtime.launch()
        
        # Save agent ARN for later use
        agent_arn = launch_response.agent_arn
        with open('agent_arn.txt', 'w') as f:
            f.write(agent_arn)
        
        print("Agent deployed successfully!")
        print(f"   Agent ARN: {agent_arn}")
        print(f"   Saved to: agent_arn.txt")
        
        return True
        
    except Exception as e:
        print(f" Error deploying agent: {e}")
        return False

if __name__ == "__main__":
    success = deploy_agent()
    if success:
        print(f"\n Next step: Test your agent with:")
        print(f"   python invoke_support_agent.py --prompt 'Hello, world!'")
    else:
        print(f"\n Deployment failed - check the error above")

