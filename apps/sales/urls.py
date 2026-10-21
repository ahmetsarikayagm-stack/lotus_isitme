from .views import SaleCrud

app_name = "sales"
urlpatterns = SaleCrud.urls()
