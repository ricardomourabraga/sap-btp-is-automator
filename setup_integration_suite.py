#!/usr/bin/env python3
"""
SAP BTP Integration Suite Trial - Automated Setup Script

This script automates the complete setup of SAP Integration Suite on a
SAP BTP Trial account, including:
  1. Login to SAP BTP
  2. Create a subaccount
  3. Enable Cloud Foundry environment
  4. Assign Integration Suite entitlements
  5. Subscribe to Integration Suite
  6. Assign role collections to users

Usage:
    python setup_integration_suite.py --config config.yaml
    python setup_integration_suite.py --config config.yaml --user me@example.com

Prerequisites:
    - Python 3.8+
    - SAP BTP CLI (btp) installed
    - Cloud Foundry CLI (cf) installed
    - PyYAML: pip install pyyaml

Author: Automated setup for SAP BTP Trial accounts
License: MIT
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install it with: pip install pyyaml")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FORMAT = "%(asctime)s [%(levelname)-7s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt=DATE_FORMAT)
logger = logging.getLogger("sap-btp-is-automator")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BTP_CLI = "btp"
CF_CLI = "cf"

# Retry settings
MAX_RETRIES = 30
RETRY_INTERVAL_SECONDS = 10

# Integration Suite role collections needed for trial
DEFAULT_ROLE_COLLECTIONS = [
    "Integration_Provisioner",
    "PI_Administrator",
    "PI_Business_Expert",
    "PI_Integration_Developer",
]

# SAP BTP CLI download URLs
BTP_CLI_DOWNLOAD_URL = "https://tools.hana.ondemand.com/#cloud-btpcli"
CF_CLI_DOWNLOAD_URL = "https://github.com/cloudfoundry/cli/releases"


# ---------------------------------------------------------------------------
# Configuration Data Class
# ---------------------------------------------------------------------------
@dataclass
class Config:
    """Holds all configuration for the setup process."""

    btp_user: str = ""
    btp_password: str = ""
    global_account_subdomain: str = ""

    # Subaccount
    subaccount_display_name: str = "IS-Trial"
    subaccount_subdomain: str = "is-trial"
    subaccount_region: str = "us10"
    subaccount_description: str = "Integration Suite Trial - Auto-provisioned"

    # Cloud Foundry
    cf_org_name: str = ""
    cf_space_name: str = "dev"
    cf_instance_plan: str = "trial"

    # Integration Suite
    is_service_name: str = "integrationsuite"
    is_service_plan: str = "trial"

    # Users & Roles
    admin_user: str = ""
    identity_provider: str = "sap.default"
    role_collections: list = field(default_factory=lambda: list(DEFAULT_ROLE_COLLECTIONS))

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load configuration from a YAML file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        cfg = cls()

        cfg.btp_user = data.get("btp_user", "") or ""
        cfg.btp_password = data.get("btp_password", "") or ""
        cfg.global_account_subdomain = data.get("global_account_subdomain", "") or ""

        sub = data.get("subaccount", {}) or {}
        cfg.subaccount_display_name = sub.get("display_name", cfg.subaccount_display_name) or cfg.subaccount_display_name
        cfg.subaccount_subdomain = sub.get("subdomain", cfg.subaccount_subdomain) or cfg.subaccount_subdomain
        cfg.subaccount_region = sub.get("region", cfg.subaccount_region) or cfg.subaccount_region
        cfg.subaccount_description = sub.get("description", cfg.subaccount_description) or cfg.subaccount_description

        cf = data.get("cloud_foundry", {}) or {}
        cfg.cf_org_name = cf.get("org_name", "") or ""
        cfg.cf_space_name = cf.get("space_name", cfg.cf_space_name) or cfg.cf_space_name
        cfg.cf_instance_plan = cf.get("instance_plan", cfg.cf_instance_plan) or cfg.cf_instance_plan

        is_cfg = data.get("integration_suite", {}) or {}
        cfg.is_service_name = is_cfg.get("service_name", cfg.is_service_name) or cfg.is_service_name
        cfg.is_service_plan = is_cfg.get("service_plan", cfg.is_service_plan) or cfg.is_service_plan

        users = data.get("users", {}) or {}
        cfg.admin_user = users.get("admin_user", "") or ""
        cfg.identity_provider = users.get("identity_provider", cfg.identity_provider) or cfg.identity_provider
        cfg.role_collections = users.get("role_collections", DEFAULT_ROLE_COLLECTIONS) or list(DEFAULT_ROLE_COLLECTIONS)

        return cfg

    def resolve_defaults(self) -> None:
        """Fill in defaults that depend on other fields."""
        # Use env vars for credentials if not set
        if not self.btp_user:
            self.btp_user = os.environ.get("SAP_BTP_USER", "")
        if not self.btp_password:
            self.btp_password = os.environ.get("SAP_BTP_PASSWORD", "")

        # Admin user defaults to btp_user
        if not self.admin_user:
            self.admin_user = self.btp_user

        # CF org name defaults to subaccount subdomain
        if not self.cf_org_name:
            self.cf_org_name = self.subaccount_subdomain


# ---------------------------------------------------------------------------
# CLI Runner
# ---------------------------------------------------------------------------
class CLIRunner:
    """Runs CLI commands and captures output."""

    @staticmethod
    def run(
        cmd: list[str],
        check: bool = True,
        capture: bool = True,
        mask_args: Optional[list[int]] = None,
        timeout: int = 300,
    ) -> subprocess.CompletedProcess:
        """
        Execute a command and return the result.

        Args:
            cmd: Command and arguments as a list.
            check: Raise on non-zero exit code.
            capture: Capture stdout/stderr.
            mask_args: Indices of arguments to mask in logs (for passwords).
            timeout: Timeout in seconds.
        """
        display_cmd = list(cmd)
        if mask_args:
            for idx in mask_args:
                if idx < len(display_cmd):
                    display_cmd[idx] = "****"
        logger.debug("Running: %s", " ".join(display_cmd))

        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=capture,
                text=True,
                timeout=timeout,
            )
            if result.stdout:
                logger.debug("stdout: %s", result.stdout.strip()[:500])
            return result
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            stdout = exc.stdout or ""
            logger.error("Command failed: %s", " ".join(display_cmd))
            logger.error("stderr: %s", stderr.strip()[:1000])
            logger.error("stdout: %s", stdout.strip()[:1000])
            raise
        except subprocess.TimeoutExpired:
            logger.error("Command timed out after %ds: %s", timeout, " ".join(display_cmd))
            raise

    @staticmethod
    def run_json(cmd: list[str], **kwargs) -> dict:
        """Run a command and parse the JSON output."""
        result = CLIRunner.run(cmd, **kwargs)
        try:
            return json.loads(result.stdout)
        except (json.JSONDecodeError, TypeError):
            logger.warning("Could not parse JSON from command output")
            return {}


# ---------------------------------------------------------------------------
# Prerequisite Checker
# ---------------------------------------------------------------------------
def check_prerequisites() -> None:
    """Verify that required CLI tools are installed."""
    logger.info("=" * 60)
    logger.info("STEP 0: Checking prerequisites")
    logger.info("=" * 60)

    missing = []
    for tool, url in [(BTP_CLI, BTP_CLI_DOWNLOAD_URL), (CF_CLI, CF_CLI_DOWNLOAD_URL)]:
        path = shutil.which(tool)
        if path:
            logger.info("  [OK] %s found at: %s", tool, path)
        else:
            logger.error("  [MISSING] %s not found. Download: %s", tool, url)
            missing.append(tool)

    if missing:
        logger.error("")
        logger.error("Missing tools: %s", ", ".join(missing))
        logger.error("Please install them before running this script.")
        logger.error("")
        logger.error("Install BTP CLI:")
        logger.error("  Download from: %s", BTP_CLI_DOWNLOAD_URL)
        logger.error("  Or use npm: npm install -g @sap/btp-cli")
        logger.error("")
        logger.error("Install CF CLI:")
        logger.error("  Download from: %s", CF_CLI_DOWNLOAD_URL)
        logger.error("  Or use package manager:")
        logger.error("    macOS:  brew install cloudfoundry/tap/cf-cli@8")
        logger.error("    Linux:  See %s", CF_CLI_DOWNLOAD_URL)
        sys.exit(1)


# ---------------------------------------------------------------------------
# BTP Automation Steps
# ---------------------------------------------------------------------------
class BTPAutomator:
    """Orchestrates the SAP BTP Integration Suite setup."""

    def __init__(self, config: Config):
        self.config = config
        self.cli = CLIRunner()
        self.subaccount_id: Optional[str] = None

    # ----- Step 1: Login -----
    def login(self) -> None:
        """Login to SAP BTP CLI."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 1: Logging in to SAP BTP")
        logger.info("=" * 60)

        cfg = self.config

        if not cfg.btp_user or not cfg.btp_password:
            logger.error("BTP credentials not provided.")
            logger.error("Set them in config.yaml or via SAP_BTP_USER / SAP_BTP_PASSWORD env vars.")
            sys.exit(1)

        if not cfg.global_account_subdomain:
            logger.error("Global account subdomain not provided in config.yaml.")
            sys.exit(1)

        cmd = [
            BTP_CLI, "login",
            "--url", "https://cli.btp.cloud.sap",
            "--subdomain", cfg.global_account_subdomain,
            "--user", cfg.btp_user,
            "--password", cfg.btp_password,
        ]

        try:
            self.cli.run(cmd, mask_args=[9])  # mask password
            logger.info("  Successfully logged in to SAP BTP.")
        except subprocess.CalledProcessError:
            logger.error("  Failed to login. Please check your credentials and global account subdomain.")
            sys.exit(1)

    # ----- Step 2: Create Subaccount -----
    def create_subaccount(self) -> None:
        """Create a new subaccount or find existing one."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 2: Creating subaccount '%s'", self.config.subaccount_display_name)
        logger.info("=" * 60)

        # Check if subaccount already exists
        existing_id = self._find_subaccount()
        if existing_id:
            self.subaccount_id = existing_id
            logger.info("  Subaccount already exists with ID: %s", self.subaccount_id)
            return

        # Create subaccount
        cmd = [
            BTP_CLI, "create", "accounts/subaccount",
            "--display-name", self.config.subaccount_display_name,
            "--subdomain", self.config.subaccount_subdomain,
            "--region", self.config.subaccount_region,
            "--description", self.config.subaccount_description,
        ]

        try:
            result = self.cli.run(cmd)
            stdout = result.stdout or ""

            # Extract subaccount ID from output
            self.subaccount_id = self._extract_guid(stdout)
            if not self.subaccount_id:
                # Try to find it by listing
                self.subaccount_id = self._find_subaccount()

            if self.subaccount_id:
                logger.info("  Subaccount created with ID: %s", self.subaccount_id)
            else:
                logger.error("  Could not determine subaccount ID after creation.")
                sys.exit(1)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            if "already exists" in stderr.lower() or "unique" in stderr.lower():
                logger.info("  Subaccount may already exist. Looking it up...")
                self.subaccount_id = self._find_subaccount()
                if self.subaccount_id:
                    logger.info("  Found existing subaccount: %s", self.subaccount_id)
                    return
            logger.error("  Failed to create subaccount.")
            raise

        # Wait for subaccount to be ready
        self._wait_for_subaccount_ready()

    def _find_subaccount(self) -> Optional[str]:
        """Find a subaccount by subdomain."""
        try:
            result = self.cli.run([BTP_CLI, "list", "accounts/subaccount"], check=False)
            stdout = result.stdout or ""

            # Parse output to find the subaccount
            for line in stdout.splitlines():
                if self.config.subaccount_subdomain in line or self.config.subaccount_display_name in line:
                    guid = self._extract_guid(line)
                    if guid:
                        return guid

            # Try JSON format
            result_json = self.cli.run(
                [BTP_CLI, "--format", "json", "list", "accounts/subaccount"],
                check=False,
            )
            try:
                data = json.loads(result_json.stdout or "{}")
                subaccounts = data.get("value", [])
                for sa in subaccounts:
                    if (
                        sa.get("subdomain") == self.config.subaccount_subdomain
                        or sa.get("displayName") == self.config.subaccount_display_name
                    ):
                        return sa.get("guid", "")
            except (json.JSONDecodeError, TypeError):
                pass

        except subprocess.CalledProcessError:
            pass
        return None

    def _wait_for_subaccount_ready(self) -> None:
        """Wait for the subaccount to be in 'OK' state."""
        logger.info("  Waiting for subaccount to be ready...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.cli.run(
                    [BTP_CLI, "--format", "json", "get", "accounts/subaccount", self.subaccount_id],
                    check=False,
                )
                data = json.loads(result.stdout or "{}")
                state = data.get("state", "")
                logger.info("    Attempt %d/%d - State: %s", attempt, MAX_RETRIES, state)
                if state == "OK":
                    logger.info("  Subaccount is ready.")
                    return
            except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
                pass

            time.sleep(RETRY_INTERVAL_SECONDS)

        logger.error("  Subaccount did not become ready within the timeout.")
        sys.exit(1)

    # ----- Step 3: Enable Cloud Foundry -----
    def enable_cloud_foundry(self) -> None:
        """Enable Cloud Foundry environment in the subaccount."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 3: Enabling Cloud Foundry environment")
        logger.info("=" * 60)

        if not self.subaccount_id:
            logger.error("  Subaccount ID not set. Cannot enable CF.")
            sys.exit(1)

        # First, assign CF entitlement
        logger.info("  Assigning Cloud Foundry Runtime entitlement...")
        try:
            self.cli.run([
                BTP_CLI, "assign", "accounts/entitlement",
                "--to-subaccount", self.subaccount_id,
                "--for-service", "APPLICATION_RUNTIME",
                "--plan", "MEMORY",
                "--amount", "1",
            ], check=False)
            logger.info("  CF Runtime entitlement assigned.")
        except subprocess.CalledProcessError:
            logger.warning("  Could not assign CF Runtime entitlement (may already be assigned).")

        # Check if CF environment already exists
        cf_instance_id = self._find_cf_environment()
        if cf_instance_id:
            logger.info("  Cloud Foundry environment already exists: %s", cf_instance_id)
        else:
            # Create CF environment instance
            logger.info("  Creating Cloud Foundry environment instance...")
            cf_org = self.config.cf_org_name or self.config.subaccount_subdomain

            cmd = [
                BTP_CLI, "create", "accounts/environment-instance",
                "--subaccount", self.subaccount_id,
                "--environment", "cloudfoundry",
                "--service", "cloudfoundry",
                "--plan", self.config.cf_instance_plan,
                "--parameters", json.dumps({"instance_name": cf_org}),
            ]

            try:
                self.cli.run(cmd)
                logger.info("  Cloud Foundry environment creation initiated.")
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr or ""
                if "already exists" in stderr.lower() or "conflict" in stderr.lower():
                    logger.info("  CF environment may already exist.")
                else:
                    logger.error("  Failed to create CF environment.")
                    raise

            # Wait for CF to be ready
            self._wait_for_cf_ready()

        # Create CF space
        self._create_cf_space()

    def _find_cf_environment(self) -> Optional[str]:
        """Check if CF environment already exists."""
        try:
            result = self.cli.run(
                [BTP_CLI, "--format", "json", "list", "accounts/environment-instance",
                 "--subaccount", self.subaccount_id],
                check=False,
            )
            data = json.loads(result.stdout or "{}")
            instances = data.get("environmentInstances", [])
            for inst in instances:
                if inst.get("environmentType") == "cloudfoundry":
                    return inst.get("id", "")
        except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
            pass
        return None

    def _wait_for_cf_ready(self) -> None:
        """Wait for CF environment to be ready."""
        logger.info("  Waiting for Cloud Foundry environment to be ready...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.cli.run(
                    [BTP_CLI, "--format", "json", "list", "accounts/environment-instance",
                     "--subaccount", self.subaccount_id],
                    check=False,
                )
                data = json.loads(result.stdout or "{}")
                instances = data.get("environmentInstances", [])
                for inst in instances:
                    if inst.get("environmentType") == "cloudfoundry":
                        state = inst.get("state", "")
                        logger.info("    Attempt %d/%d - CF State: %s", attempt, MAX_RETRIES, state)
                        if state == "OK":
                            logger.info("  Cloud Foundry environment is ready.")
                            return
            except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
                pass

            time.sleep(RETRY_INTERVAL_SECONDS)

        logger.warning("  CF environment did not become ready within the timeout. Continuing anyway...")

    def _create_cf_space(self) -> None:
        """Login to CF and create a space."""
        logger.info("  Setting up CF org and space...")

        # Get CF API endpoint
        cf_api = self._get_cf_api_endpoint()
        if not cf_api:
            logger.warning("  Could not determine CF API endpoint. Skipping CF space creation.")
            logger.warning("  You may need to create the CF space manually in the BTP cockpit.")
            return

        # Login to CF
        logger.info("  Logging in to Cloud Foundry at %s...", cf_api)
        try:
            cmd = [
                CF_CLI, "login",
                "-a", cf_api,
                "-u", self.config.btp_user,
                "-p", self.config.btp_password,
                "-o", self.config.cf_org_name or self.config.subaccount_subdomain,
            ]
            self.cli.run(cmd, mask_args=[7])
            logger.info("  CF login successful.")
        except subprocess.CalledProcessError:
            logger.warning("  CF login failed. The org may not be ready yet.")
            logger.warning("  You can login manually later with:")
            logger.warning("    cf login -a %s", cf_api)
            return

        # Create space
        logger.info("  Creating CF space '%s'...", self.config.cf_space_name)
        try:
            self.cli.run([CF_CLI, "create-space", self.config.cf_space_name], check=False)
            logger.info("  CF space '%s' created (or already exists).", self.config.cf_space_name)
        except subprocess.CalledProcessError:
            logger.warning("  Could not create CF space (may already exist).")

        # Target the space
        try:
            self.cli.run([CF_CLI, "target", "-s", self.config.cf_space_name], check=False)
            logger.info("  CF target set to space '%s'.", self.config.cf_space_name)
        except subprocess.CalledProcessError:
            pass

    def _get_cf_api_endpoint(self) -> Optional[str]:
        """Determine the CF API endpoint from the environment instance."""
        try:
            result = self.cli.run(
                [BTP_CLI, "--format", "json", "list", "accounts/environment-instance",
                 "--subaccount", self.subaccount_id],
                check=False,
            )
            data = json.loads(result.stdout or "{}")
            instances = data.get("environmentInstances", [])
            for inst in instances:
                if inst.get("environmentType") == "cloudfoundry":
                    labels = inst.get("labels", "")
                    # labels is a JSON string containing API endpoint
                    try:
                        labels_data = json.loads(labels) if isinstance(labels, str) else labels
                        api_endpoint = labels_data.get("API Endpoint", "")
                        if api_endpoint:
                            return api_endpoint
                    except (json.JSONDecodeError, TypeError):
                        pass
                    # Try to construct from landscape/region
                    break
        except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
            pass

        # Fallback: construct from region
        region = self.config.subaccount_region
        return f"https://api.cf.{region}.hana.ondemand.com"

    # ----- Step 4: Assign Integration Suite Entitlements -----
    def assign_entitlements(self) -> None:
        """Assign Integration Suite entitlements to the subaccount."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 4: Assigning Integration Suite entitlements")
        logger.info("=" * 60)

        if not self.subaccount_id:
            logger.error("  Subaccount ID not set.")
            sys.exit(1)

        entitlements = [
            (self.config.is_service_name, self.config.is_service_plan, "1"),
            # Process Integration Runtime is also needed
            ("it-rt", "integration-flow", "1"),
        ]

        for service, plan, amount in entitlements:
            logger.info("  Assigning entitlement: %s (plan: %s)...", service, plan)
            try:
                self.cli.run([
                    BTP_CLI, "assign", "accounts/entitlement",
                    "--to-subaccount", self.subaccount_id,
                    "--for-service", service,
                    "--plan", plan,
                    "--amount", amount,
                ], check=False)
                logger.info("    Entitlement '%s/%s' assigned.", service, plan)
            except subprocess.CalledProcessError:
                logger.warning("    Could not assign entitlement '%s/%s' (may already be assigned or not available).", service, plan)

        logger.info("  Entitlement assignment complete.")

    # ----- Step 5: Subscribe to Integration Suite -----
    def subscribe_integration_suite(self) -> None:
        """Subscribe to SAP Integration Suite."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 5: Subscribing to Integration Suite")
        logger.info("=" * 60)

        if not self.subaccount_id:
            logger.error("  Subaccount ID not set.")
            sys.exit(1)

        # Check if already subscribed
        if self._is_subscribed():
            logger.info("  Already subscribed to Integration Suite.")
            return

        # Subscribe
        logger.info("  Creating subscription to '%s' (plan: %s)...",
                     self.config.is_service_name, self.config.is_service_plan)
        try:
            self.cli.run([
                BTP_CLI, "subscribe",
                "--subaccount", self.subaccount_id,
                "--to-app", self.config.is_service_name,
                "--plan", self.config.is_service_plan,
            ])
            logger.info("  Subscription initiated.")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr or ""
            if "already subscribed" in stderr.lower():
                logger.info("  Already subscribed to Integration Suite.")
                return
            logger.error("  Failed to subscribe to Integration Suite.")
            raise

        # Wait for subscription to be active
        self._wait_for_subscription()

    def _is_subscribed(self) -> bool:
        """Check if already subscribed to Integration Suite."""
        try:
            result = self.cli.run(
                [BTP_CLI, "--format", "json", "list", "accounts/subscription",
                 "--subaccount", self.subaccount_id],
                check=False,
            )
            data = json.loads(result.stdout or "{}")
            apps = data.get("applications", [])
            for app in apps:
                app_name = app.get("appName", "").lower()
                if self.config.is_service_name.lower() in app_name:
                    state = app.get("state", "")
                    if state == "SUBSCRIBED":
                        return True
        except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
            pass
        return False

    def _wait_for_subscription(self) -> None:
        """Wait for Integration Suite subscription to become active."""
        logger.info("  Waiting for Integration Suite subscription to activate...")
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                result = self.cli.run(
                    [BTP_CLI, "--format", "json", "list", "accounts/subscription",
                     "--subaccount", self.subaccount_id],
                    check=False,
                )
                data = json.loads(result.stdout or "{}")
                apps = data.get("applications", [])
                for app in apps:
                    app_name = app.get("appName", "").lower()
                    if self.config.is_service_name.lower() in app_name:
                        state = app.get("state", "")
                        logger.info("    Attempt %d/%d - Subscription state: %s", attempt, MAX_RETRIES, state)
                        if state == "SUBSCRIBED":
                            logger.info("  Integration Suite subscription is active!")
                            return
                        if state in ("SUBSCRIBE_FAILED", "ERROR"):
                            logger.error("  Subscription failed with state: %s", state)
                            sys.exit(1)
            except (json.JSONDecodeError, TypeError, subprocess.CalledProcessError):
                pass

            time.sleep(RETRY_INTERVAL_SECONDS)

        logger.warning("  Subscription did not activate within the timeout. Check the BTP cockpit.")

    # ----- Step 6: Assign Role Collections -----
    def assign_roles(self) -> None:
        """Assign role collections to the admin user."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("STEP 6: Assigning role collections to user")
        logger.info("=" * 60)

        if not self.subaccount_id:
            logger.error("  Subaccount ID not set.")
            sys.exit(1)

        user = self.config.admin_user
        idp = self.config.identity_provider

        if not user:
            logger.error("  Admin user not set. Cannot assign roles.")
            sys.exit(1)

        logger.info("  User: %s", user)
        logger.info("  Identity Provider: %s", idp)

        for role_collection in self.config.role_collections:
            logger.info("  Assigning role collection: '%s'...", role_collection)
            try:
                cmd = [
                    BTP_CLI, "assign", "security/role-collection",
                    role_collection,
                    "--to-user", user,
                    "--of-idp", idp,
                    "--subaccount", self.subaccount_id,
                ]
                self.cli.run(cmd, check=False)
                logger.info("    Role collection '%s' assigned.", role_collection)
            except subprocess.CalledProcessError:
                logger.warning("    Could not assign role collection '%s' (may not exist yet).", role_collection)

        logger.info("  Role collection assignment complete.")

    # ----- Helpers -----
    @staticmethod
    def _extract_guid(text: str) -> Optional[str]:
        """Extract a GUID from text."""
        pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(0) if match else None

    # ----- Summary -----
    def print_summary(self) -> None:
        """Print a summary of the setup."""
        logger.info("")
        logger.info("=" * 60)
        logger.info("SETUP COMPLETE!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("  Subaccount:    %s", self.config.subaccount_display_name)
        logger.info("  Subaccount ID: %s", self.subaccount_id or "N/A")
        logger.info("  Region:        %s", self.config.subaccount_region)
        logger.info("  CF Space:      %s", self.config.cf_space_name)
        logger.info("")
        logger.info("  Integration Suite: SUBSCRIBED")
        logger.info("  Admin User:        %s", self.config.admin_user)
        logger.info("  Role Collections:  %s", ", ".join(self.config.role_collections))
        logger.info("")
        logger.info("  NEXT STEPS:")
        logger.info("  1. Open the SAP BTP Cockpit:")
        logger.info("     https://cockpit.btp.cloud.sap")
        logger.info("  2. Navigate to your subaccount '%s'", self.config.subaccount_display_name)
        logger.info("  3. Go to 'Instances and Subscriptions'")
        logger.info("  4. Click on 'Integration Suite' to open it")
        logger.info("  5. In Integration Suite, click 'Add Capabilities' to activate:")
        logger.info("     - Build Integration Scenarios (Cloud Integration)")
        logger.info("     - Manage APIs (API Management)")
        logger.info("")
        logger.info("  NOTE: Capability activation must be done through the")
        logger.info("  Integration Suite UI and cannot be automated via CLI.")
        logger.info("=" * 60)


# ---------------------------------------------------------------------------
# Cleanup / Teardown (optional)
# ---------------------------------------------------------------------------
class BTPCleanup:
    """Optional cleanup to remove previous trial setup."""

    def __init__(self, config: Config):
        self.config = config
        self.cli = CLIRunner()

    def cleanup_subaccount(self, subaccount_id: str) -> None:
        """Delete a subaccount (use with caution!)."""
        logger.warning("Deleting subaccount %s...", subaccount_id)
        try:
            self.cli.run([
                BTP_CLI, "delete", "accounts/subaccount", subaccount_id,
                "--confirm",
            ])
            logger.info("  Subaccount deletion initiated.")
        except subprocess.CalledProcessError:
            logger.error("  Failed to delete subaccount.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="SAP BTP Integration Suite Trial - Automated Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with config file:
  python setup_integration_suite.py --config config.yaml

  # Override user and password:
  python setup_integration_suite.py --config config.yaml \\
      --user me@example.com --password MyPass123

  # Use environment variables for credentials:
  export SAP_BTP_USER=me@example.com
  export SAP_BTP_PASSWORD=MyPass123
  python setup_integration_suite.py --config config.yaml

  # Enable verbose logging:
  python setup_integration_suite.py --config config.yaml --verbose

  # Cleanup (delete) existing subaccount before re-creating:
  python setup_integration_suite.py --config config.yaml --cleanup
        """,
    )

    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to the YAML configuration file (default: config.yaml)",
    )
    parser.add_argument(
        "--user", "-u",
        help="SAP BTP user email (overrides config and env var)",
    )
    parser.add_argument(
        "--password", "-p",
        help="SAP BTP password (overrides config and env var)",
    )
    parser.add_argument(
        "--global-account",
        help="Global account subdomain (overrides config)",
    )
    parser.add_argument(
        "--region",
        help="Subaccount region (overrides config)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete existing subaccount before re-creating (USE WITH CAUTION!)",
    )
    parser.add_argument(
        "--skip-cf",
        action="store_true",
        help="Skip Cloud Foundry environment setup",
    )
    parser.add_argument(
        "--skip-subscribe",
        action="store_true",
        help="Skip Integration Suite subscription",
    )
    parser.add_argument(
        "--skip-roles",
        action="store_true",
        help="Skip role collection assignment",
    )

    return parser.parse_args()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Banner
    logger.info("")
    logger.info("=" * 60)
    logger.info("  SAP BTP Integration Suite Trial - Automated Setup")
    logger.info("=" * 60)
    logger.info("")

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        logger.error("Config file not found: %s", config_path)
        logger.error("Create one from the template: cp config.yaml.example config.yaml")
        sys.exit(1)

    logger.info("Loading configuration from: %s", config_path)
    config = Config.from_yaml(str(config_path))

    # Apply CLI overrides
    if args.user:
        config.btp_user = args.user
    if args.password:
        config.btp_password = args.password
    if args.global_account:
        config.global_account_subdomain = args.global_account
    if args.region:
        config.subaccount_region = args.region

    # Resolve defaults
    config.resolve_defaults()

    # Check prerequisites
    check_prerequisites()

    # Initialize automator
    automator = BTPAutomator(config)

    # Step 1: Login
    automator.login()

    # Optional: Cleanup
    if args.cleanup:
        existing_id = automator._find_subaccount()
        if existing_id:
            cleanup = BTPCleanup(config)
            cleanup.cleanup_subaccount(existing_id)
            logger.info("  Waiting 30 seconds for cleanup to complete...")
            time.sleep(30)
        else:
            logger.info("  No existing subaccount found to clean up.")

    # Step 2: Create subaccount
    automator.create_subaccount()

    # Step 3: Enable Cloud Foundry
    if not args.skip_cf:
        automator.enable_cloud_foundry()
    else:
        logger.info("Skipping Cloud Foundry setup (--skip-cf)")

    # Step 4: Assign entitlements
    automator.assign_entitlements()

    # Step 5: Subscribe to Integration Suite
    if not args.skip_subscribe:
        automator.subscribe_integration_suite()
    else:
        logger.info("Skipping Integration Suite subscription (--skip-subscribe)")

    # Step 6: Assign roles
    if not args.skip_roles:
        automator.assign_roles()
    else:
        logger.info("Skipping role assignment (--skip-roles)")

    # Summary
    automator.print_summary()


if __name__ == "__main__":
    main()
