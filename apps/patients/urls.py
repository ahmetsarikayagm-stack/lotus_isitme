from .views import PatientCrud

app_name = "patients"
urlpatterns = PatientCrud.urls()
