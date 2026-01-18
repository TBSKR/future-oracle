# 🤖 AI Agent Development & Prompt Engineering Guide

This document outlines the best practices for developing and prompting the AI agents within the FutureOracle system. The goal is to create a consistent, reliable, and powerful multi-agent workforce that can be easily extended and maintained by human developers and other AI agents (like Claude or Cursor).

---

## 1. Core Principles

1.  **Role-Based Specialization:** Each agent has a clearly defined `role`, `goal`, and `backstory`. Prompts should always align with this persona. An `Analyst` thinks differently from a `Scout`.
2.  **Structured I/O:** Agents communicate through structured data (JSON, YAML) or well-defined text formats (Markdown). Avoid ambiguous natural language for inter-agent communication.
3.  **Context is King:** Provide agents with all necessary context to perform their task. This includes previous agent outputs, relevant data (e.g., stock prices), and configuration parameters.
4.  **Iterative Refinement:** Start with simple prompts and progressively add complexity. Test prompts in isolation (`notebooks/`) before integrating them into a workflow.
5.  **Think in Workflows:** No agent is an island. Design prompts with the entire agentic workflow in mind. The output of one agent is the input for the next.

---

## 2. Prompting Best Practices

### The Anatomy of a Good Prompt

A robust prompt for a CrewAI agent in this system should contain these four elements:

1.  **Persona & Goal:** Reiterate the agent's core identity. Start the prompt by reminding the agent of its role.
2.  **Context:** Provide the necessary data and background information. Use clear headings like `## Context`, `## Data`, `## Previous Analysis`.
3.  **Task & Instructions:** State the specific task clearly and unambiguously. Use numbered lists or bullet points for multi-step instructions.
4.  **Output Format:** Specify the exact output format required. Provide a template or an example.

### Example: Prompting the `Analyst` Agent

```jinja
### Persona: Deep Alpha Analyst
Your goal is to generate deep investment insights and impact predictions for breakthrough technologies. Think in decades, not quarters. Be bold but rigorous.

### Context
- **News Item:** {{ news_item.title }}
- **Source:** {{ news_item.source }}
- **Published:** {{ news_item.published_at }}
- **Summary:** {{ news_item.summary }}
- **Company:** {{ company.name }} ({{ company.ticker }})
- **Current Price:** ${{ market_data.price }}
- **52-Week Range:** ${{ market_data.low }} - ${{ market_data.high }}

### Task
Analyze the provided news item and generate a comprehensive investment analysis. Follow these steps:

1.  **Assess Impact:** Rate the significance of this development on a scale of 1-10 for its potential civilization-scale impact.
2.  **Formulate Thesis:** Write a concise investment thesis. Why does this matter for the long term?
3.  **Generate Scenarios:** Create three scenarios (Realistic, Bull, Super-Bull) with 5-year and 10-year price targets for each. Justify your targets.
4.  **Identify Risks:** List the top 3-5 risks that could invalidate this thesis.
5.  **Provide Actionable Recommendation:** State a clear action (e.g., `BUY`, `HOLD`, `WATCH`, `ACCUMULATE`) and your conviction level (`High`, `Medium`, `Low`).

### Output Format

Provide your analysis in Markdown format as follows:

---

**Impact Score:** [Your score]/10

**Thesis:**
[Your investment thesis here]

**Scenarios:**
| Scenario     | 5-Year Target | 10-Year Target | Justification |
|--------------|---------------|----------------|---------------|
| Realistic    | $XXX          | $YYYY          | ...           |
| Bull         | $XXX          | $YYYY          | ...           |
| Super-Bull   | $XXX          | $YYYY          | ...           |

**Risk Flags:**
- **Risk 1:** [Description]
- **Risk 2:** [Description]
- **Risk 3:** [Description]

**Recommendation:**
- **Action:** [Your Action]
- **Conviction:** [Your Conviction Level]

--- 
```

---

## 3. Agent Development Workflow (for AI Agents)

If you are an AI agent (like Claude or Cursor) tasked with modifying or creating a new agent, follow this workflow:

1.  **Understand the Goal:** Read the user's request and the existing documentation (`README.md`, `docs/AGENTS.md`).
2.  **Review Configuration:** Examine `config/agents.yaml` and `config/watchlist.yaml` to understand the current agent roles and data context.
3.  **Isolate & Test:** Create a new Jupyter Notebook in the `notebooks/` directory to experiment. For example, `notebooks/dev_new_agent.ipynb`.
4.  **Write Tests First (TDD):** In the notebook, write a simple test case for the new functionality. What is the ideal input and the expected output?
5.  **Implement the Agent Logic:** Create the agent's Python code in `src/agents/`. Start with a basic class structure inheriting from a `BaseAgent` if one exists.
6.  **Implement the Prompt:** Craft the prompt following the best practices in this guide. Store the prompt template in `config/agents.yaml`.
7.  **Run Tests:** Use the notebook to run your test cases against the new agent and prompt. Iterate until the tests pass.
8.  **Integrate into Workflow:** Add the new agent to a workflow in `config/agents.yaml` or a script in `scripts/`.
9.  **Document Your Work:** Update the `README.md` and this document if you've made significant changes to the architecture or added a new agent.

---

## 4. Managing Agent State & Memory

- **Stateless by Default:** Treat agents as stateless functions where possible. They receive input, perform a task, and produce an output. This makes them predictable and easy to test.
- **Passing State:** State (e.g., a list of analyzed news items) should be managed by the `Orchestrator` and passed explicitly to other agents as context in their prompts.
- **Long-Term Memory:** For memory that needs to persist across runs (e.g., portfolio holdings), use the SQLite database (`data/futureoracle.db`). The `Portfolio Guardian` is the primary interface for this database.

---

## 5. Key Prompt Snippets & Patterns

### Forcing Structured Output (JSON)

When you need a reliable JSON output, end your prompt with this:

```
Provide your response as a valid JSON object. Do not include any explanatory text or markdown formatting before or after the JSON. The JSON object must conform to the following schema:

{
  "impact_score": "number",
  "recommendation": "string",
  "confidence": "string (High/Medium/Low)"
}

Your JSON response:
```

### Chain-of-Thought Reasoning

For complex analysis, ask the agent to "think step-by-step" before giving the final answer. This improves reasoning quality.

```
First, think step-by-step about the problem. Lay out your reasoning process. Then, based on your reasoning, provide the final answer in the specified format.

**Step-by-Step Reasoning:**
[Agent's reasoning process goes here]

**Final Answer:**
[Agent's final, formatted answer goes here]
```

### Using Few-Shot Examples

Provide one or two examples of good outputs within the prompt to guide the model's response style and structure.

```
Here is an example of a good analysis:

**News:** "Figure AI signs deal with BMW."
**Analysis:**
- **Impact:** 8/10
- **Thesis:** Commercial validation for humanoid robots in manufacturing.
- **Action:** WATCH
- **Conviction:** High

Now, analyze the following news item using the same format:

**News:** {{ news_item.title }}
**Your Analysis:**
```

---

This guide is a living document. As we learn more about prompting Grok and other models, we will update it with new best practices.
