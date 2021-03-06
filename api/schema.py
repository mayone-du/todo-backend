import asyncio

import graphene
import graphql_social_auth
from django.contrib.auth import get_user_model
from graphene import relay
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene_file_upload.scalars import Upload
from graphql_relay import from_global_id

from api.decorators import validate_token

from .models import Profile, Task, User


# ユーザー
class UserNode(DjangoObjectType):
    class Meta:
        model = User
        filter_fields = {
            'username': ['exact', 'icontains'],
            'email': ['exact', 'icontains'],
            'is_staff': ['exact'],
            'is_superuser': ['exact'],
        }
        interfaces = (relay.Node, )


# プロフィール
class ProfileNode(DjangoObjectType):
    class Meta:
        model = Profile
        filter_fields = {
            'profile_name': ['exact', 'icontains'],
            'self_introduction': ['exact', 'icontains'],
            'github_username': ['exact', 'icontains'],
            'twitter_username': ['exact', 'icontains'],
        }
        interfaces = (relay.Node, )

    # 100件を超えると一度のクエリで全て取得できない可能性があるため、先に数だけ取得出来るようにしておく
    following_users_count = graphene.Int()
    followed_users_count = graphene.Int()

    # フォローしているユーザーの人数を返す
    def resolve_following_users_count(root, info, **kwargs):
        return root.following_users.all().count()

    # フォローされているユーザーの人数を返す
    def resolve_followed_users_count(root, info, **kwargs):
        return root.related_user.following_users.all().count()


# タスク
class TaskNode(DjangoObjectType):
    class Meta:
        model = Task
        filter_fields = {'title': ['exact', 'icontains']}
        interfaces = (relay.Node, )


# プロフィールの作成
# TODO: ユーザー作成時にプロフィールも初期化するからいらないかも
class CreateProfileMutation(relay.ClientIDMutation):
    class Input:
        profile_name = graphene.String(required=True)
        profile_image = Upload(required=False)
        self_introduction = graphene.String(required=False)
        github_username = graphene.String(required=False)
        twitter_username = graphene.String(required=False)

    profile = graphene.Field(ProfileNode)

    @validate_token
    def mutate_and_get_payload(root, info, **input):
        try:
            profile_name = input.get('profile_name')
            profile_image = input.get('profile_image')
            self_introduction = input.get('self_introduction')
            github_username = input.get('github_username')
            twitter_username = input.get('twitter_username')

            my_user_id = get_user_model().objects.get(
                email=info.context.user.email).id
            profile = Profile(related_user=get_user_model().objects.get(
                id=my_user_id))

            if profile_name is not None:
                profile.profile_name = profile_name
            if profile_image != []:
                profile.profile_image = profile_image
            if self_introduction is not None:
                profile.self_introduction = self_introduction
            if github_username is not None:
                profile.github_username = github_username
            if twitter_username is not None:
                profile.twitter_username = twitter_username
            profile.save()
            return CreateProfileMutation(profile=profile)
        except:
            raise


# プロフィールの更新
class UpdateProfileMutation(relay.ClientIDMutation):
    class Input:
        profile_name = graphene.String(required=False)
        google_image_url = graphene.String()
        profile_image = Upload(required=False)
        self_introduction = graphene.String(required=False)
        github_username = graphene.String(required=False)
        twitter_username = graphene.String(required=False)
        website_url = graphene.String(required=False)
        following_users = graphene.List(graphene.ID)

    profile = graphene.Field(ProfileNode)

    @validate_token
    def mutate_and_get_payload(root, info, **input):
        try:
            profile_name = input.get('profile_name')
            google_image_url = input.get('google_image_url')
            profile_image = input.get('profile_image')
            self_introduction = input.get('self_introduction')
            github_username = input.get('github_username')
            twitter_username = input.get('twitter_username')
            following_users = input.get('following_users')

            profile_id = get_user_model().objects.get(
                email=info.context.user.email).related_user.id
            profile = Profile.objects.get(id=profile_id)

            if profile_name is not None:
                profile.profile_name = profile_name
            if google_image_url is not None:
                profile.google_image_url = google_image_url
            if profile_image != [] and profile_image is not None:
                profile.profile_image = profile_image
            if self_introduction is not None:
                profile.self_introduction = self_introduction
            if github_username is not None:
                profile.github_username = github_username
            if twitter_username is not None:
                profile.twitter_username = twitter_username

            # フォローしているユーザーを配列形式で保存
            if following_users is not None:
                followings_set = []
                for user in following_users:
                    user_id = from_global_id(user)[1]
                    user_object = get_user_model().objects.get(id=user_id)
                    followings_set.append(user_object)
                profile.following_users.set(followings_set)
            profile.save()
            return UpdateProfileMutation(profile=profile)
        except:
            raise


# タスクの作成
class CreateTaskMutation(relay.ClientIDMutation):
    class Input:
        title = graphene.String(required=True)
        content = graphene.String(required=False)
        task_image = Upload(required=False)

    task = graphene.Field(TaskNode)

    @validate_token
    def mutate_and_get_payload(root, info, **input):
        try:
            current_user = get_user_model().objects.get(
                email=info.context.user.email)
            title = input.get('title')
            # タスクのタイトルが空文字だったらエラー
            if title == '':
                raise ValueError('title is must')
            # ForeignKeyなどは、ユーザーにそのままユーザーモデルを入れるか、create_user_id = current_user.idなどとする
            task = Task(create_user=current_user,
                        title=title,
                        content="task content",
                        is_done=False)
            task.save()
            return CreateTaskMutation(task=task)
        except:
            raise


# タスクの更新
class UpdateTaskMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        title = graphene.String(required=False)
        content = graphene.String(required=False)
        is_done = graphene.Boolean(required=False)
        task_image = Upload(required=False)

    task = graphene.Field(TaskNode)

    @validate_token
    def mutate_and_get_payload(root, info, **input):
        try:
            title = input.get('title')
            content = input.get('content')
            is_done = input.get('is_done')
            task_image = input.get('task_image')
            task = Task.objects.get(id=from_global_id(input.get('id'))[1])
            if title is not None:
                task.title = title
            if content is not None:
                task.content = content
            if is_done is not None:
                task.is_done = is_done
            if task_image != [] and task_image is not None:
                task.task_image = task_image[0]
            task.save()
            return UpdateTaskMutation(task=task)
        except:
            raise


# タスクの削除
class DeleteTaskMutation(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)

    task = graphene.Field(TaskNode)

    @validate_token
    def mutate_and_get_payload(root, info, **input):
        try:
            task = Task.objects.get(id=from_global_id(input.get('id'))[1])
            task.delete()
            return DeleteTaskMutation(task=task)
        except:
            raise


# ミューテーション
class Mutation(graphene.ObjectType):
    # OAuth
    social_auth = graphql_social_auth.SocialAuth.Field()

    # プロフィール
    create_profile = CreateProfileMutation.Field()
    update_profile = UpdateProfileMutation.Field()

    # タスク
    create_task = CreateTaskMutation.Field()
    update_task = UpdateTaskMutation.Field()
    delete_task = DeleteTaskMutation.Field()


# クエリ
class Query(graphene.ObjectType):
    # ユーザー
    user = graphene.Field(UserNode, id=graphene.NonNull(graphene.ID))
    all_users = DjangoFilterConnectionField(UserNode)
    my_user_info = graphene.Field(UserNode)

    # プロフィール
    profile = graphene.Field(ProfileNode, id=graphene.NonNull(graphene.ID))
    my_profile = graphene.Field(ProfileNode)
    all_profiles = DjangoFilterConnectionField(ProfileNode)

    # タスク
    task = graphene.Field(TaskNode, id=graphene.NonNull(graphene.ID))
    my_all_tasks = DjangoFilterConnectionField(TaskNode)

    #--- リゾルバー ---#

    # ユーザーのリゾルバー
    def resolve_user(self, info, **kwargs):
        id = kwargs.get('id')
        user = get_user_model().objects.get(id=from_global_id(id)[1])
        return user

    def resolve_all_users(self, info, **kwargs):
        return get_user_model().objects.all()

    @validate_token
    def resolve_my_user_info(self, info, **kwargs):
        return get_user_model().objects.get(email=info.context.user.email)

    # プロフィールのリゾルバー
    def resolve_profile(self, info, **kwargs):
        id = kwargs.get('id')
        profile = Profile.objects.get(id=from_global_id(id)[1])
        return profile

    @validate_token
    def resolve_my_profile(self, info):
        my_user_data = get_user_model().objects.get(
            email=info.context.user.email)
        my_profile = Profile.objects.get(related_user=my_user_data)
        return my_profile

    def resolve_all_profiles(self, info, **kwargs):
        return Profile.objects.all()

    # タスクのリゾルバー
    def resolve_task(self, info, **kwargs):
        id = kwargs.get('id')
        task = Task.objects.get(id=from_global_id(id)[1])
        return task

    @validate_token
    def resolve_my_all_tasks(self, info, **kwargs):
        login_user = get_user_model().objects.get(
            email=info.context.user.email)
        my_all_tasks = Task.objects.filter(create_user=login_user)
        return my_all_tasks


# サブスクリプション
class Subscription(graphene.ObjectType):
    count_seconds = graphene.Float(up_to=graphene.Int())

    async def resolve_count_seconds(root, info, up_to):
        for i in range(up_to):
            yield i
            await asyncio.sleep(1.)
        yield up_to
