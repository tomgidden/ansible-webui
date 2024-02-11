from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from rest_framework.generics import GenericAPIView
from rest_framework import serializers
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse

from aw.model.job import Job
from aw.model.job_credential import JobGlobalCredentials
from aw.model.job_permission import JobPermission, JobPermissionMapping, JobPermissionMemberUser, \
    JobPermissionMemberGroup, JobCredentialsPermissionMapping
from aw.api_endpoints.base import API_PERMISSION, GenericResponse, get_api_user
from aw.utils.permission import get_permission_name
from aw.utils.util import is_set

# pylint: disable=E1101


class PermissionReadResponse(serializers.ModelSerializer):
    class Meta:
        model = JobPermission
        fields = JobPermission.api_fields_read

    permission_name = serializers.CharField(required=False)
    jobs = serializers.ListSerializer(child=serializers.IntegerField(), required=False)
    credentials = serializers.ListSerializer(child=serializers.IntegerField(), required=False)
    users_name = serializers.ListSerializer(child=serializers.CharField(), required=False)
    groups_name = serializers.ListSerializer(child=serializers.CharField(), required=False)
    jobs_name = serializers.ListSerializer(child=serializers.CharField(), required=False)
    credentials_name = serializers.ListSerializer(child=serializers.CharField(), required=False)


class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job


class PermissionWriteRequest(serializers.ModelSerializer):
    class Meta:
        model = JobPermission
        fields = JobPermission.api_fields_write

    jobs = serializers.MultipleChoiceField(allow_blank=True, choices=[])
    credentials = serializers.MultipleChoiceField(allow_blank=True, choices=[])
    users = serializers.MultipleChoiceField(allow_blank=True, choices=[])
    groups = serializers.MultipleChoiceField(allow_blank=True, choices=[])

    def __init__(self, *args, **kwargs):
        # pylint: disable=E1101
        super().__init__(*args, **kwargs)
        self.fields['jobs'] = serializers.MultipleChoiceField(choices=[job.id for job in Job.objects.all()])
        self.fields['credentials'] = serializers.MultipleChoiceField(
            choices=[creds.id for creds in JobGlobalCredentials.objects.all()]
        )
        self.fields['users'] = serializers.MultipleChoiceField(choices=[user.id for user in User.objects.all()])
        self.fields['groups'] = serializers.MultipleChoiceField(choices=[group.id for group in Group.objects.all()])

    @staticmethod
    def create_or_update(validated_data: dict, perm: JobPermission = None):
        if perm is None:
            perm = JobPermission(
                name=validated_data['name'],
                permission=validated_data['permission'],
            )

        else:
            perm.name = validated_data['name']
            perm.permission = validated_data['permission']

        perm.save()

        if 'jobs' in validated_data and is_set(validated_data['jobs']):
            jobs = []
            for job_id in validated_data['jobs']:
                try:
                    jobs.append(Job.objects.get(id=job_id))

                except ObjectDoesNotExist:
                    continue

            perm.jobs.set(jobs)

        if 'credentials' in validated_data and is_set(validated_data['credentials']):
            credentials = []
            for creds_id in validated_data['credentials']:
                try:
                    credentials.append(JobGlobalCredentials.objects.get(id=creds_id))

                except ObjectDoesNotExist:
                    continue

            perm.credentials.set(credentials)

        if 'users' in validated_data and is_set(validated_data['users']):
            users = []
            for user_id in validated_data['users']:
                try:
                    users.append(User.objects.get(id=user_id))

                except ObjectDoesNotExist:
                    continue

            perm.users.set(users)

        if 'groups' in validated_data and is_set(validated_data['groups']):
            groups = []
            for group_id in validated_data['groups']:
                try:
                    groups.append(Group.objects.get(id=group_id))

                except ObjectDoesNotExist:
                    continue

            perm.groups.set(groups)

        perm.save()


def build_permissions(perm_id_filter: int = None) -> (list, dict):
    permissions_raw = JobPermission.objects.all()
    permission_jobs_id = {permission.id: [] for permission in permissions_raw}
    permission_jobs_name = {permission.id: [] for permission in permissions_raw}
    permission_credentials_id = {permission.id: [] for permission in permissions_raw}
    permission_credentials_name = {permission.id: [] for permission in permissions_raw}
    permission_users_id = {permission.id: [] for permission in permissions_raw}
    permission_users_name = {permission.id: [] for permission in permissions_raw}
    permission_groups_id = {permission.id: [] for permission in permissions_raw}
    permission_groups_name = {permission.id: [] for permission in permissions_raw}

    for mapping in JobPermissionMapping.objects.all():
        permission_jobs_id[mapping.permission.id].append(mapping.job.id)
        permission_jobs_name[mapping.permission.id].append(mapping.job.name)

    for mapping in JobCredentialsPermissionMapping.objects.all():
        permission_credentials_id[mapping.permission.id].append(mapping.credentials.id)
        permission_credentials_name[mapping.permission.id].append(mapping.credentials.name)

    for mapping in JobPermissionMemberUser.objects.all():
        permission_users_id[mapping.permission.id].append(mapping.user.id)
        permission_users_name[mapping.permission.id].append(mapping.user.username)

    for mapping in JobPermissionMemberGroup.objects.all():
        permission_groups_id[mapping.permission.id].append(mapping.group.id)
        permission_groups_name[mapping.permission.id].append(mapping.group.name)

    permissions = []

    for permission in permissions_raw:
        if perm_id_filter is not None:
            if perm_id_filter != permission.id:
                continue

        permissions.append({
            'id': permission.id,
            'name': permission.name,
            'permission': permission.permission,
            'permission_name': get_permission_name(permission.permission),
            'jobs': permission_jobs_id[permission.id],
            'credentials': permission_credentials_id[permission.id],
            'users': permission_users_id[permission.id],
            'groups': permission_groups_id[permission.id],
            'jobs_name': permission_jobs_name[permission.id],
            'credentials_name': permission_credentials_name[permission.id],
            'users_name': permission_users_name[permission.id],
            'groups_name': permission_groups_name[permission.id],
        })

    try:
        if perm_id_filter is not None:
            return permissions[0]

    except IndexError:
        return {}

    return permissions


def has_permission_privileges(user: settings.AUTH_USER_MODEL) -> bool:
    # todo: create explicit privilege
    return user.is_staff


class APIPermission(GenericAPIView):
    http_method_names = ['get', 'post']
    serializer_class = PermissionReadResponse
    permission_classes = API_PERMISSION

    @staticmethod
    @extend_schema(
        request=None,
        responses={200: PermissionReadResponse},
        summary='Return list of permissions',
        operation_id='permission_list',
    )
    def get(request):
        del request
        return Response(build_permissions())

    @extend_schema(
        request=PermissionWriteRequest,
        responses={
            200: OpenApiResponse(response=GenericResponse, description='Permission created'),
            400: OpenApiResponse(response=GenericResponse, description='Invalid permission data provided'),
            403: OpenApiResponse(response=GenericResponse, description='Not privileged to create a permission'),
        },
        summary='Create a new Permission.',
        operation_id='permission_create',
    )
    def post(self, request):
        privileged = has_permission_privileges(get_api_user(request))
        if not privileged:
            return Response(
                data={'msg': 'Not privileged to manage permissions'},
                status=403,
            )

        serializer = PermissionWriteRequest(data=request.data)

        if not serializer.is_valid():
            return Response(
                data={'msg': f"Provided permission data is not valid: '{serializer.errors}'"},
                status=400,
            )

        try:
            serializer.create_or_update(validated_data=serializer.validated_data, perm=None)

        except IntegrityError as err:
            return Response(
                data={'msg': f"Provided permission data is not valid: '{err}'"},
                status=400,
            )

        return Response({'msg': f"Permission '{serializer.data['name']}' created successfully"})


class APIPermissionItem(GenericAPIView):
    http_method_names = ['get', 'put', 'delete']
    serializer_class = GenericResponse
    permission_classes = API_PERMISSION

    @staticmethod
    @extend_schema(
        request=None,
        responses={200: PermissionReadResponse},
        summary='Return information of a permission.',
        operation_id='permission_get'
    )
    def get(request, perm_id: int):
        del request
        return Response(build_permissions(perm_id_filter=perm_id))

    @extend_schema(
        request=PermissionWriteRequest,
        responses={
            200: OpenApiResponse(response=GenericResponse, description='Permission updated'),
            403: OpenApiResponse(response=GenericResponse, description='Not privileged to edit the permission'),
            404: OpenApiResponse(response=GenericResponse, description='Permission does not exist'),
        },
        summary='Modify a permission.',
        operation_id='permission_edit',
    )
    def put(self, request, perm_id: int):
        privileged = has_permission_privileges(get_api_user(request))
        if not privileged:
            return Response(
                data={'msg': 'Not privileged to manage permissions'},
                status=403,
            )

        serializer = PermissionWriteRequest(data=request.data)

        if not serializer.is_valid():
            return Response(
                data={'msg': f"Provided permission data is not valid: '{serializer.errors}'"},
                status=400,
            )

        try:
            permission = JobPermission.objects.get(id=perm_id)

        except ObjectDoesNotExist:
            permission = None

        if permission is None:
            return Response(
                data={'msg': f"Permission with ID {perm_id} does not exist"},
                status=404,
            )

        try:
            serializer.create_or_update(validated_data=serializer.validated_data, perm=permission)
            return Response(data={'msg': f"Permission '{permission.name}' updated"}, status=200)

        except IntegrityError as err:
            return Response(data={'msg': f"Provided permission data is not valid: '{err}'"}, status=400)

    @extend_schema(
        request=None,
        responses={
            200: OpenApiResponse(response=GenericResponse, description='Permission deleted'),
            400: OpenApiResponse(response=GenericResponse, description='Invalid permission data provided'),
            403: OpenApiResponse(response=GenericResponse, description='Not privileged to delete the permission'),
            404: OpenApiResponse(response=GenericResponse, description='Permission does not exist'),
        },
        summary='Delete a permission.',
        operation_id='permission_delete'
    )
    def delete(self, request, perm_id: int):
        privileged = has_permission_privileges(get_api_user(request))
        if not privileged:
            return Response(
                data={'msg': 'Not privileged to manage permissions'},
                status=403,
            )

        try:
            permission = JobPermission.objects.get(id=perm_id)
            if permission is not None:
                permission.delete()
                return Response(data={'msg': f"Permission '{permission.name}' deleted"}, status=200)

        except ObjectDoesNotExist:
            pass

        return Response(data={'msg': f"Permission with ID {perm_id} does not exist"}, status=404)
