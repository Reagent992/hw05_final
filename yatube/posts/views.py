from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_page

from yatube.settings import POSTS_PER_PAGE
from .forms import PostForm, CommentForm
from .models import Group, Post, User, Follow


def get_paginated_page(request, queryset):
    """Пагинатор, выводит по 10 постов на странице."""
    paginator = Paginator(queryset, POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


@cache_page(20, key_prefix='index_page')
def index(request):
    """Главная страница."""
    posts = Post.objects.all().select_related('author', 'group')
    page_obj = get_paginated_page(request, posts)

    template = 'posts/index.html'

    context = {
        'title': 'Последние обновления на сайте',
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    """Группы постов."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all().select_related('author')
    page_obj = get_paginated_page(request, posts)

    template = 'posts/group_list.html'

    context = {
        'group': group,
        'posts': posts,
        'title': f'Посты группы {group.title}',
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    """Профиль пользователя."""
    user = get_object_or_404(User, username=username)
    user_posts = user.posts.all().select_related('author', 'group')
    page_obj = get_paginated_page(request, user_posts)

    # Проверка на авторизацию.
    if request.user.is_authenticated:
        # Проверка на подписку.
        following_check = Follow.objects.filter(author=user, user=request.user)
        following = following_check.exists()
    else:
        following = False

    template = 'posts/profile.html'

    context = {
        'title': f'Профайл пользователя: {user.first_name} '
                 f'{user.last_name}',
        'page_obj': page_obj,
        'author': user,
        'following': following,
    }
    return render(request, template, context)


def post_detail(request, post_id):
    """Подробнее о посте."""
    post = get_object_or_404(
        Post.objects.select_related('author', 'group'), id=post_id
    )
    form = CommentForm(request.POST or None)
    comments = post.comments.all()

    template = 'posts/post_detail.html'

    context = {
        'title': post.text[:30],
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, template, context)


@login_required
def add_comment(request, post_id):
    """Добавление комментария."""
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def post_create(request):
    """Отправка поста."""
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )

    if form.is_valid():
        new_post = form.save(commit=False)
        new_post.author = request.user
        new_post.save()
        return redirect('posts:profile', username=new_post.author)

    template = 'posts/create_post.html'

    context = {
        'title': 'Добавить запись',
        'form': form,
    }
    return render(request, template, context)


@login_required
def post_edit(request, post_id):
    """Редактирование поста."""
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        return redirect('posts:post_detail', post_id=post.id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )

    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post.id)

    template = 'posts/create_post.html'

    context = {
        'title': 'Редактировать запись',
        'is_edit': True,
        'form': form,
        'post': post,
    }
    return render(request, template, context)


@login_required
def follow_index(request):
    """Персональная лента."""

    # Получаем id авторов, на которых подписан пользователь.
    followed_authors = Follow.objects \
        .filter(user_id=request.user.id) \
        .values_list('author_id')

    # Получаем посты этих авторов,
    # author, и group нужны в карточке поста.
    post_list = Post.objects.filter(author__in=followed_authors) \
        .select_related('author', 'group')

    page_obj = get_paginated_page(request, post_list)

    context = {
        'title': 'Персональная лента',
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    """Кнопка Подписаться"""
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username=author.username)


@login_required
def profile_unfollow(request, username):
    """Кнопка Отписаться"""
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=author.username)
