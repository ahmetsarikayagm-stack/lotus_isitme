from .permissions import build_menu


def sidebar_menu(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"sidebar_menu": build_menu(user, request.path)}
