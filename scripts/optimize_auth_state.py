"""Eliminar proxies @rx.var duplicados y renombrar cache vars en auth_state.py."""
import re

FILE = "app/states/auth_state.py"

with open(FILE, "r", encoding="utf-8") as f:
    content = f.read()

original_len = len(content)

# 1. Delete pure pass-through proxies
for name in ["available_branches", "active_branch_name"]:
    pat = (
        r"    @rx\.var\(cache=True\)\n"
        r"    def " + name + r"\(self\) -> [^:]+:\n"
        r"        return self\." + name + r"_cache\n\n?"
    )
    content, n = re.subn(pat, "", content)
    print(f"  {'✓' if n else '✗'} Deleted proxy: {name} ({n} matches)")

# 2. Delete subscription_snapshot proxy (or default)
pat = (
    r"    @rx\.var\(cache=True\)\n"
    r"    def subscription_snapshot\(self\) -> Dict\[str, Any\]:\n"
    r"        return self\.subscription_snapshot_cache or self\._default_subscription_snapshot\(\)\n\n?"
)
content, n = re.subn(pat, "", content)
print(f"  {'✓' if n else '✗'} Deleted proxy: subscription_snapshot ({n} matches)")

# 3. Delete payment_alert_info proxy (docstring + or default)
pat = (
    r'    @rx\.var\(cache=True\)\n'
    r'    def payment_alert_info\(self\) -> Dict\[str, Any\]:\n'
    r'        """[^"]*"""\n'
    r'        return self\.payment_alert_info_cache or self\._default_payment_alert_info\(\)\n\n?'
)
content, n = re.subn(pat, "", content)
print(f"  {'✓' if n else '✗'} Deleted proxy: payment_alert_info ({n} matches)")

# 4. Delete company_has_reservations proxy (bool())
pat = (
    r"    @rx\.var\(cache=True\)\n"
    r"    def company_has_reservations\(self\) -> bool:\n"
    r"        return bool\(self\.company_has_reservations_cache\)\n\n?"
)
content, n = re.subn(pat, "", content)
print(f"  {'✓' if n else '✗'} Deleted proxy: company_has_reservations ({n} matches)")

# 5. Rename cache vars
renames = [
    ("available_branches_cache", "available_branches"),
    ("active_branch_name_cache", "active_branch_name"),
    ("subscription_snapshot_cache", "subscription_snapshot"),
    ("payment_alert_info_cache", "payment_alert_info"),
    ("company_has_reservations_cache", "company_has_reservations"),
    ("plan_actual_cache", "plan_actual"),
]
total = 0
for old, new in renames:
    count = content.count(old)
    content = content.replace(old, new)
    total += count
    print(f"  ✓ Renamed '{old}' → '{new}' ({count} occurrences)")

with open(FILE, "w", encoding="utf-8") as f:
    f.write(content)

print(f"\nDone: {original_len - len(content)} chars removed, {total} renames. File saved.")
