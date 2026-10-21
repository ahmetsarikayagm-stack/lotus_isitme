from .views import StockCrud

app_name = "stocks"
urlpatterns = StockCrud.urls()
