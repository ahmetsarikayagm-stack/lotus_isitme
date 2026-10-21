from .views import BankCrud

app_name = "banks"
urlpatterns = BankCrud.urls()
