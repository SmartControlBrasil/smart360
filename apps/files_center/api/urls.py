from rest_framework.routers import DefaultRouter

from .views import (
    FileAccessLogViewSet,
    FileCategoryViewSet,
    FileCollectionItemViewSet,
    FileCollectionViewSet,
    FileLinkViewSet,
    FileVersionViewSet,
    MediaAssetViewSet,
    StoredFileViewSet,
)

router = DefaultRouter()
router.register("categories", FileCategoryViewSet, basename="files-categories")
router.register("files", StoredFileViewSet, basename="files-files")
router.register("file-links", FileLinkViewSet, basename="files-file-links")
router.register("media-assets", MediaAssetViewSet, basename="files-media-assets")
router.register("versions", FileVersionViewSet, basename="files-versions")
router.register("access-logs", FileAccessLogViewSet, basename="files-access-logs")
router.register("collections", FileCollectionViewSet, basename="files-collections")
router.register("collection-items", FileCollectionItemViewSet, basename="files-collection-items")

urlpatterns = router.urls

