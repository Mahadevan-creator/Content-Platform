"""
DocuSign eSignature service for sending NDA and Contractor Agreement to candidates.
Uses JWT authentication and template-based envelopes.

Template setup for candidate placeholders:
  In your DocuSign template, add Text fields where the candidate details should appear.
  Set the Data Label for each field to match:
    - "CandidateName" (or DOCUSIGN_TAB_CANDIDATE_NAME) → pre-filled with candidate name
    - "CandidateEmail" (or DOCUSIGN_TAB_CANDIDATE_EMAIL) → pre-filled with candidate email
    - "CandidatePhone" (or DOCUSIGN_TAB_CANDIDATE_PHONE) → pre-filled with candidate phone
    - "CandidateAddress" (or DOCUSIGN_TAB_CANDIDATE_ADDRESS) → pre-filled with candidate address
    - "DocumentDate" (or DOCUSIGN_TAB_DOCUMENT_DATE) → pre-filled with date when sent (e.g. "January 5, 2026")
  Tab labels are case-sensitive and must match exactly.
"""
import json
import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path

from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, ApiException, TemplatesApi

logger = logging.getLogger(__name__)


def _get_private_key() -> str:
    """Load DocuSign private key from env or file."""
    key = os.getenv("DOCUSIGN_PRIVATE_KEY")
    if key:
        # Handle newlines in env var (often stored as \n)
        return key.replace("\\n", "\n")
    key_path = os.getenv("DOCUSIGN_PRIVATE_KEY_PATH")
    if key_path:
        path = Path(key_path)
        if path.is_absolute():
            full_path = path
        else:
            full_path = Path(__file__).resolve().parent.parent / key_path
        if full_path.exists():
            return full_path.read_text()
    raise ValueError(
        "DocuSign private key not found. Set DOCUSIGN_PRIVATE_KEY or DOCUSIGN_PRIVATE_KEY_PATH in .env"
    )


def _get_api_client() -> ApiClient:
    """Create authenticated DocuSign API client using JWT.
    Uses get_user_info to get the account's base_uri for correct API routing."""
    integration_key = os.getenv("DOCUSIGN_INTEGRATION_KEY")
    user_id = os.getenv("DOCUSIGN_USER_ID")
    account_id = os.getenv("DOCUSIGN_ACCOUNT_ID")

    if not all([integration_key, user_id, account_id]):
        raise ValueError(
            "DocuSign credentials missing. Set DOCUSIGN_INTEGRATION_KEY, DOCUSIGN_USER_ID, DOCUSIGN_ACCOUNT_ID in .env"
        )

    api_client = ApiClient()
    base_path = os.getenv("DOCUSIGN_BASE_PATH", "https://demo.docusign.net/restapi")
    api_client.set_base_path(base_path)
    api_client.host = base_path  # SDK uses .host for API calls, not .base_path

    private_key = _get_private_key()
    # OAuth host: use explicit override, or derive from base_path
    oauth_host = os.getenv("DOCUSIGN_OAUTH_HOST", "").strip()
    if not oauth_host:
        oauth_host = "account-d.docusign.com" if "demo" in base_path else "account.docusign.com"
    api_client.set_oauth_host_name(oauth_host)

    token = api_client.request_jwt_user_token(
        client_id=integration_key,
        user_id=user_id,
        oauth_host_name=oauth_host,
        private_key_bytes=private_key.encode("utf-8"),
        expires_in=3600,
        scopes=["signature", "impersonation"],
    )
    api_client.set_default_header("Authorization", f"Bearer {token.access_token}")

    # Get user info to use the account's actual base_uri (na1, na2, eu, etc.)
    # SDK uses .host for API calls (not .base_path) - must set both or API calls go to wrong env
    user_info = api_client.get_user_info(token.access_token)
    if user_info and user_info.accounts:
        for acc in user_info.accounts:
            if str(acc.account_id) == str(account_id):
                if acc.base_uri:
                    correct_base = acc.base_uri.rstrip("/") + "/restapi"
                    api_client.set_base_path(correct_base)
                    api_client.host = correct_base
                break
        else:
            # Use first/default account if no match
            acc = user_info.accounts[0]
            if acc.base_uri:
                correct_base = acc.base_uri.rstrip("/") + "/restapi"
                api_client.set_base_path(correct_base)
                api_client.host = correct_base

    return api_client


def send_contract_envelope(
    recipient_email: str,
    recipient_name: str,
    include_nda: bool,
    include_contract: bool,
    recipient_phone: Optional[str] = None,
    recipient_address: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send NDA and/or Contractor Agreement to a candidate via DocuSign.

    Args:
        recipient_email: Candidate's email address
        recipient_name: Candidate's display name
        include_nda: Include NDA document
        include_contract: Include Contractor Agreement document
        recipient_phone: Candidate's phone number (optional)
        recipient_address: Candidate's address (optional)

    Returns:
        Dict with envelope_id, status, and any error info
    """
    nda_template_id = os.getenv("DOCUSIGN_NDA_TEMPLATE_ID", "").strip()
    contract_template_id = os.getenv("DOCUSIGN_CONTRACT_TEMPLATE_ID", "").strip()

    logger.info(
        "[DocuSign] send_contract_envelope called: recipient=%s, include_nda=%s, include_contract=%s, "
        "nda_template_id=%s, contract_template_id=%s",
        recipient_email,
        include_nda,
        include_contract,
        nda_template_id or "(empty)",
        contract_template_id or "(empty)",
    )

    if include_nda and not nda_template_id:
        raise ValueError(
            "NDA template not configured. Create an NDA template in DocuSign and set DOCUSIGN_NDA_TEMPLATE_ID in .env"
        )
    if include_contract and not contract_template_id:
        raise ValueError(
            "Contract template not configured. Create a Contractor Agreement template in DocuSign and set DOCUSIGN_CONTRACT_TEMPLATE_ID in .env"
        )
    if not include_nda and not include_contract:
        raise ValueError("Select at least one document (NDA or Contractor Agreement) to send")

    logger.info("[DocuSign] Getting API client...")
    api_client = _get_api_client()
    account_id = os.getenv("DOCUSIGN_ACCOUNT_ID")
    envelopes_api = EnvelopesApi(api_client)
    templates_api = TemplatesApi(api_client)
    logger.info("[DocuSign] API client ready: account_id=%s, host=%s", account_id, getattr(api_client, "host", "?"))

    from docusign_esign import Tabs, Text, SignHere

    # Role name must match exactly what you set in the DocuSign template (e.g. "Signer", "Candidate")
    role_name = os.getenv("DOCUSIGN_TEMPLATE_ROLE_NAME", "Signer").strip() or "Signer"

    # Anchor strings - text in the PDF that DocuSign uses to auto-place fields. Must match the document.
    anchor_document_date = os.getenv("DOCUSIGN_ANCHOR_DOCUMENT_DATE", "[DocumentDate]").strip()
    anchor_candidate_name = os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_NAME", "[CandidateName]").strip()
    anchor_candidate_email = os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_EMAIL", "[CandidateEmail]").strip()
    anchor_candidate_phone = os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_PHONE", "[CandidatePhone]").strip()
    anchor_candidate_address = os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_ADDRESS", "[CandidateAddress]").strip()
    anchor_signature = os.getenv("DOCUSIGN_ANCHOR_SIGNATURE", "**signature**").strip()

    # Pre-flight: verify template exists and is accessible (diagnoses "must specify a template" errors)
    template_ids_to_check = []
    if include_nda and nda_template_id:
        template_ids_to_check.append(("NDA", nda_template_id))
    if include_contract and contract_template_id:
        template_ids_to_check.append(("Contract", contract_template_id))
    for label, tid in template_ids_to_check:
        try:
            tmpl = templates_api.get(account_id, tid)
            signers = getattr(getattr(tmpl, "recipients", None), "signers", None) or []
            roles = [getattr(r, "role_name", None) for r in signers if getattr(r, "role_name", None)]
            logger.info("[DocuSign] Template %s (%s) accessible. Roles in template: %s", label, tid, roles)
            if roles and role_name not in roles:
                logger.warning(
                    "[DocuSign] role_name=%s does not match template roles %s - DocuSign may reject",
                    role_name,
                    roles,
                )
        except ApiException as te:
            err = te.body.decode("utf-8") if isinstance(te.body, bytes) else (te.body or str(te))
            logger.error("[DocuSign] Template %s (%s) pre-flight failed: %s - %s", label, tid, te.status, err)
            if "envelopeid as the templateid" in err.lower() or "envelopeid as templateid" in err.lower():
                raise ValueError(
                    f"DOCUSIGN_CONTRACT_TEMPLATE_ID (or DOCUSIGN_NDA_TEMPLATE_ID) contains an envelope ID, not a template ID. "
                    f"Templates are in DocuSign Admin → Templates (not Envelopes). "
                    f"Create a template from your document, save it, then copy its Template ID from the template URL or details."
                ) from te
            raise ValueError(
                f"Template {label} ({tid}) not accessible: {err}. "
                f"Ensure the template exists in your DocuSign account, is shared with the JWT user (DOCUSIGN_USER_ID), "
                f"and has status 'Available' (not Draft)."
            ) from te

    # Dynamic date when document is sent (e.g. "January 5, 2026")
    from datetime import datetime
    now = datetime.now()
    document_date = f"{now.strftime('%B')} {now.day}, {now.year}"

    # Use anchor_string to auto-place fields in the document (works without pre-defined template tabs).
    # The PDF must contain these anchor strings (e.g. [DocumentDate], [CandidateName]).
    # See backend/templates/README.md for document setup.
    def make_text_tab(anchor: str, value: str):
        return Text(
            value=value,
            anchor_string=anchor,
            anchor_units="pixels",
            anchor_y_offset="0",
            anchor_x_offset="0",
        )

    text_tabs = []
    if anchor_document_date:
        text_tabs.append(make_text_tab(anchor_document_date, document_date))
    if anchor_candidate_name:
        text_tabs.append(make_text_tab(anchor_candidate_name, recipient_name or recipient_email))
    if anchor_candidate_email:
        text_tabs.append(make_text_tab(anchor_candidate_email, recipient_email))
    if anchor_candidate_phone and (recipient_phone or "").strip():
        text_tabs.append(make_text_tab(anchor_candidate_phone, (recipient_phone or "").strip()))
    if anchor_candidate_address and (recipient_address or "").strip():
        text_tabs.append(make_text_tab(anchor_candidate_address, (recipient_address or "").strip()))

    # Sign Here tab - placed at anchor in document (e.g. **signature**)
    sign_here_tabs = [SignHere(
        anchor_string=anchor_signature,
        anchor_units="pixels",
        anchor_y_offset="10",
        anchor_x_offset="0",
    )] if anchor_signature else []

    signer_tabs = None
    if text_tabs or sign_here_tabs:
        signer_tabs = Tabs(
            text_tabs=text_tabs if text_tabs else None,
            sign_here_tabs=sign_here_tabs if sign_here_tabs else None,
        )

    # Single template: use simpler templateId + templateRoles (more reliable than composite)
    # Multiple templates: use composite_templates
    use_composite = include_nda and include_contract and nda_template_id and contract_template_id
    logger.info(
        "[DocuSign] Flow: %s (include_nda=%s, include_contract=%s, nda_id=%s, contract_id=%s)",
        "composite" if use_composite else "single_template",
        include_nda,
        include_contract,
        bool(nda_template_id),
        bool(contract_template_id),
    )

    if use_composite:
        # Both documents: composite templates
        from docusign_esign import (
            CompositeTemplate,
            InlineTemplate,
            Recipients,
            ServerTemplate,
            Signer,
        )

        def make_signer():
            signer = Signer(
                email=recipient_email,
                name=recipient_name or recipient_email,
                recipient_id="1",
                role_name=role_name,
            )
            if signer_tabs:
                signer.tabs = signer_tabs
            return signer

        composite_templates = [
            CompositeTemplate(
                composite_template_id="1",
                server_templates=[ServerTemplate(template_id=nda_template_id, sequence="1")],
                inline_templates=[
                    InlineTemplate(sequence="1", recipients=Recipients(signers=[make_signer()]))
                ],
            ),
            CompositeTemplate(
                composite_template_id="2",
                server_templates=[ServerTemplate(template_id=contract_template_id, sequence="2")],
                inline_templates=[
                    InlineTemplate(sequence="2", recipients=Recipients(signers=[make_signer()]))
                ],
            ),
        ]
        envelope_definition = EnvelopeDefinition(
            email_subject="Please sign your agreement",
            email_blurb="Please review and sign the attached document(s).",
            composite_templates=composite_templates,
            status="sent",
        )
        logger.info(
            "[DocuSign] Built composite envelope: nda_template_id=%s, contract_template_id=%s, role_name=%s",
            nda_template_id,
            contract_template_id,
            role_name,
        )
    else:
        # Single template: use templateId + templateRoles
        from docusign_esign import TemplateRole

        template_id = nda_template_id if include_nda else contract_template_id
        template_role = TemplateRole(
            email=recipient_email,
            name=recipient_name or recipient_email,
            role_name=role_name,
        )
        if signer_tabs:
            template_role.tabs = signer_tabs

        envelope_definition = EnvelopeDefinition(
            email_subject="Please sign your agreement",
            email_blurb="Please review and sign the attached document(s).",
            template_id=template_id,
            template_roles=[template_role],
            status="sent",
        )
        logger.info(
            "[DocuSign] Built single-template envelope: template_id=%s, role_name=%s, recipient_email=%s",
            template_id,
            role_name,
            recipient_email,
        )

    try:
        kwargs = {"envelope_definition": envelope_definition}
        if envelope_definition.composite_templates:
            kwargs["merge_roles_on_draft"] = "true"

        # Log request params for debugging (no sensitive data)
        req_summary = {
            "account_id": account_id,
            "api_host": getattr(api_client, "host", "?"),
            "template_id": getattr(envelope_definition, "template_id", None),
            "template_roles_count": len(envelope_definition.template_roles) if envelope_definition.template_roles else 0,
            "composite_templates_count": len(envelope_definition.composite_templates) if envelope_definition.composite_templates else 0,
            "merge_roles_on_draft": kwargs.get("merge_roles_on_draft"),
        }
        if envelope_definition.template_roles:
            req_summary["role_names"] = [tr.role_name for tr in (envelope_definition.template_roles or [])]
        if envelope_definition.composite_templates:
            req_summary["composite_template_ids"] = [
                ct.composite_template_id for ct in envelope_definition.composite_templates
            ]
            req_summary["server_template_ids"] = []
            for ct in envelope_definition.composite_templates:
                for st in (ct.server_templates or []):
                    req_summary["server_template_ids"].append(st.template_id)

        logger.info("[DocuSign] Calling create_envelope with: %s", json.dumps(req_summary, default=str))

        results = envelopes_api.create_envelope(account_id, **kwargs)
        logger.info("[DocuSign] create_envelope succeeded: envelope_id=%s", results.envelope_id)
        return {
            "success": True,
            "envelope_id": results.envelope_id,
            "status": "sent",
            "message": f"Contract sent to {recipient_email}",
        }
    except ApiException as e:
        error_body = e.body.decode("utf-8") if isinstance(e.body, bytes) else (e.body or str(e))
        err_detail = {
            "where": "EnvelopesApi.create_envelope",
            "http_status": e.status,
            "error_body": error_body,
            "account_id": account_id,
            "api_host": getattr(api_client, "host", "?"),
            "template_id": getattr(envelope_definition, "template_id", None),
            "template_roles_count": len(envelope_definition.template_roles) if envelope_definition.template_roles else 0,
            "composite_templates_count": len(envelope_definition.composite_templates) if envelope_definition.composite_templates else 0,
            "role_name": role_name,
        }
        logger.error(
            "[DocuSign] API error at create_envelope: %s",
            json.dumps(err_detail, default=str),
            exc_info=True,
        )
        print(f"❌ DocuSign API error: {e.status} - {error_body}")
        print(f"   [DocuSign] Failed at: create_envelope | account_id={account_id} | host={getattr(api_client, 'host', '?')}")
        print(f"   [DocuSign] Params: template_id={getattr(envelope_definition, 'template_id', None)} | role_name={role_name} | template_roles={len(envelope_definition.template_roles or [])} | composite_templates={len(envelope_definition.composite_templates or [])}")
        if "must specify a template" in error_body.lower():
            print(
                "   [DocuSign] TROUBLESHOOTING: This often means (1) template not shared with JWT user - "
                "DocuSign Admin → Templates → your template → Share with Users; "
                "(2) role_name must match template exactly - check template roles; "
                "(3) template must be Available, not Draft."
            )
        raise ValueError(f"DocuSign error: {error_body}") from e


def get_envelope_status(envelope_id: str) -> Dict[str, Any]:
    """
    Fetch envelope status from DocuSign for a given envelope ID.

    Args:
        envelope_id: DocuSign envelope ID

    Returns:
        Dict with status, envelope_id, and optionally recipients info.
        status: 'sent' | 'delivered' | 'completed' | 'voided' | 'declined'
    """
    api_client = _get_api_client()
    account_id = os.getenv("DOCUSIGN_ACCOUNT_ID")
    envelopes_api = EnvelopesApi(api_client)
    try:
        envelope = envelopes_api.get_envelope(account_id, envelope_id)
        status = getattr(envelope, "status", None) or "unknown"
        return {
            "envelope_id": envelope_id,
            "status": status,
            "email_subject": getattr(envelope, "email_subject", None),
        }
    except ApiException as e:
        error_body = e.body.decode("utf-8") if isinstance(e.body, bytes) else (e.body or str(e))
        logger.error("[DocuSign] get_envelope failed: %s - %s", e.status, error_body)
        raise ValueError(f"DocuSign error: {error_body}") from e


def get_docusign_config() -> Dict[str, Any]:
    """Check if DocuSign is configured. Does NOT validate credentials."""
    return {
        "configured": bool(
            os.getenv("DOCUSIGN_INTEGRATION_KEY")
            and os.getenv("DOCUSIGN_USER_ID")
            and os.getenv("DOCUSIGN_ACCOUNT_ID")
        ),
        "nda_template_configured": bool(os.getenv("DOCUSIGN_NDA_TEMPLATE_ID", "").strip()),
        "contract_template_configured": bool(os.getenv("DOCUSIGN_CONTRACT_TEMPLATE_ID", "").strip()),
        "anchor_strings": {
            "document_date": os.getenv("DOCUSIGN_ANCHOR_DOCUMENT_DATE", "[DocumentDate]").strip(),
            "candidate_name": os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_NAME", "[CandidateName]").strip(),
            "candidate_email": os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_EMAIL", "[CandidateEmail]").strip(),
            "candidate_phone": os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_PHONE", "[CandidatePhone]").strip(),
            "candidate_address": os.getenv("DOCUSIGN_ANCHOR_CANDIDATE_ADDRESS", "[CandidateAddress]").strip(),
            "signature": os.getenv("DOCUSIGN_ANCHOR_SIGNATURE", "**signature**").strip(),
        },
        "template_role_name": os.getenv("DOCUSIGN_TEMPLATE_ROLE_NAME", "Signer").strip(),
    }
