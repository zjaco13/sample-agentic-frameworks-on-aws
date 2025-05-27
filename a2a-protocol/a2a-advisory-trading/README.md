# A2A Advisory Trading

A multi-agent serverless application built on Google's Agent2Agent Protocol for intelligent trading advisory services, powered by Amazon Bedrock.

This project serves as a reference implementation demonstrating how to design and deploy multi-agent systems using Google's Agent2Agent Protocol on AWS through a serverless architecture, powered by Amazon Bedrock. It showcases practical patterns for building agent networks while leveraging cloud-native services.

### Table of Content 
- [Architecture Design](#architecture-design)
- [Technical Stack](#technical-stack)
  - [Agent2Agent Protocol Implementation](#agent2agent-protocol-implementation)
  - [Serverless Infrastructure](#serverless-infrastructure)
- [Solution Deployment](#solutions-deployment)
  - [Deployment Pre-requisite](#deployment-pre-requisite)
  - [Deployment Steps](#deployment-steps)
  - [Demo](#demo)
  - [Test Individual Sub-Agents](#test-individual-sub-agents)
- [Use Cases](#use-cases)
- [Common Pattern Across Industries](#common-patterns-across-industries)


### Architecture Design

![A2A Advisory Trading Architecture](docs/images/adt-architecture.png)

The A2A Advisory Trading platform represents the approach to automated trading advisory through a distributed agent-based architecture. At its core, the system orchestrates multiple specialized AI agents that work in concert to analyze market conditions, assess risk on an investment decision, and execute trade.

The architecture centers around four primary agents, each with distinct responsibilities. The Portfolio Manager Agent serves as the central orchestrator of the system, responsible for discovering user intent from their inputs, identifying relevant agents based on their stated capabilities in agent cards, and delegating tasks accordingly. It also plays a crucial role in presenting analysis findings to users and confirming their trading decisions based on reports from other agents. The Market Analysis Agent provides insights about market conditions, trends, and potential opportunities. The Risk Assessment Agent provides risk score assessment on the sector as a whole, or on an investing company. The Trade Execution Agent then handles the final phase, managing the actual implementation of trading decisions. This agent ecosystem ensures a structured workflow where the Portfolio Manager coordinates all interactions between users and specialized agents, maintaining a clear chain of responsibility from initial user intent to final trade execution.

![A2A Advisory Trading Discovery and Task Delegation](docs/images/adt-discovery-and-task-delegation.png)

The implementation of Google's Agent2Agent Protocol as our communication framework ensures standardized and reliable interaction between agents. The protocol's structured communication patterns help maintain system integrity and ensure that all agents operate with consistent information and clear objectives.

Our choice of serverless infrastructure, particularly AWS Lambda and DynamoDB, serves primarily as a lightweight demonstration of how an Agent-to-Agent (A2A) network operates in practice. While the core focus of our work is implementing the A2A protocol on AWS, it's important to note that the actual hosting location of agents is flexible - agents could be hosted on EC2 instances, containers, or any other compute platform. We chose Lambda functions to provide a clear, simplified example of specialized agents communicating through HTTP endpoints via API Gateway. This setup demonstrates the fundamental principles of A2A communication while keeping the infrastructure minimal and easily reproducible. Each Lambda function represents a highly specialized agent with unique capabilities, showcasing how agents can discover, interact, and collaborate regardless of their hosting environment. DynamoDB complements this architecture by providing consistent, millisecond-level response times crucial for trading operations, while its serverless nature ensures seamless scaling alongside our Lambda-based agents.  This solution serves as a reference implementation for building agent networks and showcases how serverless computing can simplify and streamline agent-based systems.

> **Disclaimer:**
> This tool is developed primarily to demonstrate the implementation of specialized AI agents communicating via the Agent-to-Agent (A2A) protocol in a serverless architecture. The trading scenarios and agent interactions are designed to showcase the capabilities of A2A protocol in a practical context, not to provide actual investment guidance.

### Technical Stack

#### Agent2Agent Protocol Implementation
The platform leverages Google's Agent2Agent Protocol to enable:
- Structured agent-to-agent communication
- Standardized agent discovery 
- Coordinated decision-making processes

#### Serverless Infrastructure
- **Compute Layer**: AWS Lambda for scalable, event-driven processing and hosting of agents
- **Data Layer**: Amazon DynamoDB for low-latency write execution
- **API Layer**: Amazon API Gateway for RESTful endpoints
- **AI/ML Layer**: Amazon Bedrock for foundation model integration
  - Support for specialized tasks
  - Reasoning for task analysis and agent selection 

#### Next Step: LangGraph/LangChain Integration
The platform will integrate LangGraph/LangChain's capabilities for:
- Agent Orchestration
- State Management
- Reasoning Engine
- Data Processing

### Solutions Deployment

The application follows a serverless-first architecture deployed on AWS:

1. Infrastructure-as-Code using Terraform
2. Monitoring and observability with CloudWatch

#### Deployment Pre-requisite

* [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* [Terraform >= 1.8.0](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli)
* [Git CLI](https://git-scm.com/downloads)
* [Python >= 3.10](https://www.python.org/downloads/)
* [PIP >= 25.0.1](https://pypi.org/project/pip/)
* [make](https://www.gnu.org/software/make/)
* On the Console, make sure Amazon BedRock has enabled access to `Claude 3 Haiku`
* Install the following libraries for the CLI start:
```python
pip install pyfiglet colorama halo aiohttp boto3
```

* Export environment variables:
```
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_REGION=your_region
```

* **[Optional]** Setting the environment: In the Makefile of root project, check for the current configuration of the app name, environment name, and region. You may change these configuration; however, make sure that the selected region support the selected model ID of Amazon BedRock
```
##################################################
### Global variables for naming convention
##################################################

APP_NAME ?=adt
ENV_NAME ?=dev
AWS_REGION =us-east-1
```

#### Deployment Steps

To deploy the solutions, run the following in order: 

| Order | Command                         | Purpose                                                 | Dependency                                                         |
|-------|---------------------------------|---------------------------------------------------------|--------------------------------------------------------------------|
| 1     | `make deploy-core`              | Zip, add dependencies, and prepare a2a package in local | Pre-requisite                                                      |
| 2     | `make deploy-shared`            | Deploy the core a2a package from local as lambda layer  | Wait for layers/a2a_core.zip to be created in local before proceed |
| 3     | `make deploy-market-analysis`   | Deploy market analysis agent                            | a2a_core must be deployed as layer before proceed                  |
| 4     | `make deploy-risk-assessment`   | Deploy risk assessment agent                            | a2a_core must be deployed as layer before proceed                  |
| 5     | `make deploy-trade-execution`   | Deploy trade execution agent                            | a2a_core must be deployed as layer before proceed                  |
| 6     | `make deploy-portfolio-manager` | Deploy portfolio manager agent                          | a2a_core must be deployed as layer before proceed                  |
---

To destroy any module, run the following command: 

| Order | Command                           | Purpose                              |
|-------|-----------------------------------|--------------------------------------|
| 1     | `make destroy-core`               | Destroy bucket deployed for a2a core |
| 2     | `make destroy-shared`             | Destroy the a2a core layer           |
| 3     | `make destroy-market-analysis`    | Destroy market analysis agent        |
| 4     | `make destroy-risk-assessment`    | Destroy risk assessment agent        |
| 5     | `make destroy-trade-execution`    | Destroy trade execution agent        |
| 6     | `make destroy-portfolio-manager`  | Destroy portfolio manager agent      |
---

Once the infrastructure has been set up, run the following command at the project root to start the program:

```python
python3 cli.py
# or 
py cli.py
```

#### Demo

![Demo Video](docs/demo/adt-demo.mp4)

### Use Cases

While this project demonstrates implementation through a financial services example, the pattern of deploying multi-agent systems using Agent2Agent Protocol on serverless architecture can be applied across various industries:

#### Enterprise Applications
- **Supply Chain Management**
  - Inventory optimization agents
  - Logistics coordination agents
  - Supplier relationship agents
  - Demand forecasting agents

- **Customer Service**
  - Query routing agents
  - Knowledge base agents
  - Sentiment analysis agents
  - Resolution recommendation agents

#### Healthcare
- **Patient Care Coordination**
  - Diagnosis assistance agents
  - Treatment planning agents
  - Medical record analysis agents
  - Drug interaction checking agents

#### Manufacturing
- **Smart Factory Operations**
  - Production scheduling agents
  - Quality control agents
  - Maintenance prediction agents
  - Resource optimization agents

#### Retail
- **Personalized Shopping Experience**
  - Product recommendation agents
  - Inventory management agents
  - Price optimization agents
  - Customer behavior analysis agents

#### Energy Sector
- **Grid Management**
  - Load balancing agents
  - Energy trading agents
  - Consumption prediction agents
  - Maintenance scheduling agents

#### Research & Development
- **Scientific Research**
  - Data analysis agents
  - Literature review agents
  - Experiment design agents
  - Hypothesis generation agents

#### Common Patterns Across Industries
1. **Agent Specialization**
  - Domain-specific knowledge agents
  - Data processing agents
  - Decision-making agents
  - Coordination agents

2. **State Management**
  - Context preservation
  - Historical data tracking
  - Progress monitoring
  - Transaction management

3. **Integration Capabilities**
  - External API connectivity
  - Data source integration
  - Third-party service coordination
  - Legacy system interaction

4. **Scalability Considerations**
  - Load-based scaling
  - Geographic distribution
  - Resource optimization
  - Cost management

This architecture pattern is particularly valuable for scenarios requiring:
- Complex decision-making processes
- Multiple specialized knowledge domains
- Asynchronous workflows
- Scalable computing needs
