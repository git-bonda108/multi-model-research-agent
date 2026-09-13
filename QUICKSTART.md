# 🚀 Quick Start Guide - Multi-Model Research Agent

## Prerequisites Check

Run the setup test to verify everything is configured:

```bash
python test_setup.py
```

## Running the Application

### Option 1: Direct Streamlit Command

```bash
python -m streamlit run research_agent_app.py
```

### Option 2: Using Streamlit CLI

```bash
streamlit run research_agent_app.py
```

### Option 3: With Custom Port

```bash
streamlit run research_agent_app.py --server.port 8502
```

## First Run

1. **Open your browser** to `http://localhost:8501`
2. **Check the sidebar** - you should see configuration options
3. **Enable Agentic AI** if you want to use the advanced features
4. **Enter a research topic** in the main text area
5. **Click "🚀 Generate"** to start

## Example Queries

Try these research topics:

- "Transformer Architecture Optimization"
- "Quantum Computing Applications in Machine Learning"
- "Climate Change Solutions and Renewable Energy"
- "Large Language Models: Current State and Future Trends"
- "Neural Network Interpretability Methods"

## Troubleshooting

### App won't start

- Check that port 8501 is not in use
- Verify Python version is 3.9+
- Run `python test_setup.py` to check dependencies

### API errors

- Verify API keys in `.env` file
- Check API key permissions and quotas
- Ensure billing is active

### Agentic features not working

- Install OpenAI Agents SDK: `pip install openai-agents`
- Check that OPENAI_API_KEY is set
- Review console for error messages

## Next Steps

- Read `README_ENHANCED.md` for detailed documentation
- Explore the different tabs in the UI
- Check version history for previous queries
- Review the analysis tab for insights

---

**Happy Researching! 🔬**

