# 🔐 Streamlit Secrets Setup Guide

## Why This Matters

The Multi-Model Research Agent app now supports **both** local development (using `.env` files) and Streamlit Cloud deployment (using `st.secrets`). The code automatically detects which environment it's running in and uses the appropriate method.

## ✅ How It Works

The app checks for secrets in this order:
1. **Streamlit Cloud**: `st.secrets["KEY_NAME"]` (when deployed)
2. **Local Development**: `os.getenv("KEY_NAME")` from `.env` file

This means:
- ✅ Works locally with `.env` file
- ✅ Works on Streamlit Cloud with Secrets
- ✅ No code changes needed between environments

## 🚀 Setting Up Secrets on Streamlit Cloud

### Step 1: Go to Your App Settings

1. Visit https://share.streamlit.io/
2. Click on your app
3. Click **"Settings"** (gear icon)
4. Click **"Secrets"** tab

### Step 2: Add Your API Keys

Paste this into the Secrets editor:

```toml
[secrets]
OPENAI_API_KEY = "sk-proj-..."
ANTHROPIC_API_KEY = "sk-ant-api03-..."
TAVILY_API_KEY = "tvly-dev-..."
SERPER_API_KEY = "your-serper-key-here"
```

### Step 3: Save and Restart

1. Click **"Save"**
2. The app will automatically restart
3. Your secrets are now active!

## 🏠 Local Development Setup

For local development, create a `.env` file in the project root:

```env
OPENAI_API_KEY="sk-proj-..."
ANTHROPIC_API_KEY="sk-ant-api03-..."
TAVILY_API_KEY="tvly-dev-..."
SERPER_API_KEY="xoM7QXTQZt5tMMmEGokLhi6w"
```

**Important**: The `.env` file is in `.gitignore` and will NOT be committed to Git.

## 🔍 Verifying Secrets Are Set

### On Streamlit Cloud

1. Check the app logs for any authentication errors
2. If you see "OPENAI_API_KEY is not set", the secrets weren't saved correctly
3. Go back to Settings → Secrets and verify they're there

### Locally

```bash
# Test that .env is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('OPENAI_API_KEY:', 'Set' if os.getenv('OPENAI_API_KEY') else 'Missing')"
```

## ⚠️ Common Issues

### Issue: "OPENAI_API_KEY is not set" on Streamlit Cloud

**Solution:**
1. Go to Settings → Secrets
2. Verify the key name is exactly `OPENAI_API_KEY` (case-sensitive)
3. Make sure there are no extra spaces
4. Click "Save"
5. Wait for app to restart

### Issue: Secrets not working after update

**Solution:**
1. The app should auto-restart, but you can manually trigger a restart
2. Go to Settings → "Reboot app"
3. Check logs to verify secrets are loaded

### Issue: Works locally but not on Cloud

**Solution:**
- This means secrets aren't set in Streamlit Cloud
- Follow "Setting Up Secrets on Streamlit Cloud" above
- Double-check the key names match exactly

## 🔒 Security Best Practices

1. ✅ **Never commit secrets** to Git (`.env` is in `.gitignore`)
2. ✅ **Use Streamlit Secrets** for production (not `.env` files)
3. ✅ **Rotate keys regularly** for security
4. ✅ **Use different keys** for development and production
5. ✅ **Monitor API usage** to detect unauthorized access

## 📝 Secret Names Reference

The app expects these exact secret names (case-sensitive):

| Secret Name | Required | Purpose |
|------------|----------|---------|
| `OPENAI_API_KEY` | ✅ Yes | GPT-4 Turbo content generation |
| `ANTHROPIC_API_KEY` | ✅ Yes | Claude 3.5 Sonnet content generation |
| `TAVILY_API_KEY` | ⚠️ Optional | Web search (app works without it) |
| `SERPER_API_KEY` | ⚠️ Optional | Google search (app works without it) |

## ✅ Verification Checklist

After setting up secrets:

- [ ] All required secrets are in Streamlit Cloud Secrets
- [ ] Secret names match exactly (case-sensitive)
- [ ] No extra spaces in secret values
- [ ] App restarted after saving secrets
- [ ] No authentication errors in logs
- [ ] App can generate content successfully

---

**Your app should now work perfectly on Streamlit Cloud! 🎉**

