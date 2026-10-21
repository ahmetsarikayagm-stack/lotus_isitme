from .views import DeviceModelCrud

app_name = "models_app"
urlpatterns = DeviceModelCrud.urls()
