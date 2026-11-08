"""End-to-end tests: start the real server and speak MCP JSON-RPC over HTTP, as ChatGPT does."""
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]

MANIFEST = """<manifest xmlns:android="http://schemas.android.com/apk/res/android">
  <uses-permission android:name="android.permission.READ_SMS"/>
  <uses-permission android:name="android.permission.INTERNET"/>
  <application android:label="Demo"/>
</manifest>"""

PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleName</key><string>Demo</string></dict></plist>"""

PUBSPEC = "name: demo\ndependencies:\n  camera: ^0.11.0\n"


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            cls.port = sock.getsockname()[1]
        cls.server = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning"],
            cwd=APP_DIR, env={**os.environ, "OPENAI_APPS_CHALLENGE": "token-123"},
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        for _ in range(100):
            try:
                urllib.request.urlopen(cls.base + "/health", timeout=1).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            cls.server.kill()
            raise RuntimeError("server did not start")
        cls.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}})

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.wait(timeout=10)

    @classmethod
    def rpc(cls, method, params):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        request = urllib.request.Request(cls.base + "/mcp", data=body, method="POST", headers={
            "Content-Type": "application/json", "Accept": "application/json, text/event-stream",
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def call(self, tool, **arguments):
        return self.rpc("tools/call", {"name": tool, "arguments": arguments})["result"]

    def structured(self, tool, **arguments):
        result = self.call(tool, **arguments)
        self.assertFalse(result.get("isError"), result)
        return result["structuredContent"]

    def test_every_tool_declares_what_directory_review_needs(self):
        tools = self.rpc("tools/list", {})["result"]["tools"]
        self.assertEqual(len(tools), 5)
        for tool in tools:
            with self.subTest(tool["name"]):
                self.assertIs(tool["annotations"]["readOnlyHint"], True)
                self.assertIs(tool["annotations"]["destructiveHint"], False)
                self.assertIs(tool["annotations"]["openWorldHint"], False)
                self.assertTrue(tool["title"])
                self.assertIn("Use when", tool["description"])
                self.assertIn("properties", tool["outputSchema"])

    def test_audit_flags_sms_and_missing_ios_keys(self):
        report = self.structured("audit_flutter_permissions", android_manifest=MANIFEST, info_plist=PLIST, pubspec=PUBSPEC, has_privacy_manifest=False)
        self.assertEqual(report["restricted_permissions"], ["android.permission.READ_SMS"])
        joined = " ".join(report["issues"])
        self.assertIn("NSCameraUsageDescription", joined)
        self.assertIn("PrivacyInfo.xcprivacy", joined)
        self.assertNotIn("path", report["android"])
        self.assertNotIn("path", report["ios"])
        self.assertNotIn("/tmp", json.dumps(report))
        self.assertNotIn("/var/folders", json.dumps(report))

    def test_unknown_privacy_manifest_is_not_reported_as_missing(self):
        report = self.structured("audit_flutter_permissions", info_plist=PLIST)
        self.assertNotIn("PrivacyInfo", " ".join(report["issues"]))
        self.assertTrue(any("privacy manifest" in note for note in report["not_checked"]))

    def test_audit_rejects_bad_input_without_echoing_it(self):
        result = self.call("audit_flutter_permissions", android_manifest="<manifest>SECRET-CONTENT")
        self.assertTrue(result["isError"])
        self.assertNotIn("SECRET-CONTENT", json.dumps(result))
        self.assertTrue(self.call("audit_flutter_permissions")["isError"])
        entity = '<!DOCTYPE x [<!ENTITY a "b">]><manifest/>'
        self.assertTrue(self.call("audit_flutter_permissions", android_manifest=entity)["isError"])

    def test_lookup(self):
        self.assertEqual(self.structured("look_up_android_permission", permission="read_sms")["tier"], "restricted")
        self.assertEqual(self.structured("look_up_android_permission", permission="android.permission.INTERNET")["tier"], "normal")
        self.assertEqual(self.structured("look_up_android_permission", permission="FOREGROUND_SERVICE_CAMERA")["tier"], "restricted")
        self.assertFalse(self.structured("look_up_android_permission", permission="MADE_UP")["known"])
        self.assertTrue(self.call("look_up_android_permission", permission="not a permission!")["isError"])

    def test_google_play_limits(self):
        check = self.structured("check_google_play_listing", title="x" * 31, short_description="Track your day")
        self.assertFalse(check["passes"])
        self.assertIn("1 character(s) over", check["problems"][0])
        self.assertEqual(self.structured("check_google_play_listing", title="x" * 30)["passes"], True)
        flagged = self.structured("check_google_play_listing", title="Best #1 Tracker")
        self.assertIn("#1", flagged["warnings"][0])
        self.assertFalse(self.structured("check_google_play_listing", title="Tracker 🚀")["passes"])
        self.assertEqual(self.structured("check_google_play_listing", title="Freedom Notes")["warnings"], [])

    def test_app_store_keywords(self):
        check = self.structured("check_app_store_listing", name="Ledger", subtitle="Expense Tracker", keywords="budget, budget,ledger")
        self.assertFalse(check["passes"])
        problems = " ".join(check["problems"])
        self.assertIn("spaces", problems)
        self.assertIn("duplicates", problems)
        self.assertIn("ledger", " ".join(check["warnings"]))
        self.assertTrue(self.structured("check_app_store_listing", keywords="budget,money")["passes"])
        self.assertTrue(self.call("check_app_store_listing")["isError"])

    def test_version_bump(self):
        self.assertEqual(self.structured("plan_version_bump", current_version="1.4.2+37", part="minor")["new_version"], "1.5.0+38")
        plan = self.structured("plan_version_bump", current_version="1.4.2+37", part="patch")
        self.assertEqual((plan["pubspec_line"], plan["git_tag"]), ("version: 1.4.3+38", "v1.4.3"))
        self.assertEqual(self.structured("plan_version_bump", current_version="1.0.0", part="build")["new_version"], "1.0.0+1")
        lower = self.structured("plan_version_bump", current_version="1.0.0+9", part="exact", exact_version="2.0.0+3")
        self.assertIn("reject", lower["warnings"][0])
        self.assertTrue(self.call("plan_version_bump", current_version="abc", part="patch")["isError"])
        self.assertTrue(self.call("plan_version_bump", current_version="1.0.0+1", part="exact")["isError"])

    def test_errors_reach_the_user_with_guidance(self):
        result = self.call("plan_version_bump", current_version="abc", part="patch")
        self.assertIn("must look like 1.4.2+37", result["content"][0]["text"])
        result = self.call("audit_flutter_permissions", android_manifest="<manifest>broken")
        self.assertIn("Paste the complete XML", result["content"][0]["text"])

    def test_domain_challenge(self):
        with urllib.request.urlopen(self.base + "/.well-known/openai-apps-challenge") as response:
            self.assertEqual(response.read().decode(), "token-123")


if __name__ == "__main__":
    unittest.main()
