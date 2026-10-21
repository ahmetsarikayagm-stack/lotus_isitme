from .crud import UserCrud

app_name = "users"
urlpatterns = UserCrud.urls()
