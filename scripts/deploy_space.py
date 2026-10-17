"""Deploy the student app to a Hugging Face Space.

Static (default, free): the page and the Python files it runs in the browser.
    space/static/README.md, app/static/* at the root, and py/<file> for each of
    app.checking.BROWSER_FILES. No server, so no model explanation.
Docker (--docker, needs HF PRO for hosting): the FastAPI server, which adds the
    model's explanation. space/docker/* at the root, app/ and the core files it imports.

    python scripts/deploy_space.py --repo USER/firstslip          # needs a write token (hf auth login)
    python scripts/deploy_space.py --repo USER/firstslip --docker
"""
import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from app.checking import BROWSER_FILES  # noqa: E402

# Previously deployed files that are removed if no longer uploaded (keeps .gitattributes).
OLD_FILES = ["*.html", "*.js", "*.css", "*.txt", "Dockerfile", "results/**", "py/**", "app/**", "core/**"]
DOCKER_CORE = ["core/__init__.py", "core/checker.py", "core/prompts.py"]


def _copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def bundle_static(dest: Path) -> None:
    _copy(ROOT / "space/static/README.md", dest / "README.md")
    shutil.copytree(ROOT / "app/static", dest, dirs_exist_ok=True)
    for f in BROWSER_FILES:
        _copy(ROOT / f, dest / "py" / f)


def bundle_docker(dest: Path) -> None:
    for f in (ROOT / "space/docker").iterdir():
        _copy(f, dest / f.name)
    shutil.copytree(ROOT / "app", dest / "app", ignore=shutil.ignore_patterns("__pycache__"))
    for f in DOCKER_CORE:
        _copy(ROOT / f, dest / f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="Space id, e.g. USER/firstslip")
    ap.add_argument("--docker", action="store_true", help="deploy the FastAPI server instead of the static page")
    args = ap.parse_args()
    api = HfApi()
    if api.whoami().get("auth", {}).get("accessToken", {}).get("role") == "read":
        sys.exit("The stored Hugging Face token is read-only. Log in with a write token: hf auth login")
    sdk = "docker" if args.docker else "static"
    url = api.create_repo(args.repo, repo_type="space", space_sdk=sdk, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        (bundle_docker if args.docker else bundle_static)(Path(tmp))
        api.upload_folder(folder_path=tmp, repo_id=args.repo, repo_type="space",
                          commit_message=f"Deploy FirstSlip student app ({sdk})", delete_patterns=OLD_FILES)
    print(url)


if __name__ == "__main__":
    main()
