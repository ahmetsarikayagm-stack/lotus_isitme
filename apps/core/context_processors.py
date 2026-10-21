from .company import company_info


def company(request):
    """Şablonlarda {{ company.name }}, {{ company.address }}, {{ company.phone }}, {{ company.email }}."""
    return {"company": company_info()}
