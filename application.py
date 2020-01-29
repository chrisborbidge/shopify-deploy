from flask import Flask, request, render_template, send_from_directory, url_for
from github import Github

import os
import time
import requests
import base64
import json

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

app.config["TESTING"] = False


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


def find(list, key, value):
    for i, dic in enumerate(list):
        if dic[key] == value:
            return i
    return None


def transfer_files_from_main_theme(
    shopify_shop, shopify_key, shopify_secret, staging_theme_id, data
):
    shopify_transfer_files = data["shopify_transfer_files"]
    for transfer_file in shopify_transfer_files:
        print("Transfer files from main theme to staging theme...")
        # GET main theme id
        session = requests_retry_session()
        user_pass_concat = f"{shopify_key}:{shopify_secret}"
        user_pass_concat_bytes = user_pass_concat.encode()
        user_pass_concat_base64 = base64.b64encode(user_pass_concat_bytes)
        user_pass_concat_base64_str = user_pass_concat_base64.decode("UTF-8")
        headers = {}
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Basic {user_pass_concat_base64_str}"
        url = f"https://{shopify_shop}.myshopify.com/admin/themes.json"
        response = session.get(url, headers=headers)
        response_json = response.json()
        themes = response_json["themes"]
        main_theme_index = find(themes, "role", "main")
        main_theme = themes[main_theme_index]
        main_theme_id = main_theme["id"]
        # GET asset from main theme
        session = requests_retry_session()
        user_pass_concat = f"{shopify_key}:{shopify_secret}"
        user_pass_concat_bytes = user_pass_concat.encode()
        user_pass_concat_base64 = base64.b64encode(user_pass_concat_bytes)
        user_pass_concat_base64_str = user_pass_concat_base64.decode("UTF-8")
        headers = {}
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Basic {user_pass_concat_base64_str}"
        url = f"https://{shopify_shop}.myshopify.com/admin/themes/{main_theme_id}/assets.json?asset[key]={transfer_file}&theme_id={staging_theme_id}"
        response = session.get(url, headers=headers)
        asset = response.json()["asset"]["value"]
        # POST asset to staging theme
        payload = {}
        payload["asset"] = {}
        payload["asset"]["key"] = transfer_file
        payload["asset"]["value"] = asset
        session = requests_retry_session()
        user_pass_concat = f"{shopify_key}:{shopify_secret}"
        user_pass_concat_bytes = user_pass_concat.encode()
        user_pass_concat_base64 = base64.b64encode(user_pass_concat_bytes)
        user_pass_concat_base64_str = user_pass_concat_base64.decode("UTF-8")
        headers = {}
        headers["Content-Type"] = "application/json"
        headers["Authorization"] = f"Basic {user_pass_concat_base64_str}"
        url = f"https://{shopify_shop}.myshopify.com/admin/themes/{staging_theme_id}/assets.json"
        response = session.put(url, headers=headers, json=payload)
        response_json = response.json()
        print("Done!")
    return response_json


def post_theme_to_shopify_and_stage(
    shopify_shop, shopify_key, shopify_secret, theme_title, theme_src, data
):
    print("Post theme to Shopify and stage...")
    payload = {}
    payload["theme"] = {}
    payload["theme"]["name"] = theme_title + " - Staging"
    testing = app.config["TESTING"]
    if not testing:
        theme_src = url_for(
            "download_file_from_tmp_dir", filename="theme.zip", _external=True
        )
    else:
        # TO DO: Host this file somewhere more suitable...
        theme_src = "https://cdn.shopify.com/s/files/1/0135/9550/8793/files/elkthelabel-elk-the-label-shopify-theme-v0.6.2-0-g320385b68942647faea333a947f025654e27d5f1.zip?16521"
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


def deploy_shopify_theme(json_data):
    data = json_data
    github_token = data["github"]["github_token"]
    github_repo_url = data["github"]["github_repo_url"]
    shopify_instances = data["shopify_instances"]
    theme_title, theme_src = get_theme_from_github(github_token, github_repo_url)
    for shopify_instance in shopify_instances:
        shopify_shop = shopify_instance["shopify_shop"]
        shopify_key = shopify_instance["shopify_key"]
        shopify_secret = shopify_instance["shopify_secret"]
        response_json = post_theme_to_shopify_and_stage(
            shopify_shop, shopify_key, shopify_secret, theme_title, theme_src, data
        )
        staging_theme_id = response_json["theme"]["id"]
        time.sleep(90)
        transfer_files_from_main_theme(
            shopify_shop, shopify_key, shopify_secret, staging_theme_id, data
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


@app.route("/deploy", methods=["POST"])
def deploy():
    json_data = request.get_json()
    if not json_data:
        return (
            {"status": "fail", "message": "No input data provided", "data": None},
            400,
        )
    response_json = deploy_shopify_theme(json_data)
    return {"status": "success", "message": "Deployed theme successfully", "data": None}


@app.route("/")
def index():
    return render_template("index.html")
