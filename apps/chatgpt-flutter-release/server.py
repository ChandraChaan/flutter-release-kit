#!/usr/bin/env python3
"""Flutter Release Check - a remote MCP server for ChatGPT.
Author: Chandra ObulaReddy (ChandraChaan)

Exposes the Flutter Release Kit rules as read-only tools. A remote server cannot
see the user's project, so tools take pasted file contents. Each request is
handled in a temporary directory that is deleted afterwards; nothing is stored
or logged.

Run: uvicorn server:app --host 0.0.0.0 --port 8000   (endpoint: /mcp)
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal, Optional

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import permission_audit  # noqa: E402  (the shared rule tables)

HOST = os.environ.get("HOST", "127.0.0.1")
MAX_FILE_CHARS = 512_000
SCRIPT_TIMEOUT_SECONDS = 20
VERIFY_NOTE = "Store policies change. Confirm against Play Console and App Store Connect before submitting."

READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)

mcp = MCPServer(
    name="flutter-release-check",
    title="Flutter Release Check",
    version="0.1.0",
    instructions=(
        "Checks Flutter apps against Google Play and App Store rules. Ask the user to paste file contents when a "
        "tool needs them, and remind them never to paste signing keys, passwords or API keys."
    ),
)


class PermissionAudit(BaseModel):
    app: str
    issue_count: int
    issues: list[str]
    restricted_permissions: list[str]
    android: dict[str, Any]
    ios: dict[str, Any]
    not_checked: list[str]
    verify: str = VERIFY_NOTE


class PermissionInfo(BaseModel):
    permission: str
    known: bool
    tier: str
    policy_note: str
    draft_declaration: Optional[str]
    verify: str = VERIFY_NOTE


class FieldCheck(BaseModel):
    field: str
    length: int
    limit: int
    remaining: int
    within_limit: bool


class ListingCheck(BaseModel):
    passes: bool
    fields: list[FieldCheck]
    problems: list[str]
    warnings: list[str]
    verify: str = VERIFY_NOTE


class VersionPlan(BaseModel):
    current_version: str
    new_version: str
    pubspec_line: str
    git_tag: str
    warnings: list[str]


def require_size(label: str, text: Optional[str]) -> None:
    if text is not None and len(text) > MAX_FILE_CHARS:
        raise ToolError(f"{label} is too large. Paste only that one file.")


def run_script(name: str, *args: str) -> subprocess.CompletedProcess:
    # -I keeps the interpreter from importing anything out of the working directory.
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPTS / name), *args],
        capture_output=True, text=True, timeout=SCRIPT_TIMEOUT_SECONDS, env={"PATH": os.environ.get("PATH", "")},
    )


def strip_paths(section: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in section.items() if key != "path"}


@mcp.tool(
    name="audit_flutter_permissions",
    title="Audit Flutter permissions",
    description=(
        "Use when the user wants a Flutter app's permissions reviewed for Google Play or App Store rejection risk. "
        "Takes the pasted text of AndroidManifest.xml, Info.plist and/or pubspec.yaml; at least one manifest or plist "
        "is required. Returns each permission's risk tier, specific issues and draft Play Console declarations."
    ),
    annotations=READ_ONLY,
)
def audit_flutter_permissions(
    android_manifest: Annotated[Optional[str], Field(description="Full text of android/app/src/main/AndroidManifest.xml")] = None,
    info_plist: Annotated[Optional[str], Field(description="Full XML text of ios/Runner/Info.plist")] = None,
    pubspec: Annotated[Optional[str], Field(description="Full text of pubspec.yaml; lets the audit find missing iOS keys")] = None,
    has_privacy_manifest: Annotated[Optional[bool], Field(description="Whether ios/Runner/PrivacyInfo.xcprivacy exists, if known")] = None,
) -> PermissionAudit:
    if not android_manifest and not info_plist:
        raise ToolError("Paste AndroidManifest.xml or Info.plist so there is something to audit.")
    require_size("AndroidManifest.xml", android_manifest)
    require_size("Info.plist", info_plist)
    require_size("pubspec.yaml", pubspec)
    for text in (android_manifest, info_plist):
        if text and "<!ENTITY" in text:
            raise ToolError("XML entity declarations are not accepted.")

    not_checked = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        if android_manifest:
            path = root / "android/app/src/main/AndroidManifest.xml"
            path.parent.mkdir(parents=True)
            path.write_text(android_manifest, encoding="utf-8")
        else:
            not_checked.append("Android: no AndroidManifest.xml provided.")
        if info_plist:
            path = root / "ios/Runner/Info.plist"
            path.parent.mkdir(parents=True)
            path.write_text(info_plist, encoding="utf-8")
            # When unknown, avoid reporting a missing privacy manifest that may well exist.
            if has_privacy_manifest is not False:
                (root / "ios/Runner/PrivacyInfo.xcprivacy").touch()
            if has_privacy_manifest is None:
                not_checked.append("iOS privacy manifest: unknown. Check that ios/Runner/PrivacyInfo.xcprivacy exists.")
            if not pubspec:
                not_checked.append("iOS plugin requirements: no pubspec.yaml provided, so missing usage keys cannot be detected.")
        else:
            not_checked.append("iOS: no Info.plist provided.")
        if pubspec:
            (root / "pubspec.yaml").write_text(pubspec, encoding="utf-8")

        try:
            result = run_script("permission_audit.py", str(root), "--json")
        except subprocess.TimeoutExpired:
            raise ToolError("The audit took too long. Check that the pasted files are correct.") from None
    if result.returncode != 0:
        # stderr can quote the pasted file, so it is deliberately not echoed or logged.
        raise ToolError("Could not read those files. Paste the complete XML of each file, unmodified.")

    report = json.loads(result.stdout)
    rows = report["android"].get("permissions", [])
    return PermissionAudit(
        app=report["app"],
        issue_count=len(report["issues"]),
        issues=report["issues"],
        restricted_permissions=[row["name"] for row in rows if row["tier"] == "restricted"],
        android=strip_paths(report["android"]),
        ios=strip_paths(report["ios"]),
        not_checked=not_checked,
    )


@mcp.tool(
    name="look_up_android_permission",
    title="Look up an Android permission",
    description=(
        "Use when the user asks whether Google Play allows a specific Android permission, such as READ_SMS or "
        "ACCESS_BACKGROUND_LOCATION. Needs no files. Returns its risk tier, the policy that applies and a draft declaration."
    ),
    annotations=READ_ONLY,
)
def look_up_android_permission(
    permission: Annotated[str, Field(description="Permission name, for example READ_SMS or android.permission.CAMERA")],
) -> PermissionInfo:
    name = permission.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.]{1,200}", name):
        raise ToolError("That does not look like an Android permission name.")
    if "." not in name:
        name = "android.permission." + name.upper()
    templates = permission_audit.JUSTIFICATION_TEMPLATES
    if name.startswith("android.permission.FOREGROUND_SERVICE_"):
        return PermissionInfo(
            permission=name, known=True, tier="restricted",
            policy_note="Foreground service type permission: Play Console needs a declaration and demo video for this type.",
            draft_declaration=templates["android.permission.FOREGROUND_SERVICE"],
        )
    if name in permission_audit.ANDROID_PERMS:
        tier, note = permission_audit.ANDROID_PERMS[name]
        known = True
    elif permission_audit.SERVICE_BOUND_PERMS.get(name):
        tier, note, known = "restricted", permission_audit.SERVICE_BOUND_PERMS[name], True
    else:
        tier, note, known = "unknown", "Not in the built-in list. Check Google Play's policy for this permission.", False
    return PermissionInfo(permission=name, known=known, tier=tier, policy_note=note, draft_declaration=templates.get(name))


FLAGGED_WORDS_RE = re.compile(
    r"(?<![\w#])(free|best|top|#1|new|sale|download|android|iphone|play|app store|official)(?![\w])", re.I
)


def has_emoji(text: str) -> bool:
    return any(ord(c) >= 0x1F000 or 0x2600 <= ord(c) <= 0x27BF for c in text)


def measure(fields: dict[str, tuple[Optional[str], int]]) -> tuple[list[FieldCheck], list[str]]:
    rows, problems = [], []
    for field, (value, limit) in fields.items():
        if value is None:
            continue
        require_size(field, value)
        remaining = limit - len(value)
        rows.append(FieldCheck(field=field, length=len(value), limit=limit, remaining=remaining, within_limit=remaining >= 0))
        if remaining < 0:
            problems.append(f"{field} is {-remaining} character(s) over the {limit} limit.")
    if not rows:
        raise ToolError("Provide at least one listing field to check.")
    return rows, problems


def check_flagged_words(label: str, value: Optional[str], warnings: list[str]) -> None:
    if value:
        found = sorted({m.group(1).lower() for m in FLAGGED_WORDS_RE.finditer(value)})
        if found:
            warnings.append(f"{label} contains words stores often flag: {', '.join(found)}.")


def words(text: Optional[str]) -> set[str]:
    return set(re.findall(r"[^\W_]+", (text or "").lower()))


@mcp.tool(
    name="check_google_play_listing",
    title="Check a Google Play listing",
    description=(
        "Use when the user wants Google Play listing text checked before submitting. Checks character limits and "
        "wording that Play commonly flags. Pass only the fields the user has written."
    ),
    annotations=READ_ONLY,
)
def check_google_play_listing(
    title: Annotated[Optional[str], Field(description="App name")] = None,
    short_description: Annotated[Optional[str], Field(description="Short description")] = None,
    full_description: Annotated[Optional[str], Field(description="Full description")] = None,
    release_notes: Annotated[Optional[str], Field(description="Release notes for one language")] = None,
) -> ListingCheck:
    rows, problems = measure({
        "title": (title, 30), "short_description": (short_description, 80),
        "full_description": (full_description, 4000), "release_notes": (release_notes, 500),
    })
    warnings: list[str] = []
    check_flagged_words("title", title, warnings)
    check_flagged_words("short_description", short_description, warnings)
    if title and has_emoji(title):
        problems.append("title must not contain emojis.")
    if title and title.isupper() and len(title) > 4:
        problems.append("title must use normal capitalisation, not all capitals.")
    return ListingCheck(passes=not problems, fields=rows, problems=problems, warnings=warnings)


@mcp.tool(
    name="check_app_store_listing",
    title="Check an App Store listing",
    description=(
        "Use when the user wants App Store Connect listing text checked before submitting. Checks character limits, "
        "keyword field formatting and wasted keywords. Pass only the fields the user has written."
    ),
    annotations=READ_ONLY,
)
def check_app_store_listing(
    name: Annotated[Optional[str], Field(description="App name")] = None,
    subtitle: Annotated[Optional[str], Field(description="Subtitle")] = None,
    promotional_text: Annotated[Optional[str], Field(description="Promotional text")] = None,
    description: Annotated[Optional[str], Field(description="Description")] = None,
    keywords: Annotated[Optional[str], Field(description="Comma-separated keyword field")] = None,
    whats_new: Annotated[Optional[str], Field(description="What's New text")] = None,
) -> ListingCheck:
    rows, problems = measure({
        "name": (name, 30), "subtitle": (subtitle, 30), "promotional_text": (promotional_text, 170),
        "description": (description, 4000), "keywords": (keywords, 100), "whats_new": (whats_new, 4000),
    })
    warnings: list[str] = []
    check_flagged_words("name", name, warnings)
    check_flagged_words("subtitle", subtitle, warnings)
    repeated_title_words = sorted(words(name) & words(subtitle))
    if repeated_title_words:
        warnings.append(f"name and subtitle repeat: {', '.join(repeated_title_words)}. Each slot is indexed separately.")
    if keywords:
        if " " in keywords:
            problems.append("keywords must not contain spaces; they use up the 100 characters.")
        terms = [t.strip().lower() for t in keywords.split(",") if t.strip()]
        duplicates = sorted({t for t in terms if terms.count(t) > 1})
        if duplicates:
            problems.append(f"keywords has duplicates: {', '.join(duplicates)}.")
        already_indexed = sorted(words(keywords) & (words(name) | words(subtitle)))
        if already_indexed:
            warnings.append(f"keywords repeat words already in the name or subtitle: {', '.join(already_indexed)}.")
    return ListingCheck(passes=not problems, fields=rows, problems=problems, warnings=warnings)


@mcp.tool(
    name="plan_version_bump",
    title="Plan a Flutter version bump",
    description=(
        "Use when the user asks what their next Flutter version or build number should be. Calculates the new "
        "pubspec.yaml version line, always raising the build number. It does not change any file."
    ),
    annotations=READ_ONLY,
)
def plan_version_bump(
    current_version: Annotated[str, Field(description="Current pubspec version, for example 1.4.2+37")],
    part: Annotated[Literal["major", "minor", "patch", "build", "exact"], Field(description="Which part to bump")],
    exact_version: Annotated[Optional[str], Field(description="Target X.Y.Z or X.Y.Z+N; required when part is exact")] = None,
) -> VersionPlan:
    current_version = current_version.strip()
    pattern = r"\d{1,9}\.\d{1,9}\.\d{1,9}(\+\d{1,12})?"
    if not re.fullmatch(pattern, current_version):
        raise ToolError("current_version must look like 1.4.2+37.")
    if part == "exact" and not (exact_version and re.fullmatch(pattern, exact_version.strip())):
        raise ToolError("exact_version must look like 2.0.0 or 2.0.0+40 when part is exact.")

    with tempfile.TemporaryDirectory() as tmp:
        pubspec = Path(tmp) / "pubspec.yaml"
        pubspec.write_text(f"version: {current_version}\n", encoding="utf-8")
        args = [part] + ([exact_version.strip()] if part == "exact" else [])
        result = run_script("bump_version.py", *args, "--pubspec", str(pubspec), "--no-changelog", "--dry-run")
    if result.returncode != 0:
        raise ToolError(result.stderr.strip().removeprefix("error: ") or "Could not calculate that version.")

    match = re.search(r"-> (\d+\.\d+\.\d+)\+(\d+)", result.stdout)
    if not match:
        raise ToolError("Could not calculate that version.")
    semver, build = match.group(1), int(match.group(2))
    new_version = f"{semver}+{build}"
    warnings = []
    old_build = int(current_version.split("+")[1]) if "+" in current_version else None
    if old_build is not None and build <= old_build:
        warnings.append(f"Build {build} is not higher than the current {old_build}. The stores will reject this upload.")
    return VersionPlan(
        current_version=current_version, new_version=new_version,
        pubspec_line=f"version: {new_version}", git_tag=f"v{semver}", warnings=warnings,
    )


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def health(_: Request) -> Response:
    return PlainTextResponse("ok")


@mcp.custom_route("/.well-known/openai-apps-challenge", methods=["GET"], include_in_schema=False)
async def domain_challenge(_: Request) -> Response:
    token = os.environ.get("OPENAI_APPS_CHALLENGE")
    return PlainTextResponse(token) if token else PlainTextResponse("not configured", status_code=404)


app = mcp.streamable_http_app(json_response=True, stateless_http=True, host=HOST)
