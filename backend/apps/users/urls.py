from django.urls import path
from .views import MyProfileView, UserListView, UserDetailView, ChangeUserRoleView, DeactivateUserView

urlpatterns = [
    path("me/profile/", MyProfileView.as_view(), name="my-profile"),
    path("", UserListView.as_view(), name="user-list"),
    path("<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),
    path("<uuid:user_id>/role/", ChangeUserRoleView.as_view(), name="user-change-role"),
    path("<uuid:user_id>/deactivate/", DeactivateUserView.as_view(), name="user-deactivate"),
]
