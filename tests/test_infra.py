"""Safety checks on the Terraform in infra/ (Stage 7e). terraform fmt/validate run in CI."""
import re
from pathlib import Path

INFRA = Path(__file__).resolve().parents[1] / "infra"


def tf(name):
    return (INFRA / name).read_text(encoding="utf-8")


def resources():
    return re.findall(r'^resource "(\w+)" "(\w+)"', tf("main.tf"), flags=re.M)


def test_every_resource_is_imported_not_created():
    imported = set(re.findall(r"to = (\w+\.\w+)", tf("imports.tf")))
    assert {f"{t}.{n}" for t, n in resources()} == imported


def test_every_resource_is_protected_from_destroy():
    blocks = re.split(r'^resource "', tf("main.tf"), flags=re.M)[1:]
    assert len(blocks) == len(resources()) == 5
    for block in blocks:
        assert "prevent_destroy = true" in block, block.splitlines()[0]


def test_no_subscription_ids_keys_or_state_in_the_repo():
    text = "".join(p.read_text(encoding="utf-8") for p in INFRA.glob("*.tf"))
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
    assert "primary_access_key" not in text and "primary_key" not in text
    assert not list(INFRA.glob("*.tfstate*"))
    gitignore = (INFRA.parent / ".gitignore").read_text(encoding="utf-8")
    assert "*.tfstate" in gitignore and "infra/.terraform/" in gitignore


def test_terraform_matches_what_the_app_uses():
    main = tf("main.tf")
    for deployment in ('"gpt-4.1-mini"', '"text-embedding-3-small"'):
        assert f"name                   = {deployment}" in main
    assert 'sku                           = "free"' in main


def test_ci_checks_the_terraform():
    ci = (INFRA.parent / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "terraform fmt -check" in ci and "terraform validate" in ci


# --- ASK-8: Entra ID identity -------------------------------------------------------------------

def role_assignments():
    blocks = re.split(r'^resource "azurerm_role_assignment" "', tf("identity.tf"), flags=re.M)[1:]
    return {b.split('"', 1)[0]: (re.search(r'role_definition_name = "([^"]+)"', b).group(1),
                                 re.search(r"principal_id\s+= (\S+)", b).group(1)) for b in blocks}


def test_live_app_gets_least_privilege_roles_only():
    render_roles = {role for role, who in role_assignments().values() if "service_principal.render" in who}
    assert render_roles == {"Cognitive Services OpenAI User", "Search Index Data Reader"}


def test_no_broad_roles_anywhere():
    for role, _ in role_assignments().values():
        assert role not in {"Owner", "Contributor", "Cognitive Services Contributor"}, role


def test_client_secret_is_never_in_terraform_state():
    text = tf("identity.tf")
    assert "azuread_application_password" not in text and "azuread_service_principal_password" not in text
    assert "client_secret" not in tf("outputs.tf") and "password" not in tf("outputs.tf")
