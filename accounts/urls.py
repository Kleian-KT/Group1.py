from django.urls import path
from accounts import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('login-redirect/', views.login_redirect_view, name='login_redirect'),
    path('portal/profile/', views.profile_view, name='user_profile'),
    
    # A1 — User Management
    path('manage/users/', views.admin_user_list, name='admin_user_list'),
    path('manage/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('manage/users/<int:user_id>/toggle-status/', views.admin_user_toggle_status, name='admin_user_toggle_status'),
]
