from os import environ, path as ospath
from subprocess import run as srun, CalledProcessError
from logging import info as log_info, error as log_error
from importlib import import_module
from sys import exit

var_list = [
    "BOT_TOKEN",
    "API_ID",
    "API_HASH",
    "DATABASE_URL",
    "UPSTREAM_REPO",
    "UPSTREAM_BRANCH",
]

try:
    settings = import_module("config")
    config_file = {k: v.strip() if isinstance(v, str) else v
                   for k, v in vars(settings).items()
                   if not k.startswith("__")}
except ModuleNotFoundError:
    config_file = {}

config_file.update({k: v.strip() if isinstance(v, str) else v
                    for k, v in environ.items() if k in var_list})

BOT_TOKEN = config_file.get("BOT_TOKEN", "")
API_ID = config_file.get("API_ID")
API_HASH = config_file.get("API_HASH")

if not BOT_TOKEN or not API_ID or not API_HASH:
    log_error("BOT_TOKEN, API_ID, or API_HASH missing! Exiting...")
    exit(1)

UPSTREAM_REPO = config_file.get("UPSTREAM_REPO", "").strip()
UPSTREAM_BRANCH = config_file.get("UPSTREAM_BRANCH", "update").strip()

def update_repo():
    if not UPSTREAM_REPO:
        log_error("No UPSTREAM_REPO set! Skipping update.")
        return

    if not ospath.exists(".git"):
        srun(["git", "init", "-q"])
        srun(["git", "remote", "add", "origin", UPSTREAM_REPO])

    try:
        update = srun(f"git fetch origin -q && git reset --hard origin/{UPSTREAM_BRANCH} -q",
                      shell=True, capture_output=True, text=True)
        if update.returncode == 0:
            log_info(f"Repo updated successfully from {UPSTREAM_REPO} [{UPSTREAM_BRANCH}]!")
        else:
            log_error(f"Update failed: {update.stderr}")
    except CalledProcessError as e:
        log_error(f"Git update failed: {e.stderr}")

if __name__ == "__main__":
    update_repo()
