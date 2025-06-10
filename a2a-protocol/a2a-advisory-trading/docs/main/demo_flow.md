# Demo Flow

User input their financial profile and requests. 

![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-01.png)

The Portfolio Manager orchestrates and delegates tasks to the specialized agents.
Agents response after completing their tasks.

In this scenario, the tasks were delegated to Market Analysis and Risk Assessment agents. 

Response from Market Analysis agent: 
![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-02.png)

Response from Risk Assessment agent:
![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-03.png)

User can continue to follow-up with more questions during the conversation.
User expresses their interest to make a trade with the Portfolio Manager.

In this scenario, the user clearly states the amount of investment they want to put in.
![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-04.png)

Portfolio Manager delegates task to Risk Assessment to analyze the investment risk in the context of expecting investment amount, term, and user profile.
![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-05.png)

Knowing the analysis result, user should confirm their stock selection, quantity, and intention of buying or selling.

![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-06.png)

Portfolio Manager then delegates task to Trade Execution.

![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-07.png)

Once a trade is confirmed, user can see its execution history written to the DynamoDB.

![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-08.png)

User can review all agents activities and input history by clicking on CloudWatch log groups.

![A2A Advisory Trading Demo](../demo/adt-demo-screenshot-09.png)
