# 🚀 DeepSeek API Integration Guide

**Last Updated**: October 28, 2025  
**Model**: DeepSeek Chat v3.1  
**Status**: Ready for Integration

---

## 📋 Overview

DeepSeek is currently the **#1 performing AI model** in the AI-Trader competition with **+10.61% returns**, significantly outperforming the baseline QQQ index (+2.30%). This guide will help you enable DeepSeek for your trading experiments.

---

## ✅ Prerequisites

Before you begin, ensure you have:
- ✅ AI-Trader project set up
- ✅ Python dependencies installed
- ✅ MCP services running
- ✅ Internet connection

---

## 🔑 Step 1: Get DeepSeek API Key

### Option A: Official DeepSeek Platform (Recommended)

1. **Visit DeepSeek Platform**
   ```
   https://platform.deepseek.com/
   ```

2. **Create Account**
   - Sign up with email
   - Verify your email address
   - Complete registration

3. **Generate API Key**
   - Navigate to: Dashboard → API Keys
   - Click "Create API Key"
   - Copy and save your API key securely
   - **⚠️ Important**: Save it now - you won't see it again!

4. **Pricing Information** (Check current rates)
   - DeepSeek typically offers competitive pricing
   - May have free tier for testing
   - Pay-as-you-go model available
   - Check: https://platform.deepseek.com/pricing

### Option B: Through OpenRouter (Alternative)

If you prefer unified API access:

1. **Visit OpenRouter**
   ```
   https://openrouter.ai/
   ```

2. **Get API Key**
   - Sign up and get OpenRouter API key
   - OpenRouter provides access to multiple models including DeepSeek
   - Use model: `deepseek/deepseek-chat`

---

## ⚙️ Step 2: Configure Environment Variables

### Edit `.env` File

```bash
cd /home/mfan/work/aitrader
nano .env
```

### Add DeepSeek Credentials

The `.env` file has already been updated with placeholders. Replace with your actual API key:

```bash
# DeepSeek API configuration
DEEPSEEK_API_BASE="https://api.deepseek.com/v1"
DEEPSEEK_API_KEY="sk-your-actual-deepseek-api-key-here"
```

### Full `.env` Example

```bash
# AI Model API configuration
# OpenAI (for GPT models)
OPENAI_API_BASE="https://api.openai.com/v1"
OPENAI_API_KEY="sk-your-openai-key"

# DeepSeek API configuration
DEEPSEEK_API_BASE="https://api.deepseek.com/v1"
DEEPSEEK_API_KEY="sk-your-deepseek-key"

# Data Source configuration
ALPHAADVANTAGE_API_KEY="your-alpha-vantage-key"
JINA_API_KEY="your-jina-key"

# Service Port Configuration
MATH_HTTP_PORT=8000
SEARCH_HTTP_PORT=8001
TRADE_HTTP_PORT=8002
GETPRICE_HTTP_PORT=8003

# AI Agent Configuration
AGENT_MAX_STEP=30

# System Configuration
RUNTIME_ENV_PATH="/home/mfan/work/aitrader/runtime_env.json"
```

**⚠️ Security Reminder**: Never commit `.env` to git! (Already protected by `.gitignore`)

---

## 🔧 Step 3: Enable DeepSeek in Configuration

### Option A: Edit Configuration File

```bash
cd /home/mfan/work/aitrader
nano configs/default_config.json
```

Find the DeepSeek model entry and change `"enabled": false` to `"enabled": true`:

```json
{
  "name": "deepseek-chat-v3.1",
  "basemodel": "deepseek-chat",
  "signature": "deepseek-chat-v3.1",
  "enabled": true,
  "openai_base_url": "https://api.deepseek.com/v1",
  "openai_api_key": null
}
```

**Configuration Fields Explained**:
- `name`: Display name for the model
- `basemodel`: Model identifier for API calls (use `deepseek-chat`)
- `signature`: Unique identifier for saving trading data
- `enabled`: Set to `true` to run this model
- `openai_base_url`: DeepSeek API endpoint
- `openai_api_key`: `null` means it will read from `DEEPSEEK_API_KEY` in `.env`

### Option B: Use Environment-Specific API Key

If you want to use a different API key for DeepSeek (not from `.env`), you can specify it directly:

```json
{
  "name": "deepseek-chat-v3.1",
  "basemodel": "deepseek-chat",
  "signature": "deepseek-chat-v3.1",
  "enabled": true,
  "openai_base_url": "https://api.deepseek.com/v1",
  "openai_api_key": "sk-your-specific-deepseek-key"
}
```

---

## 🎯 Step 4: How the Code Reads DeepSeek Configuration

The `BaseAgent` class handles API configuration automatically:

### From `agent/base_agent/base_agent.py`:

```python
# If openai_base_url is None, use default from .env
if openai_base_url == None:
    self.openai_base_url = os.getenv("OPENAI_API_BASE")
else:
    self.openai_base_url = openai_base_url  # Use config value

# If openai_api_key is None, read from .env
if openai_api_key == None:
    self.openai_api_key = os.getenv("OPENAI_API_KEY")
else:
    self.openai_api_key = openai_api_key  # Use config value
```

**However**, for DeepSeek to work properly, you need to ensure it reads `DEEPSEEK_API_KEY`. 

### ⚠️ Important Note

The current code reads `OPENAI_API_KEY` by default. For DeepSeek, you have two options:

**Option 1: Set DEEPSEEK_API_KEY as OPENAI_API_KEY** (Quick workaround)
```bash
# In .env, temporarily use DeepSeek key as OpenAI key when running DeepSeek
OPENAI_API_KEY="your-deepseek-api-key"
```

**Option 2: Specify key directly in config** (Recommended)
```json
{
  "name": "deepseek-chat-v3.1",
  "basemodel": "deepseek-chat",
  "signature": "deepseek-chat-v3.1",
  "enabled": true,
  "openai_base_url": "https://api.deepseek.com/v1",
  "openai_api_key": "YOUR_DEEPSEEK_API_KEY_FROM_ENV"
}
```

---

## 🚀 Step 5: Run AI-Trader with DeepSeek

### Quick Test (DeepSeek Only)

```bash
cd /home/mfan/work/aitrader

# Make sure only DeepSeek is enabled in config
# Disable other models to test DeepSeek first

# Run
python3 main.py
```

### Run with Multiple Models

```bash
cd /home/mfan/work/aitrader

# Enable multiple models in configs/default_config.json
# For example: gpt-5 and deepseek-chat-v3.1

# Run
python3 main.py
```

### Using the Shell Script

```bash
cd /home/mfan/work/aitrader
./main.sh
```

---

## 📊 Step 6: Verify DeepSeek is Running

### Check Console Output

You should see:

```
🚀 Starting trading experiment
🤖 Agent type: BaseAgent
📅 Date range: 2025-10-01 to 2025-10-15
🤖 Model list: ['deepseek-chat-v3.1']
⚙️  Agent config: max_steps=30, max_retries=3, base_delay=1.0, initial_cash=10000.0
============================================================
🤖 Processing model: deepseek-chat-v3.1
📝 Signature: deepseek-chat-v3.1
🔧 BaseModel: deepseek-chat
✅ BaseAgent instance created successfully
✅ Initialization successful
📈 Starting trading session: 2025-10-01
...
```

### Check Trading Data

```bash
# Verify data directory was created
ls -la data/agent_data/

# Should see:
# deepseek-chat-v3.1/

# Check position file
cat data/agent_data/deepseek-chat-v3.1/position/position.jsonl

# Check logs
ls data/agent_data/deepseek-chat-v3.1/log/
```

---

## 🔍 Step 7: Monitor DeepSeek Performance

### Real-Time Monitoring

```bash
# Watch position updates
watch -n 5 'tail -n 3 data/agent_data/deepseek-chat-v3.1/position/position.jsonl'

# View latest log
tail -f data/agent_data/deepseek-chat-v3.1/log/$(ls data/agent_data/deepseek-chat-v3.1/log/ | tail -1)/log.jsonl
```

### Check Results After Completion

```bash
# View all positions
cat data/agent_data/deepseek-chat-v3.1/position/position.jsonl | jq .

# Count trading days processed
wc -l data/agent_data/deepseek-chat-v3.1/position/position.jsonl

# Calculate final returns
python3 -c "
import json
with open('data/agent_data/deepseek-chat-v3.1/position/position.jsonl') as f:
    lines = f.readlines()
    initial = json.loads(lines[0])
    final = json.loads(lines[-1])
    initial_cash = initial['positions']['CASH']
    final_cash = final['positions']['CASH']
    print(f'Initial: \${initial_cash}')
    print(f'Final: \${final_cash}')
    print(f'Return: {((final_cash/initial_cash - 1) * 100):.2f}%')
"
```

---

## 🐛 Troubleshooting

### Issue 1: Authentication Error

**Error**: `AuthenticationError: Invalid API key`

**Solution**:
1. Verify your API key is correct in `.env`
2. Check you copied the entire key (no spaces)
3. Ensure the key is active on DeepSeek platform
4. Check your account has available credits

```bash
# Test API key
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer YOUR_DEEPSEEK_API_KEY"
```

### Issue 2: Model Not Found

**Error**: `Model deepseek/deepseek-chat-v3.1 not found`

**Solution**: 
Update `basemodel` in config to correct model name:

```json
"basemodel": "deepseek-chat"
```

Valid DeepSeek model names:
- `deepseek-chat` (latest version)
- `deepseek-coder` (for coding tasks)

### Issue 3: Wrong API Key Being Used

**Error**: DeepSeek returns error about OpenAI API key

**Solution**: 
Specify the API key directly in config:

```json
{
  "name": "deepseek-chat-v3.1",
  "basemodel": "deepseek-chat",
  "signature": "deepseek-chat-v3.1",
  "enabled": true,
  "openai_base_url": "https://api.deepseek.com/v1",
  "openai_api_key": "sk-your-deepseek-key-here"
}
```

### Issue 4: Rate Limit Exceeded

**Error**: `RateLimitError: Too many requests`

**Solution**:
1. Increase `base_delay` in config:
   ```json
   "agent_config": {
     "base_delay": 2.0
   }
   ```
2. Check your DeepSeek account limits
3. Upgrade to higher tier if needed

### Issue 5: Connection Timeout

**Error**: `Timeout waiting for response`

**Solution**:
1. Check internet connection
2. Verify DeepSeek API status: https://status.deepseek.com/
3. Increase timeout in code (if needed)

---

## 💡 Best Practices

### 1. Test First with Small Date Range

```json
"date_range": {
  "init_date": "2025-10-01",
  "end_date": "2025-10-03"
}
```

### 2. Monitor API Costs

- Check DeepSeek dashboard for usage
- Set budget alerts
- Start with small experiments

### 3. Compare with Baseline

Run both DeepSeek and a baseline model (e.g., GPT-5) to compare:

```json
"models": [
  {
    "name": "gpt-5",
    "enabled": true
  },
  {
    "name": "deepseek-chat-v3.1",
    "enabled": true
  }
]
```

### 4. Save Results

```bash
# Export results for analysis
cp -r data/agent_data/deepseek-chat-v3.1 ~/deepseek-results-$(date +%Y%m%d)
```

---

## 📈 Expected Performance

Based on the competition leaderboard:

- **DeepSeek**: +10.61% returns (Best performer)
- **Baseline (QQQ)**: +2.30%
- **Outperformance**: +8.31 percentage points

DeepSeek has shown superior performance due to:
- 🧠 Better market analysis
- 📊 More strategic position sizing
- ⚡ Quick adaptation to market trends
- 🎯 Strong risk management

---

## 🔄 Alternative: Using OpenRouter

If you prefer unified API access:

### Step 1: Get OpenRouter Key

```
https://openrouter.ai/
```

### Step 2: Update Config

```json
{
  "name": "deepseek-chat-v3.1",
  "basemodel": "deepseek/deepseek-chat",
  "signature": "deepseek-chat-v3.1",
  "enabled": true,
  "openai_base_url": "https://openrouter.ai/api/v1",
  "openai_api_key": "sk-or-v1-your-openrouter-key"
}
```

**Advantages of OpenRouter**:
- ✅ Single API key for multiple models
- ✅ Automatic fallbacks
- ✅ Usage tracking
- ✅ Cost comparison

---

## 📚 Additional Resources

### DeepSeek Documentation
- Platform: https://platform.deepseek.com/
- API Docs: https://platform.deepseek.com/api-docs/
- Pricing: https://platform.deepseek.com/pricing

### AI-Trader Project
- Main README: `README.md`
- Running Guide: `RUNNING_GUIDE.md`
- Deep Analysis: `Claude.md`

### LangChain Documentation
- ChatOpenAI: https://python.langchain.com/docs/integrations/chat/openai

---

## ✅ Quick Start Checklist

Before running DeepSeek, ensure:

- [ ] DeepSeek API key obtained
- [ ] API key added to `.env` file
- [ ] DeepSeek enabled in `configs/default_config.json`
- [ ] Correct `basemodel` name (`deepseek-chat`)
- [ ] API URL is `https://api.deepseek.com/v1`
- [ ] Price data is downloaded (`merged.jsonl` exists)
- [ ] MCP services are running
- [ ] Initial date range is set (recommend 3-5 days for testing)

---

## 🎯 Summary

**To enable DeepSeek**:

1. ✅ Get API key from https://platform.deepseek.com/
2. ✅ Add to `.env`: `DEEPSEEK_API_KEY="your-key"`
3. ✅ Enable in config: `"enabled": true`
4. ✅ Set correct model: `"basemodel": "deepseek-chat"`
5. ✅ Run: `python3 main.py`

**DeepSeek is the current champion** with +10.61% returns. Good luck with your trading experiments! 🚀

---

**Last Updated**: October 28, 2025  
**Questions?** Check `RUNNING_GUIDE.md` or open an issue on GitHub.
