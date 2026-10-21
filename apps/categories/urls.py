from .views import CategoryCrud

app_name = "categories"
urlpatterns = CategoryCrud.urls()
