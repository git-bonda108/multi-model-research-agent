# Streamlit Cloud Deployment Guide for Sage-Lens

## 🚀 Quick Deployment Checklist

- [ ] Repository is public or Streamlit Cloud has access
- [ ] All API keys are ready
- [ ] `requirements.txt` is up to date
- [ ] `.streamlit/config.toml` exists
- [ ] Main file is `multi-model-research-agent.py`

## 📋 Step-by-Step Deployment

### Step 1: Prepare Your Repository

Ensure your repository structure looks like this:
```
multi-model-research-agent/
├── multi-model-research-agent.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml
└── .gitignore (should include .env)
```

### Step 2: Push to GitHub

```bash
git add .
git commit -m "Prepare for Streamlit Cloud deployment"
git push origin main
```

### Step 3: Deploy on Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit https://share.streamlit.io
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app"
   - Select your repository: `git-bonda108/multi-model-research-agent`
   - Branch: `main`
   - Main file path: `multi-model-research-agent.py`
   - Python version: 3.9 or higher (recommended: 3.10+)

3. **Configure Secrets**
   
   Click "Advanced settings" → "Secrets" and add:
   ```toml
   [secrets]
   OPENAI_API_KEY = "sk-..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   TAVILY_API_KEY = "tvly-..."
   SERPER_API_KEY = "..."
   ```

4. **Deploy**
   - Click "Deploy"
   - Wait 1-2 minutes for the build
   - Your app will be live!

## 🔑 Required API Keys

### Minimum Required Secrets

All four API keys are **required** for the app to function:

```toml
[secrets]
OPENAI_API_KEY = "sk-..."           # Required
ANTHROPIC_API_KEY = "sk-ant-..."    # Required
TAVILY_API_KEY = "tvly-..."         # Required
SERPER_API_KEY = "..."              # Required
```

### Getting API Keys

1. **OpenAI API Key**
   - https://platform.openai.com/api-keys
   - Create account → API Keys → Create new secret key

2. **Anthropic API Key**
   - https://console.anthropic.com/settings/keys
   - Create account → API Keys → Create key

3. **Tavily API Key**
   - https://tavily.com
   - Sign up → Dashboard → API Keys

4. **Serper API Key**
   - https://serper.dev
   - Sign up → Dashboard → API Key

## ⚙️ Configuration Files

### `.streamlit/config.toml`

Already included in the repository with optimal settings:
- Headless server mode
- Security enabled (CORS, XSRF protection)
- Fast reruns for better UX
- Modern theme

### `requirements.txt`

Minimal, clean dependencies:
- `streamlit>=1.32.0`
- `openai>=1.14.0`
- `anthropic>=0.8.0`
- `tavily-python>=0.3.0`
- `requests>=2.31.0`
- `youtube_search>=1.1.0`
- `python-dotenv>=1.0.0`

## 🔍 Verification Steps

After deployment, verify:

1. ✅ App loads without errors
2. ✅ No API key errors in the UI
3. ✅ Can enter a research topic
4. ✅ Generate button works
5. ✅ Results appear (documentation, web links, videos)
6. ✅ Version history works

## 🐛 Troubleshooting

### Build Fails

**Error**: "Module not found"
- **Solution**: Check `requirements.txt` includes all dependencies

**Error**: "Import error"
- **Solution**: Verify Python version is 3.9+

### Runtime Errors

**Error**: "Initialization failed"
- **Solution**: Check all API keys are set in Secrets

**Error**: "Search error"
- **Solution**: Verify Tavily and Serper API keys are valid

**Error**: "API rate limit exceeded"
- **Solution**: Check your API provider dashboards for usage limits

### Performance Issues

**Slow response times**
- Normal: 8-23 seconds for full processing
- If consistently slow: Check API provider status pages

**Timeout errors**
- Increase timeout in code if needed
- Check API provider status

## 📊 Monitoring

### Streamlit Cloud Metrics

Monitor your app in Streamlit Cloud dashboard:
- View count
- Error logs
- Resource usage
- Deployment history

### API Usage

Monitor API usage in each provider's dashboard:
- OpenAI: https://platform.openai.com/usage
- Anthropic: https://console.anthropic.com/settings/usage
- Tavily: Check your Tavily dashboard
- Serper: Check your Serper dashboard

## 🔒 Security Best Practices

1. **Never commit API keys** to the repository
2. **Use Streamlit Secrets** for all sensitive data
3. **Rotate API keys** regularly
4. **Monitor API usage** for unusual activity
5. **Set up rate limiting** if needed

## 💰 Cost Considerations

### API Costs (Approximate)

- **OpenAI GPT-4 Turbo**: ~$0.01-0.03 per query
- **Anthropic Claude-3.5 Sonnet**: ~$0.015-0.03 per query
- **Tavily**: Free tier available, then pay-per-use
- **Serper**: Free tier (100 queries/month), then paid

**Estimated cost per research query**: $0.03-0.06

### Cost Optimization

1. Use free tiers where possible
2. Monitor usage regularly
3. Set up usage alerts
4. Consider caching results

## 🎯 Post-Deployment

### Custom Domain (Optional)

Streamlit Cloud allows custom domains:
1. Go to app settings
2. Click "Custom domain"
3. Follow the DNS configuration steps

### Analytics (Optional)

Add analytics to track usage:
- Google Analytics
- Custom event tracking
- User behavior analysis

## 📝 Maintenance

### Regular Updates

1. **Update dependencies** monthly
2. **Check for security patches**
3. **Monitor API provider changes**
4. **Update documentation** as needed

### Backup

- Repository is automatically backed up on GitHub
- Consider backing up API keys securely
- Document any custom configurations

---

**Need help?** Open an issue on GitHub or check the main README.md

