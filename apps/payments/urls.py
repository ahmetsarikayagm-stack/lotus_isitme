from .views import PaymentCrud

app_name = "payments"
urlpatterns = PaymentCrud.urls()
