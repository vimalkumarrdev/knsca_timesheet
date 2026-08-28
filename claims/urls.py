from django.urls import path

from . import views

app_name = "claims"

urlpatterns = [
    path("", views.MyClaimsView.as_view(), name="my_claims"),
    path("view/", views.ViewClaimsView.as_view(), name="view_claims"),
    path("review/", views.ClaimReviewView.as_view(), name="review"),
    path("review/export/", views.ClaimExportView.as_view(), name="review_export"),
    path("review/export/<int:user_id>/", views.ClaimReviewEmployeeExportView.as_view(), name="review_employee_export"),
    path("review/bulk-approve/", views.ClaimReviewBulkApproveView.as_view(), name="review_bulk_approve"),
    path("review/<int:pk>/<str:action>/", views.ClaimReviewActionView.as_view(), name="review_action"),
    path("settlement/", views.ClaimSettlementView.as_view(), name="settlement"),
    path("settlement/export/", views.ClaimSettlementExportView.as_view(), name="settlement_export"),
    path("settlement/bulk-settle/", views.ClaimSettlementBulkSettleView.as_view(), name="settlement_bulk_settle"),
    path("settlement/<int:pk>/<str:action>/", views.ClaimSettleActionView.as_view(), name="settlement_action"),
    path("project-wise/", views.ProjectWiseClaimsView.as_view(), name="project_wise"),
    path("project-wise/export/", views.ProjectWiseClaimsExportView.as_view(), name="project_wise_export"),
    path("types/", views.ClaimTypeListView.as_view(), name="claim_type_list"),
    path("types/add/", views.ClaimTypeCreateView.as_view(), name="claim_type_add"),
    path("types/<int:pk>/edit/", views.ClaimTypeUpdateView.as_view(), name="claim_type_edit"),
    path("types/<int:pk>/toggle/", views.ClaimTypeToggleView.as_view(), name="claim_type_toggle"),
]
