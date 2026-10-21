from .crud import GroupCrud

app_name = "groups"
urlpatterns = GroupCrud.urls()
