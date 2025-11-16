from django.urls import path
from lifeapp import views

urlpatterns = [
    path("",views.index, name="index"),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    # Backwards-compatibility alias: some templates/apps reference 'signup_view'
    path("signup/", views.signup_view, name="signup_view"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("create_profile/", views.create_profile, name="create_profile"),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path("logout/", views.logout_view, name="logout"),
    path("add_log/", views.add_health_log, name="add_health_log"),
    path("view_logs/", views.view_logs, name="view_logs"),
    path("logs/edit/<int:log_id>/", views.edit_health_log, name="edit_health_log"),
    path("logs/delete/<int:log_id>/", views.delete_health_log, name="delete_health_log"),
    path("manage_goals/", views.manage_goals, name="manage_goals"),
    path("recommendations/", views.view_recommendations, name="view_recommendations"),
    path("recommendations/regenerate/", views.regenerate_recommendations, name="regenerate_recommendations"),
    path("nutrition/", views.nutrition_tracking, name="nutrition_tracking"),
    path("nutrition/delete/<int:entry_id>/", views.delete_nutrition_entry, name="delete_nutrition_entry"),
    path('nutrition/edit/<int:entry_id>/', views.edit_nutrition_entry, name='edit_nutrition_entry'),
    path('password-reset/', views.custom_password_reset, name='custom_password_reset'),
]
