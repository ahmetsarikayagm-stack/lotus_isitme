"""
Rol/modül yetkilendirmesinin TEK kaynağı.

Sidebar, view mixin'leri ve decorator'lar buradaki MODULES kaydını kullanır.
Yeni sayfa eklemek için sadece bu listeye bir `Module` eklemek yeterlidir.
"""
from dataclasses import dataclass

from django.urls import NoReverseMatch, reverse

from .models import Role


@dataclass(frozen=True)
class Module:
    key: str
    label: str
    url_name: str
    icon: str
    roles: tuple
    section: str


ALL_ROLES = (Role.ADMIN, Role.SALES)
ADMIN_ONLY = (Role.ADMIN,)

SECTION_GENERAL = "Genel"
SECTION_ADMIN = "Yönetim"

MODULES: tuple[Module, ...] = (
    # --- Admin + Satış Temsilcisi ---
    Module("dashboard", "Grafikler", "dashboard:index", "chart-bar", ALL_ROLES, SECTION_GENERAL),
    Module("patients", "Hastalar", "patients:list", "users", ALL_ROLES, SECTION_GENERAL),
    Module("stocks", "Stoklar", "stocks:list", "archive-box", ALL_ROLES, SECTION_GENERAL),
    Module("sales", "Satışlar", "sales:list", "shopping-cart", ALL_ROLES, SECTION_GENERAL),
    Module("month_end", "Ay Sonu", "month_end:list", "calendar", ALL_ROLES, SECTION_GENERAL),
    # --- Sadece Admin ---
    Module("payments", "Ödemeler", "payments:list", "credit-card", ADMIN_ONLY, SECTION_ADMIN),
    Module("banks", "Bankalar", "banks:list", "building-library", ADMIN_ONLY, SECTION_ADMIN),
    Module("categories", "Kategoriler", "categories:list", "tag", ADMIN_ONLY, SECTION_ADMIN),
    Module("brands", "Markalar", "brands:list", "bookmark", ADMIN_ONLY, SECTION_ADMIN),
    Module("models", "Modeller", "models_app:list", "cube", ADMIN_ONLY, SECTION_ADMIN),
    Module("users", "Kullanıcılar", "users:list", "user-group", ADMIN_ONLY, SECTION_ADMIN),
    Module("groups", "Gruplar", "groups:list", "shield-check", ADMIN_ONLY, SECTION_ADMIN),
)

MODULE_MAP = {m.key: m for m in MODULES}


def can_access(user, module_key: str) -> bool:
    """Kullanıcı bu modüle erişebilir mi?"""
    module = MODULE_MAP.get(module_key)
    if module is None or not getattr(user, "is_authenticated", False) or not user.is_active:
        return False
    return user.is_superuser or user.role in module.roles


def _safe_url(url_name: str) -> str:
    try:
        return reverse(url_name)
    except NoReverseMatch:
        return "#"  # modül henüz geliştirilmemişse sidebar kırılmasın


def build_menu(user, current_path: str = "") -> list[dict]:
    """Kullanıcının rolüne göre bölümlere ayrılmış sidebar menüsü üretir."""
    sections: dict[str, list[dict]] = {}
    for module in MODULES:
        if not can_access(user, module.key):
            continue
        url = _safe_url(module.url_name)
        is_root = url == "/"
        active = (current_path == url) if is_root else (url != "#" and current_path.startswith(url))
        sections.setdefault(module.section, []).append(
            {"key": module.key, "label": module.label, "url": url, "icon": module.icon, "active": active}
        )
    return [{"title": title, "items": items} for title, items in sections.items()]
