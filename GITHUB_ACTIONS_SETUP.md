# GitHub Actions Setup Guide - IB Gateway Historical Data Automation

This guide explains how to set up automated daily downloads of historical market data from Interactive Brokers using GitHub Actions.

## Overview

The GitHub Actions workflow automatically:
- Runs **Monday-Friday at 2 PM UTC** (9 AM EST / after previous day's market close)
- Downloads **previous trading day's 1-minute bar data** for AAPL
- Compresses the data using your existing `tools/compress.py`
- Commits and pushes the data to your repository

## Architecture

The workflow uses:
- **Ubuntu runner** (GitHub-hosted, free)
- **Docker IB Gateway container** with Xvfb (headless display)
- **IBC (Interactive Brokers Controller)** for automation
- **Python ib_async library** to fetch historical data

## Setup Instructions

### Step 1: Configure GitHub Secrets

Your IB Gateway credentials need to be stored securely in GitHub Secrets.

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add the following secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `IB_USERNAME` | `otremo926` | Your IB Gateway username |
| `IB_PASSWORD` | `yJuF3HUGzHQNCbS` | Your IB Gateway password |

**Security Note**: Once added, these secrets are encrypted and cannot be viewed again. Only GitHub Actions workflows can access them.

### Step 2: Push the Workflow Files

The following files have been created and need to be committed to your repository:

```
.github/workflows/download-ib-data.yml  # GitHub Actions workflow
scripts/download_historical_data.py     # Python download script
requirements.txt                         # Python dependencies
```

Commit and push these files:

```bash
git add .github/workflows/download-ib-data.yml
git add scripts/download_historical_data.py
git add requirements.txt
git add .gitignore
git commit -m "Add GitHub Actions workflow for IB Gateway historical data"
git push
```

### Step 3: Enable GitHub Actions

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Actions** → **General**
3. Under "Workflow permissions", ensure **Read and write permissions** is selected
4. Click **Save**

This allows the workflow to commit and push downloaded data back to your repository.

### Step 4: Test the Workflow

#### Manual Test Run

1. Go to **Actions** tab in your repository
2. Click on **Download IB Historical Data** workflow
3. Click **Run workflow** → **Run workflow** (green button)
4. Wait 2-3 minutes for completion
5. Check the workflow logs for:
   - ✓ IB Gateway container startup
   - ✓ Connection to IB Gateway
   - ✓ Data download for AAPL
   - ✓ Compression
   - ✓ Git commit/push

#### View Results

After successful execution, check:
- `sessions/AAPL-YYYYMMDD.csv` - Raw CSV data
- `sessions/AAPL-YYYYMMDD.bin.gz` - Compressed binary (if compression succeeded)
- Recent commit in repository history

### Step 5: Monitor Scheduled Runs

The workflow runs automatically Monday-Friday at 2 PM UTC. You can:

1. Go to **Actions** tab to see workflow history
2. Click on any run to view logs
3. Enable notifications: **Settings** → **Notifications** → **GitHub Actions**

## Customization

### Change Download Schedule

Edit `.github/workflows/download-ib-data.yml`:

```yaml
on:
  schedule:
    - cron: '0 14 * * 1-5'  # Change this line
    # Examples:
    # '0 21 * * 1-5'  # 9 PM UTC = 4 PM EST (after market close)
    # '30 14 * * *'   # 2:30 PM UTC daily
```

Cron format: `minute hour day month weekday`

### Add More Symbols

Edit `scripts/download_historical_data.py`:

```python
# Line 16
SYMBOLS = ['AAPL', 'MSFT', 'GOOGL', 'TSLA']  # Add symbols here
```

### Change Data Duration

Edit `scripts/download_historical_data.py`:

```python
# Line 78
durationStr='1 D',  # Change to '5 D', '1 W', '1 M', etc.
```

### Change Bar Size

Edit `scripts/download_historical_data.py`:

```python
# Line 79
barSizeSetting='1 min',  # Change to '5 mins', '15 mins', '1 hour', etc.
```

## Troubleshooting

### Workflow Fails: "Connection timeout"

**Cause**: IB Gateway container didn't start in time

**Solution**: Increase wait time in workflow:
```yaml
- name: Wait for IB Gateway to start
  run: sleep 120  # Change from 90 to 120 seconds
```

### Workflow Fails: "Authentication failed"

**Cause**: Incorrect credentials in GitHub Secrets

**Solution**:
1. Verify username/password are correct
2. Re-add secrets in GitHub repository settings
3. Ensure there are no extra spaces in secret values

### No Data Downloaded

**Cause**: Market was closed (holiday, weekend)

**Solution**: This is expected. The workflow will succeed but report "No data received". It will download data on the next trading day.

### Paper Trading Popup Issue

**Cause**: IB Gateway shows paper trading warning

**Solution**: The Docker container automatically handles this with IBC configuration. If it persists, the container image may need updating.

### Compression Fails

**Cause**: `tools/compress.py` may have dependencies or format issues

**Solution**: Check compress.py script. The workflow has `continue-on-error: true` so CSV files are still committed even if compression fails.

## Local Testing

You can test the download script locally:

### Option 1: Using Docker (Recommended)

```bash
# Start IB Gateway container
docker run -d --name ib-gateway \
  -e TWS_USERID=otremo926 \
  -e TWS_PASSWORD=yJuF3HUGzHQNCbS \
  -e TRADING_MODE=paper \
  -p 4002:4002 \
  ghcr.io/gnzsnz/ib-gateway:latest

# Wait for startup
sleep 90

# Run download script
pip install -r requirements.txt
python scripts/download_historical_data.py

# Cleanup
docker stop ib-gateway
docker rm ib-gateway
```

### Option 2: Using Local IB Gateway

```bash
# Set environment variables
set IB_USERNAME=otremo926
set IB_PASSWORD=yJuF3HUGzHQNCbS

# Launch IB Gateway (updated batch file now uses env vars)
launch_ibgateway.bat

# In another terminal, run download script
set IB_HOST=localhost
set IB_PORT=4002
python scripts/download_historical_data.py
```

## Security Best Practices

✅ **DO**:
- Store credentials in GitHub Secrets only
- Use environment variables for local testing
- Keep `.gitignore` updated to exclude credential files

❌ **DON'T**:
- Commit credentials to the repository
- Share your IB Gateway password
- Use live trading credentials in automation (use paper trading)

## Cost Analysis

- **GitHub Actions**: Free (2,000 minutes/month on free plan)
- **Docker container**: Free (public image)
- **IB Account**: Paper trading is free
- **Data storage**: Minimal (few MB per day)

**Estimated monthly cost**: $0

## Files Reference

| File | Purpose |
|------|---------|
| `.github/workflows/download-ib-data.yml` | GitHub Actions workflow definition |
| `scripts/download_historical_data.py` | Python script to download data from IB |
| `requirements.txt` | Python dependencies |
| `launch_ibgateway.bat` | Local IB Gateway launcher (now secure) |
| `.gitignore` | Excludes sensitive files from git |

## Support

- **IB Gateway Docker**: https://github.com/gnzsnz/ib-gateway-docker
- **ib_async Library**: https://github.com/ib-api-reloaded/ib_async
- **IB API Docs**: https://interactivebrokers.github.io/tws-api/
- **GitHub Actions Docs**: https://docs.github.com/en/actions

## Next Steps

1. ✅ Configure GitHub Secrets (IB_USERNAME, IB_PASSWORD)
2. ✅ Commit and push workflow files
3. ✅ Enable GitHub Actions write permissions
4. ✅ Run manual test workflow
5. ✅ Monitor first scheduled run
6. 🔄 Customize symbols/schedule as needed

---

**Last Updated**: 2025-11-15
**Created By**: GitHub Actions automation setup
