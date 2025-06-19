# Memory Types in Agents: Insurance Domain Examples

This repository demonstrates how different types of memory enhance AI-powered customer support systems using insurance domain examples. By incorporating various memory types, support agents can provide more personalized, accurate, and efficient service.

## Overview

Memory is crucial for creating intelligent customer support systems. This project showcases four fundamental types of memory and their impact on service quality:

1. **Short-Term Memory** - Maintains conversation context
2. **Long-Term Memory**: Persistent Knowledge
    - **Semantic Memory** - Stores general knowledge and concepts
    - **Episodic Memory** - Remembers specific customer events
    - **Factual Memory** - Retains user preferences and persistent attributes

| Memory Type  | Purpose                                           | Use Cases                                          | Benefits                                              |
| ------------ | ------------------------------------------------- | -------------------------------------------------- | ----------------------------------------------------- |
| **Semantic** | Facts, knowledge relationships & domain expertise | Insurance policy understanding, coverage patterns  | Accumulated domain knowledge, cross-customer insights |
| **Episodic** | Specific interaction history                      | Case continuity, pattern recognition               | Seamless follow-ups, learning from history            |
| **Factual**  | User preferences & persistent attributes          | Communication style, technical level, risk profile | Personalized interactions, tailored responses         |

Each memory type serves a unique purpose and, when combined, creates a support experience that feels natural, knowledgeable, and personalized.

---

## Mem0 + AWS

Mem0 can be integrated with Bedrock models and OpenSearch serverless for vector store. Go through this example for more details - https://docs.mem0.ai/examples/aws_example

For this demo we are going to use mem0 managed platform

## Short-Term Memory in Customer Support

### Core Philosophy: Context Preservation Throughout Conversations

Short-term memory maintains information throughout an active conversation or session. It remembers what you discussed earlier in the chat, uploaded files, and relevant context from the current interaction. However, this memory is ephemeral—once you end the session, it's gone. This type of memory enables agents to provide coherent, contextual responses without asking you to repeat information within the same conversation.

### Real-World Insurance Examples

**Multi-Turn Claim Filing Conversation:**
```python
"conversation": [
    {
        "role": "customer",
        "content": "I need to file a claim. I was in an accident yesterday at 3:45 PM at the intersection of Main and 5th Street."
    },
    {
        "role": "agent",
        "content": "I'm sorry to hear about your accident yesterday at Main and 5th Street. I'll help you file this claim right away. Since it occurred at 3:45 PM, was this during rush hour traffic?"
    },
    {
        "role": "customer",
        "content": "Yes, it was pretty busy. The other driver ran a red light and hit my passenger side."
    },
    {
        "role": "agent",
        "content": "That must have been frightening. So we have a collision at Main and 5th yesterday at 3:45 PM, where another driver ran a red light and struck your passenger side. Were you or any passengers injured?"
    },
    {
        "role": "customer",
        "content": "My daughter had some neck pain but we went to urgent care and she's okay now."
    },
    {
        "role": "agent",
        "content": "I'm glad your daughter is okay now. I'll note that she received medical attention at urgent care for neck pain. Given all the details - the accident yesterday at 3:45 PM at Main and 5th, the red light violation, passenger side damage, and your daughter's urgent care visit - I'll need claim numbers for both vehicle damage and medical expenses."
    }
]
```

**Context Accumulated:**
- Each message is added to the state
- Every response sees the full conversation history
- No information is lost or needs to be extracted
- Context builds organically with each turn

### Implementation Architecture

```python
class ConversationState(TypedDict):
    """The state IS the short-term memory"""
    messages: List[Dict[str, str]]
    customer_id: str

async def respond_with_memory(state: ConversationState) -> ConversationState:
    """Generate response using the full conversation history (short-term memory)"""
    
    # The entire conversation history IS the short-term memory
    # No extraction needed - just pass it to the LLM
    response = await llm.ainvoke(state["messages"])
    
    # Add response to conversation state
    state["messages"].append({
        "role": "assistant",
        "content": response.content
    })
    
    return state

# Simple workflow - state maintains itself
workflow = StateGraph(ConversationState)
workflow.add_node("respond", respond_with_memory)
workflow.set_entry_point("respond")
workflow.add_edge("respond", END)
```

### Key Features

**Conversation History Maintenance**
```python
# Build complete conversation context
conversation_history = "\n".join([
    f"{msg['role']}: {msg['content']}" 
    for msg in state["messages"]
])

# Never ask for information already provided
if context["accident_date"]:
    context_summary.append(f"Accident occurred: {context['accident_date']}")
```

**Information Accumulation**

```python
# The conversation state grows naturally
# No parsing, no extraction, just accumulation
Turn 1: [accident info message]
Turn 2: [accident info, fault info messages]  
Turn 3: [accident info, fault info, injury info messages]
Turn 4: [all previous messages plus witness info]

# Each response has complete context
```

### Use Cases

1. **Complex Multi-Step Processes**: The agent naturally tracks all details across multiple turns without any special logic - "Since you already mentioned your daughter was treated at Springfield Urgent Care for the accident yesterday at 3:45 PM..."

2. **Same-Day Callbacks**: The conversation state can be persisted and restored - "I see from our earlier conversation today about your accident at Main and 5th. Your claim number is CLM-789456."

3. **Information Building**: Each turn adds to the complete picture without repetition - no need to ask "What was the location again?" because it's all in the state.

4. **Natural Dialogue Flow**: Responses reference any part of the conversation naturally - "You mentioned the other driver ran a red light and hit your passenger side where your daughter was sitting..."

---

## Semantic Memory in Customer Support

### Core Philosophy: Knowledge Emerges from Interactions

Semantic memory stores factual information and learned concepts about users and topics. For AI agents, this includes user details, preferences, and specific facts that should influence future interactions. Unlike traditional knowledge bases, semantic memory in this implementation demonstrates how **domain expertise accumulates organically** from real customer conversations. Mem0 automatically extracts semantic insights without manual knowledge curation.

### Real-World Insurance Examples

**Prior Conversations that Build Knowledge:**
```python
"conversation": [
    {
        "role": "customer",
        "content": "My neighbor's tree looks diseased and is leaning toward my house. If it falls and damages my roof, whose insurance covers it?"
    },
    {
        "role": "agent",
        "content": "Great question! This is a common concern. If the tree falls due to natural causes like wind, disease, or storms, YOUR homeowner's insurance would cover the damage to your house, regardless of whose tree it is. This falls under your property coverage with your deductible applying."
    },
    {
        "role": "customer",
        "content": "Really? Even though it's their tree? That doesn't seem fair."
    },
    {
        "role": "agent",
        "content": "I understand it seems counterintuitive, but this is standard across all insurance companies. It's based on the legal principle that acts of nature are 'Acts of God' - no one's at fault. However, there's an important exception: if you formally notify your neighbor in writing that their tree is dangerous and they ignore it, then they could be liable for negligence."
    }
]
```

**Semantic Knowledge Extracted:**
- Acts of God = natural events where no one is at fault
- Tree damage follows "where it lands" rule
- Written notification shifts Act of God to negligence
- Property coverage vs. liability coverage distinction

### Implementation Architecture

```python
async def retrieve_semantic_knowledge(state: SupportState) -> SupportState:
    """Retrieve relevant semantic (general) knowledge about insurance concepts"""
    
    # Search for general insurance knowledge related to the query
    semantic_memories = memory_client.search(
        query=state["customer_query"],
        agent_id="insurance_semantic_agent",
        limit=5
    )
    
    state["semantic_knowledge"] = semantic_memories
    return state
```

### Key Features

**Cross-Customer Knowledge Application**
```python
# Knowledge from one customer helps another
Customer A: "If neighbor's tree falls on my house, who pays?"
Agent: [Explains Acts of God principle]

Customer B: "Storm knocked neighbor's tree on my garage, they say it's my problem"
Agent: [Applies learned principle] "Your neighbor is correct..."
```

**Concept Understanding**
```python
# Store generalized concepts
semantic_knowledge = [
    {
        "content": "Property coverage is first-party insurance covering damage to YOUR property. Liability coverage is third-party insurance covering damage you cause to OTHERS.",
        "metadata": {"type": "semantic_knowledge", "category": "coverage_types"}
    }
]
```

### Use Cases

1. **Concept Application**: "Your situation is different - since you warned them about the dead tree, this shifts from an Act of God to negligence."

2. **Knowledge Transfer**: "Like with tree damage, hail damage to your roof falls under property coverage, not liability."

---

## Episodic Memory in Customer Support

### Core Philosophy: Every Customer Has a Unique Story

Episodic memory ensures that **specific customer events, circumstances, and history are remembered**, creating a personalized experience where customers feel valued and understood. Each interaction builds upon their unique journey.

### Real-World Insurance Examples

**Customer's Personal History:**
```python
"conversation": [
    {
        "role": "customer",
        "content": "I have a major problem. A pipe burst in our basement and there's water everywhere. My elderly mother lives with us and her medical equipment is down there."
    },
    {
        "role": "agent",
        "content": "This is definitely urgent. First, have you shut off the main water valve?"
    },
    {
        "role": "customer",
        "content": "Yes, my husband did that. But my mother's oxygen concentrator, her CPAP machine, and her electric wheelchair are all in standing water. She has severe COPD and can't be without oxygen for long."
    },
    {
        "role": "agent",
        "content": "I understand the critical nature. I'm immediately dispatching ServePro for emergency water mitigation - they'll be there within 2 hours. I'm authorizing an emergency equipment rental. Call Brookdale Medical Supplies at 555-MEDICAL - tell them claim CLM-WATER-8899 pre-authorizes immediate rental."
    }
]

# Six months later:
"conversation": [
    {
        "role": "customer",
        "content": "Hi, I need help. We're having another water issue, this time from the water heater."
    },
    {
        "role": "agent",
        "content": "Oh no, not again! I see you had the burst pipe incident in January that affected your mother's medical equipment. Is she and her equipment safe this time? I know she depends on her oxygen concentrator and CPAP machine."
    }
]
```

**Personal Details Remembered:**
- Mother lives with them
- Mother has COPD
- Medical equipment: oxygen concentrator, CPAP, wheelchair
- Previous water damage claim
- 12-year customer loyalty

### Implementation Architecture

```python
async def retrieve_customer_history(state: CustomerState) -> CustomerState:
    """Retrieve specific customer's episodic memories"""
    
    # Search for this specific customer's past interactions
    customer_memories = memory_client.search(
        query=state["customer_query"],
        user_id=state["customer_id"],
        limit=10
    )
    
    state["customer_history"] = customer_memories
    state["is_returning_customer"] = len(customer_memories) > 0
    return state
```

### Key Features

**Personal Context Awareness**
```python
# Retrieve and reference specific past events
memory_context = []
for memory in customer_memories:
    memory_content = memory.get('memory', '')
    if memory_content:
        memory_context.append(memory_content)

# Generate personalized response
"I understand your concern. Looking at your history, the January claim 
was clearly unavoidable - burst pipe during a freeze."
```

**Relationship Building**
```python
# Acknowledge customer tenure and history
if customer_context.get('tenure_years', 0) > 10:
    response += "As a valued 12-year customer, we're here for you..."
```

### Use Cases

1. **Pattern Identification**: "I notice this is your second water-related claim. Two different causes (frozen pipe vs. water heater) won't trigger non-renewal."

2. **Proactive Service**: "Since you mentioned your mother's equipment was relocated upstairs, shall I update your policy to reflect the renovated basement?"

---

## Factual Memory in Customer Support

### Core Philosophy: Know Your Customer's Persistent Preferences

Factual memory stores persistent facts about customers that shape how we communicate with them - their preferences, style, technical level, and personal context. This ensures every interaction is tailored to who they are.

### Real-World Insurance Examples

**Teen Driver Addition Process:**
```python
"conversation": [
    {
        "role": "customer",
        "content": "Hi, I need to review my policies. I'm not very tech-savvy, so please keep explanations simple. Also, I prefer phone calls over emails - I can never find emails in my inbox!"
    },
    {
        "role": "agent",
        "content": "Absolutely! I'll keep everything straightforward and avoid technical jargon. I've noted that you prefer phone communication. Would you like me to call you to discuss your policy review?"
    },
    {
        "role": "customer",
        "content": "Yes, please. I'm usually available mornings before 11 AM. I'm retired so I have time to talk through things properly."
    },
    {
        "role": "agent",
        "content": "Perfect! I've noted that morning calls work best for you. Since you have time for detailed discussions, I'll make sure we cover everything thoroughly but in simple terms."
    },
    {
        "role": "customer",
        "content": "I'm very safety-conscious, prefer comprehensive coverage even if it costs more. Peace of mind is worth it at my age."
    }
]
```

**Factual Information Stored:**
Not tech-savvy, prefers simple explanations
Prefers phone calls over emails
Best contact time: mornings before 11 AM
Retired with time for detailed discussions
Safety-conscious, values comprehensive coverage
Prioritizes peace of mind over cost savings

### Implementation Architecture

```python
async def generate_factual_aware_response(state: FactualMemoryState) -> FactualMemoryState:
    """Generate response tailored to customer's factual profile"""
    
    # Extract factual information
    factual_context = "\n".join([
        memory.get('memory', '') for memory in state["factual_memories"]
    ])
    
    prompt = f"""
    Customer Query: {state["customer_query"]}
    
    Customer's Known Preferences and Facts:
    {factual_context if factual_context else "No preferences found"}
    
    Adapt your response to match their:
    - Communication style (simple/technical)
    - Contact preferences (email/phone/text)
    - Risk tolerance (conservative/moderate/aggressive)
    - Personal context (retired/busy/business owner)
    """
    
    response = await llm.ainvoke(prompt)
    state["response"] = response.content.strip()
```


---

## Integrated Memory Architecture

### Combining All Memory Types

In real-world scenarios, multiple memory types work together:

```python
class IntegratedMemorySystem:
    def __init__(self, memory_client):
        self.memory_weights = {
            MemoryType.SHORT_TERM: 1.0,
            MemoryType.EPISODIC: 0.8,    
            MemoryType.FACTUAL: 0.7,    
            MemoryType.SEMANTIC: 0.6       
        }
```

### Complex Scenario Example

**Customer with History Needs Multiple Services:**
```
Customer: "Remember my water damage claim from January with my mother's 
medical equipment? Well, now I need to add my 16-year-old son to our 
auto policy. Given our claim history, will this affect our rates?"

Memory Integration:
- Short-term: Current conversation about teen driver
- Episodic: Previous water damage, mother's medical needs
- Semantic: How claims affect rates across different policy types
- Factual: Customer prefers simple explanations, conservative coverage

Response: "I remember your water damage claim - I hope your mother's 
equipment situation is stable now. Good news in simple terms: home 
insurance claims don't affect auto rates, they're separate. For your 
son, I recommend comprehensive coverage for peace of mind. With his 
good grades, the increase will be about $175/month. Shall I call you 
tomorrow morning to finalize everything?"
```

## Getting Started

1. Clone this repository
2. Install required dependencies:
   ```bash
   pip install mem0 langgraph langchain-aws
   ```
3. Set up your API keys:
   ```python
   os.environ["MEM0_API_KEY"] = "your-mem0-api-key"
   ```
4. Run the Jupyter notebooks to see each memory type in action

## Repository Structure

```
├── README.md
├── notebooks/
│   ├── 1_short_term_memory.ipynb
│   ├── 2_semantic_memory.ipynb
│   ├── 3_episodic_memory.ipynb
│   ├── 4_factual_memory.ipynb
│   └── 5_integrated_memory.ipynb
└── requirements.txt
```

## Conclusion

By implementing these four types of memory, AI support systems transform from simple chatbots into intelligent agents that:
- Never ask customers to repeat information (Short-term)
- Understand domain concepts deeply (Semantic)
- Remember each customer's unique journey (Episodic)
- Personalize every interaction to preferences (Factual)
