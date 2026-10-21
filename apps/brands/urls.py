from .views import BrandCrud

app_name = "brands"
urlpatterns = BrandCrud.urls()
