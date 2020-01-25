# shopify-deploy

[![Build Status](https://travis-ci.com/chrisborbidge/shopify-deploy.svg?branch=master)](https://travis-ci.com/chrisborbidge/shopify-deploy)

Note: Don't use this, it's early days!

An app that simplifies Shopify Theme deployment.

### Quick start

#### Development
```
python -m venv .venv
pip install -r "requirements.txt"
python3 application.py
```

#### Production
```
pip install -r "requirements.txt"
gunicorn application:app -w 1 --threads 2
```
