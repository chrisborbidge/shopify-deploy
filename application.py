from flask import Flask, render_template, send_from_directory, url_for
from github import Github

import os
import requests
import base64
import json
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SHOPIFY_KEY = os.getenv("SHOPIFY_KEY")
SHOPIFY_SECRET = os.getenv("SHOPIFY_SECRET")

app = Flask(__name__)

data = {
    "github": {
        "github_repo_url": "elkthelabel/elk-the-label-shopify-theme",
        "github_token": GITHUB_TOKEN,
    },
    "shopify_instances": [
        {
            "shopify_instance": 0,
            "shopify_shop": "elkthelabel-dev",
            "shopify_key": SHOPIFY_KEY,
            "shopify_secret": SHOPIFY_SECRET,
        }
    ],
    "shopify_transfer_files": {"settings.liquid"},
}


def requests_retry_session(
    retries=10, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        method_whitelist=frozenset(["GET", "POST"]),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def post_theme_to_shopify_and_stage(
    shopify_shop, shopify_key, shopify_secret, theme_title, theme_src
):
    print("Post theme to Shopify and stage...")
    payload = {}
    payload["theme"] = {}
    payload["theme"]["name"] = theme_title + " - Staging"
    theme_src = url_for(
        "download_file_from_tmp_dir", filename="theme.zip", _external=True
    )
    print(theme_src)
    payload["theme"]["src"] = theme_src
    payload = json.dumps(payload)
    session = requests_retry_session()
    user_pass_concat = f"{shopify_key}:{shopify_secret}"
    user_pass_concat_bytes = user_pass_concat.encode()
    user_pass_concat_base64 = base64.b64encode(user_pass_concat_bytes)
    user_pass_concat_base64_str = user_pass_concat_base64.decode("UTF-8")
    headers = {}
    headers["Content-Type"] = "application/json"
    headers["Authorization"] = f"Basic {user_pass_concat_base64_str}"
    url = f"https://{shopify_shop}.myshopify.com/admin/themes.json"
    response = session.post(url, headers=headers, data=payload)
    response_json = response.json()
    cwd = os.path.dirname(__file__)
    tmp = os.path.join(cwd, "tmp", "theme.zip")
    os.remove(tmp)
    print("Done!")
    return response_json


def get_theme_from_github(github_token, github_repo_url):
    print("Getting theme from GitHub...")
    g = Github(github_token)
    repo = g.get_repo(github_repo_url)
    latest = repo.get_latest_release()
    theme_title = latest.title
    theme_src = latest.zipball_url + "?access_token=" + github_token
    r = requests.get(theme_src)
    cwd = os.path.dirname(__file__)
    tmp = os.path.join(cwd, "tmp", "theme.zip")
    with open(tmp, "w+b") as f:
        f.write(r.content)
    print("Done!")
    return theme_title, theme_src


def deploy_shopify_theme():
    github_token = data["github"]["github_token"]
    github_repo_url = data["github"]["github_repo_url"]
    shopify_instances = data["shopify_instances"]
    theme_title, theme_src = get_theme_from_github(github_token, github_repo_url)
    for shopify_instance in shopify_instances:
        shopify_shop = shopify_instance["shopify_shop"]
        shopify_key = shopify_instance["shopify_key"]
        shopify_secret = shopify_instance["shopify_secret"]
        response_json = post_theme_to_shopify_and_stage(
            shopify_shop, shopify_key, shopify_secret, theme_title, theme_src
        )
    return response_json


@app.route("/tmp/<path:filename>")
def download_file_from_tmp_dir(filename):
    cwd = os.path.dirname(__file__)
    tmp = os.path.join(cwd, "tmp")
    return send_from_directory(tmp, filename, as_attachment=True)


@app.route("/health")
def health():
    return "Healthy!"


@app.route("/deploy")
def deploy():
    response_json = deploy_shopify_theme()
    return response_json


@app.route("/")
def index():
    return render_template("index.html")
