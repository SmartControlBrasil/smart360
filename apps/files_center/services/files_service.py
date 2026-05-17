import hashlib

from django.db import transaction

from ..models import FileAccessLog, FileLink, StoredFile


class FileChecksumService:
    @staticmethod
    def generate(*, uploaded_file):
        if not uploaded_file:
            return ""
        hasher = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            hasher.update(chunk)
        uploaded_file.seek(0)
        return hasher.hexdigest()


class FileAccessLogService:
    @staticmethod
    def log(*, stored_file, action_type, accessed_by=None, ip_address="", user_agent=""):
        return FileAccessLog.objects.create(
            stored_file=stored_file,
            action_type=action_type,
            accessed_by=accessed_by,
            ip_address=ip_address,
            user_agent=user_agent,
        )


class StoredFileService:
    @staticmethod
    @transaction.atomic
    def create_file(**validated_data):
        uploaded_file = validated_data.get("file")
        if uploaded_file and not validated_data.get("checksum"):
            validated_data["checksum"] = FileChecksumService.generate(uploaded_file=uploaded_file)
        stored_file = StoredFile.objects.create(**validated_data)
        FileAccessLogService.log(
            stored_file=stored_file,
            action_type=FileAccessLog.ActionType.UPLOADED,
            accessed_by=stored_file.uploaded_by,
        )
        return stored_file


class FileLinkService:
    @staticmethod
    @transaction.atomic
    def create_link(**validated_data):
        link = FileLink.objects.create(**validated_data)
        FileAccessLogService.log(
            stored_file=link.stored_file,
            action_type=FileAccessLog.ActionType.LINKED,
        )
        return link

