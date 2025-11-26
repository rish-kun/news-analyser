# Quick Start: Generate Screenshots

This guide will help you quickly generate screenshots of the News Analyser application.

## Option 1: Automated Script (Easiest)

```bash
# 1. Make sure you're in the project directory
cd /path/to/news-analyser

# 2. Run the screenshot generator
./generate_screenshots.sh

# 3. Screenshots will be saved to screenshots/ directory
ls screenshots/
```

**What it does**:
- Creates a virtual environment
- Installs all dependencies including Playwright
- Sets up a test database with sample data
- Starts Django server
- Captures screenshots automatically
- Saves 7 screenshots to `screenshots/` directory

## Option 2: Docker-Based (Most Reliable)

```bash
# 1. Make sure .env file exists
cp .env.example .env
# Add your GEMINI_API_KEY (or use dummy-key for screenshots)

# 2. Run screenshot generation
docker-compose -f docker-compose.screenshots.yml up

# 3. Check screenshots
ls screenshots/
```

## Option 3: Manual Python Script

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. Start Django server in one terminal
python manage.py runserver

# 3. In another terminal, run the capture script
python capture_screenshots.py
```

## Verify Screenshots

After running any of the above methods:

```bash
# List generated screenshots
ls -lh screenshots/

# Should show:
# 01-login.png
# 02-search-page.png
# 03-search-results.png
# 04-news-detail.png
# 05-past-searches.png
# 06-watchlist.png
# 07-admin.png (if admin user exists)
```

## Add Screenshots to PR

```bash
# 1. Verify screenshots look good
open screenshots/01-login.png  # macOS
xdg-open screenshots/01-login.png  # Linux

# 2. Commit them
git add screenshots/*.png
git commit -m "docs: Add application screenshots"

# 3. Push to GitHub
git push

# 4. Update PR description with screenshots
# Go to GitHub PR and drag-drop images or reference them
```

## Troubleshooting

### Script Permission Denied
```bash
chmod +x generate_screenshots.sh
```

### Playwright Not Found
```bash
pip install playwright
playwright install chromium
```

### Django Server Won't Start
```bash
# Check if port 8000 is in use
lsof -i :8000
# Kill the process if needed
kill -9 <PID>
```

### Screenshots Are Blank
- Wait a few seconds after page load
- Check Django server logs
- Try increasing sleep time in capture_screenshots.py

### No .env File
```bash
cp .env.example .env
# Edit and add GEMINI_API_KEY (can be dummy for screenshots)
```

## Next Steps

1. **Review screenshots**: Open each file to verify quality
2. **Retake if needed**: Delete and run script again
3. **Optimize size**: Use tools like ImageOptim or TinyPNG if files are large
4. **Add to PR**: Commit and push to GitHub
5. **Update PR description**: Add screenshots with markdown:

```markdown
## Screenshots

### Login Page
![Login](screenshots/01-login.png)

### Search Interface
![Search](screenshots/02-search-page.png)

### Search Results
![Results](screenshots/03-search-results.png)
```

## Time Estimate

- **Automated script**: 2-3 minutes
- **Docker method**: 3-5 minutes (first time, includes image build)
- **Manual method**: 5-10 minutes

---

**Ready to generate? Run**: `./generate_screenshots.sh`
