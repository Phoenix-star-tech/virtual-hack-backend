from app.services.supabase_service import supabase_admin as supabase

def log_action(
    admin_id: str | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str = "",
):
    if not supabase:
        return
    try:
        supabase.from_("audit_logs").insert({
            "admin_id": admin_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
        }).execute()
    except Exception:
        pass
