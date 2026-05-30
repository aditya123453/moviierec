# DEPLOYMENT GUIDE
## CINEMAGIC AI Hub - Production Deployment

This guide covers deploying CINEMAGIC to production environments.

---

## Table of Contents
1. [Streamlit Cloud](#streamlit-cloud-recommended)
2. [Docker & Docker Compose](#docker)
3. [Heroku](#heroku)
4. [AWS](#aws)
5. [Performance Optimization](#performance-optimization)
6. [Monitoring & Logging](#monitoring--logging)

---

## Streamlit Cloud (Recommended)
**Easiest deployment with automatic CI/CD**

### Steps
1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Ready for production"
   git push origin master
   ```

2. **Create Streamlit Cloud account**
   - Visit [share.streamlit.io](https://share.streamlit.io/)
   - Sign in with GitHub

3. **Deploy app**
   - Click "New app"
   - Select repository: `aditya123453/cinemagic-ai-hub`
   - Main file path: `app.py`
   - Click "Deploy"

4. **Set secrets**
   - Go to app settings (⚙️)
   - Click "Secrets"
   - Add:
     ```
     TMDB_API_KEY = "your_api_key_here"
     API_TIMEOUT = 5
     CACHE_TTL = 86400
     LOG_LEVEL = "INFO"
     ```

5. **Auto-deployment**
   - App automatically redeploys when you push to GitHub
   - View logs in "Manage app" → "Logs"

### Troubleshooting
```bash
# If models aren't found
# Upload movies_list.pkl, vectorizer.pkl to repo
git add *.pkl
git commit -m "Add model files"
git push
```

---

## Docker

### Build & Run Locally
```bash
# Build image
docker build -t cinemagic:latest .

# Run container
docker run -p 8501:8501 \
  -e TMDB_API_KEY="your_key" \
  cinemagic:latest

# Access at http://localhost:8501
```

### Docker Compose
```bash
# Start service
docker-compose up -d

# View logs
docker-compose logs -f cinemagic

# Stop service
docker-compose down
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  cinemagic:
    build: .
    ports:
      - "8501:8501"
    environment:
      TMDB_API_KEY: ${TMDB_API_KEY}
      API_TIMEOUT: 5
      LOG_LEVEL: INFO
    volumes:
      - ./:/app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## Heroku

### Deploy
```bash
# Install Heroku CLI
# Login
heroku login

# Create app
heroku create cinemagic-ai-hub

# Add buildpack
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set TMDB_API_KEY="your_key"
heroku config:set API_TIMEOUT=5

# Deploy
git push heroku master

# View logs
heroku logs --tail
```

**Procfile:**
```
web: streamlit run app.py --server.port=$PORT --server.address=0.0.0.0
```

**runtime.txt:**
```
python-3.10.12
```

---

## AWS

### Option 1: AWS App Runner (Easiest)
```bash
# Push Docker image to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag cinemagic:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/cinemagic:latest

# Push
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/cinemagic:latest

# Create App Runner service via AWS Console
# Source: ECR image
# Port: 8501
```

### Option 2: AWS EC2
```bash
# Connect to EC2 instance
ssh -i "key.pem" ec2-user@your-instance.aws.com

# Install dependencies
sudo apt-get update
sudo apt-get install python3.10 python3-pip git

# Clone repo
git clone https://github.com/aditya123453/cinemagic-ai-hub.git
cd cinemagic-ai-hub

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with Gunicorn (production)
pip install gunicorn
gunicorn --bind 0.0.0.0:8501 --workers 4 app:app
```

### Option 3: AWS Lambda + API Gateway
```python
# lambda_handler.py
import json
from app import generate_recommendations

def lambda_handler(event, context):
    movie = event['queryStringParameters']['movie']
    recs = generate_recommendations(movie)
    return {
        'statusCode': 200,
        'body': json.dumps(recs)
    }
```

---

## Performance Optimization

### Caching Strategy
```python
# config.py
CACHE_TTL = 86400  # 24 hours
API_TIMEOUT = 5    # 5 second timeout
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f locustfile.py --host=http://localhost:8501
```

### CDN Configuration
- Use CloudFlare for static assets
- Cache poster images for 24 hours
- Compress API responses (gzip)

### Database Indexing
```python
# If using database instead of pickle
CREATE INDEX idx_genre ON movies(genre);
CREATE INDEX idx_rating ON movies(vote_average);
```

---

## Monitoring & Logging

### Streamlit Cloud Logs
```bash
# View from terminal
# Set up GitHub integration for automated logs
```

### Application Logging
```python
import logging

# In config.py
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

# In utils.py
logger.error(f"API error: {e}")
logger.info("Movie fetched successfully")
```

### Monitoring Tools
- **Sentry** - Error tracking
  ```python
  import sentry_sdk
  sentry_sdk.init("https://your-token@sentry.io/123456")
  ```

- **DataDog** - Performance monitoring
- **New Relic** - Application monitoring

### Health Checks
```python
# /health endpoint
@router.get("/health")
def health():
    return {
        "status": "healthy",
        "models_loaded": engine.is_loaded(),
        "movies_count": len(engine.movies_df)
    }
```

---

## Environment-Specific Configuration

### Development
```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
CACHE_TTL=600
```

### Staging
```bash
ENVIRONMENT=staging
DEBUG=false
LOG_LEVEL=INFO
CACHE_TTL=3600
```

### Production
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING
CACHE_TTL=86400
API_TIMEOUT=5
ENABLE_MONITORING=true
```

---

## Security Best Practices

### API Key Protection
✅ Use `.env` files (never commit)
✅ Streamlit Cloud secrets
✅ Environment variables in production
✅ Rotate keys regularly

### Request Validation
✅ Input sanitization
✅ Rate limiting
✅ CORS configuration
✅ HTTPS only

### Data Privacy
✅ No user data stored locally
✅ GDPR compliant
✅ API key never logged
✅ HTTPS for all requests

### Dependency Security
```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip install -U -r requirements.txt
```

---

## Deployment Checklist

- [ ] All environment variables configured
- [ ] Model files uploaded (.pkl files)
- [ ] Requirements.txt updated
- [ ] Logging configured
- [ ] Error handling in place
- [ ] API timeout set
- [ ] Cache TTL appropriate
- [ ] GitHub workflow configured
- [ ] Domain/URL pointing to app
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Documentation updated

---

## Rollback Procedure

### Streamlit Cloud
```bash
# Revert to previous commit
git revert HEAD
git push origin master
# App auto-redeploys
```

### Docker
```bash
# Use previous image tag
docker run cinemagic:previous-tag
```

### Manual Rollback
```bash
# Kill current process
kill $(lsof -t -i :8501)

# Checkout previous version
git checkout HEAD~1
streamlit run app.py
```

---

## Cost Estimation

| Platform | Tier | Monthly Cost |
|----------|------|-------------|
| Streamlit Cloud | Free | $0 |
| Heroku | Hobby | $7 |
| AWS App Runner | Pay-as-you-go | $1-20 |
| Docker on VPS | Linode 2GB | $10 |

---

## Support & Troubleshooting

### Common Issues

**1. Models not found**
```bash
python recommender.py  # Regenerate models
```

**2. API timeouts**
- Increase `API_TIMEOUT` in config.py
- Check network connectivity
- Verify TMDB API key is valid

**3. Memory issues**
- Reduce `RECOMMENDATIONS_COUNT`
- Enable pickle compression
- Use database instead of pickle

**4. Slow performance**
- Enable caching
- Use CDN for images
- Optimize vector search

---

**For questions or issues, open a GitHub issue or contact: adityanandan450@gmail.com**
