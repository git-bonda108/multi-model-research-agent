# API Keys Quick Reference

## 🔑 Required API Keys

Multi-Model Research Agent requires **4 API keys** to function properly. All are essential:

| Key | Provider | Purpose | Get It Here |
|-----|----------|---------|------------|
| `OPENAI_API_KEY` | OpenAI | GPT-4 Turbo content generation | [platform.openai.com](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Anthropic | Claude-3.5 Sonnet content generation | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `TAVILY_API_KEY` | Tavily | AI-powered web research | [tavily.com](https://tavily.com) |
| `SERPER_API_KEY` | Serper | Google search results | [serper.dev](https://serper.dev) |

## 📝 Setup Instructions

### Local Development

1. **Create `.env` file** in project root:
   ```env
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=sk-ant-...
   TAVILY_API_KEY=tvly-...
   SERPER_API_KEY=...
   ```

2. **Load environment variables**:
   - The app uses `python-dotenv` to automatically load `.env`
   - Make sure `.env` is in `.gitignore` (already included)

### Streamlit Cloud

1. Go to your app settings
2. Navigate to **Secrets**
3. Add all 4 keys in TOML format:
   ```toml
   [secrets]
   OPENAI_API_KEY = "sk-..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   TAVILY_API_KEY = "tvly-..."
   SERPER_API_KEY = "..."
   ```

## 💰 Pricing & Free Tiers

### OpenAI
- **Free Tier**: $5 credit for new users
- **Pricing**: ~$0.01-0.03 per query (GPT-4 Turbo)
- **Link**: https://openai.com/pricing

### Anthropic
- **Free Tier**: Limited free tier available
- **Pricing**: ~$0.015-0.03 per query (Claude-3.5 Sonnet)
- **Link**: https://www.anthropic.com/pricing

### Tavily
- **Free Tier**: Available with limits
- **Pricing**: Pay-per-use after free tier
- **Link**: https://tavily.com/pricing

### Serper
- **Free Tier**: 100 queries/month
- **Pricing**: $5/month for 2,500 queries
- **Link**: https://serper.dev/pricing

## ⚠️ Security Notes

1. **Never commit API keys** to Git
2. **Use `.env` locally** and **Streamlit Secrets** on Cloud
3. **Rotate keys regularly** for security
4. **Monitor usage** to detect unauthorized access
5. **Set up usage alerts** in provider dashboards

## 🔍 Verifying Keys

### Test OpenAI Key
```python
from openai import OpenAI
client = OpenAI(api_key="sk-...")
response = client.chat.completions.create(
    model="gpt-4-turbo",
    messages=[{"role": "user", "content": "test"}]
)
print("✅ OpenAI key works!")
```

### Test Anthropic Key
```python
import anthropic
client = anthropic.Anthropic(api_key="sk-ant-...")
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=10,
    messages=[{"role": "user", "content": "test"}]
)
print("✅ Anthropic key works!")
```

### Test Tavily Key
```python
from tavily import TavilyClient
client = TavilyClient(api_key="tvly-...")
results = client.search("test query", max_results=1)
print("✅ Tavily key works!")
```

### Test Serper Key
```python
import requests
response = requests.post(
    "https://google.serper.dev/search",
    headers={"X-API-KEY": "..."},
    json={"q": "test"}
)
print("✅ Serper key works!")
```

## 🐛 Troubleshooting

### "Initialization failed" Error
- **Cause**: Missing or invalid API keys
- **Solution**: Verify all keys are set correctly in `.env` or Streamlit Secrets

### "API rate limit exceeded"
- **Cause**: Too many requests
- **Solution**: Wait or upgrade your API plan

### "Invalid API key"
- **Cause**: Key is incorrect or expired
- **Solution**: Generate a new key from the provider dashboard

### "Insufficient credits"
- **Cause**: Account has no credits/balance
- **Solution**: Add credits to your account

## 📊 Monitoring Usage

### OpenAI
- Dashboard: https://platform.openai.com/usage
- Set up usage alerts in account settings

### Anthropic
- Dashboard: https://console.anthropic.com/settings/usage
- Monitor usage in real-time

### Tavily
- Check usage in your Tavily dashboard
- Set up alerts for usage limits

### Serper
- Dashboard: https://serper.dev/dashboard
- Track queries per month

---

**Need help?** Check the main README.md or open an issue on GitHub.

