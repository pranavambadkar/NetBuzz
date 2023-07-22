from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .models import *
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
import json


def index(request):
    all_posts = Post.objects.all().order_by('-date_created')
    paginator = Paginator(all_posts, 10)
    page_number = request.GET.get('page')

    if page_number == None:
        page_number = 1
    
    posts = paginator.get_page(page_number)
    followings = []
    suggestions = []

    if request.user.is_authenticated:
        followings = Follower.objects.filter(followers = request.user).values_list('user', flat = True)
        suggestions = User.objects.exclude(pk__in=followings).exclude(username=request.user.username).order_by("?")[:6]
    return render(request, "index.html", {
        "posts" : posts,
        "suggestions" : suggestions,
        "page" : "all_posts",
        "profile" : False
    })


def ulogin(request):
    if request.user.is_authenticated:
        return redirect("index")
    else:
        if request.method == "POST":
            username = request.POST["username"]
            password = request.POST["password"]
            user = authenticate(request, username=username, password=password)

            # Check authentication
            if user is not None:
                login(request, user)
                return HttpResponseRedirect(reverse("index"))
            else:
                return render(request, 'ulogin.html', {"message" : "Invalid username or password."})
        else:
            return render(request, "ulogin.html")
    

def ulogout(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def usignup(request):
    if request.user.is_authenticated:
        return redirect("index")
    else:
        if request.method == "POST":
            username = request.POST["username"]
            email = request.POST["email"]
            fname = request.POST["firstname"]
            lname = request.POST["lastname"]
            profile = request.FILES.get("profile")
            print(f"--------------------------Profile: {profile}----------------------------")
            cover = request.FILES.get('cover')
            print(f"--------------------------Cover: {cover}----------------------------")

            # Password confirmation
            password = request.POST["password"]
            confirmation = request.POST["confirmation"]
            if password != confirmation:
                return render(request, "usignup.html", {"message" : "Failed, Password did not match."})
    
            # Create new user
            try:
                user = User.objects.create_user(username, email, password)
                user.first_name = fname
                user.last_name = lname

                if profile is not None:
                    user.profile_pic = profile
                else:
                    user.profile_pic = "profile_pic/no_pic.png"
                user.cover = cover
                user.save()
                Follower.objects.create(user=user)
            except IntegrityError:
                return render(request, "usignup.html", {"message" : "Username already registered."})
            login(request, user)
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "usignup.html")
    
# Profile function
def profile(request, username):
    user = User.objects.get(username=username)
    all_posts = Post.objects.filter(creater=user).order_by('-date_created')
    paginator = Paginator(all_posts, 10)
    page_number = request.GET.get('page')

    if page_number == None:
        page_number = 1
    posts = paginator.get_page(page_number)
    followings = []
    suggestions = []
    follower = False

    if request.user.is_authenticated:
        followings = Follower.objects.filter(followers=request.user).values_list('user', flat=True)
        suggestions = User.objects.exclude(pk__in=followings).exclude(username=request.user.username).order_by("?")[:6]

        if request.user in Follower.objects.get(user=user).followers.all():
            follower = True
    
    follower_count = Follower.objects.get(user=user).followers.all().count()
    following_count = Follower.objects.filter(followers=user).count()

    return render(request, 'profile.html', {
        "username": user,
        "posts": posts,
        "posts_count": all_posts.count(),
        "suggestions": suggestions,
        "page": "profile",
        "is_follower": follower,
        "follower_count": follower_count,
        "following_count": following_count
    })

    

# Function for following page
def following(request):
    if request.user.is_authenticated:
        following_user = Follower.objects.filter(followers = request.user).values('user')
        all_posts = Post.objects.filter(creater__in=following_user).order_by('-date_created')
        paginator = Paginator(all_posts, 10)
        page_number = request.GET.get('page')

        if page_number == None:
            page_number = 1
        
        posts = paginator.get_page(page_number)
        followings = Follower.objects.filter(followers = request.user).values_list('user', flat = True)
        suggestions = User.objects.exclude(pk__in = followings).exclude(username = request.user.username).order_by("?")[:6]
        return render(request, "index.html", {
            "posts" : posts,
            "suggestions" : suggestions,
            "page" : "following"
        })
    else:
        return HttpResponseRedirect(reverse('ulogin'))
    

# Function for saved page
def saved(request):
    if request.user.is_authenticated:
        all_posts = Post.objects.filter(savers=request.user).order_by('-date_created')

        paginator = Paginator(all_posts, 10)
        page_number = request.GET.get('page')
        if page_number == None:
            page_number = 1
        posts = paginator.get_page(page_number)

        followings = Follower.objects.filter(followers=request.user).values_list('user', flat=True)
        suggestions = User.objects.exclude(pk__in=followings).exclude(username=request.user.username).order_by("?")[:6]
        return render(request, "index.html", {
            "posts": posts,
            "suggestions": suggestions,
            "page": "saved"
        })
    else:
        return HttpResponseRedirect(reverse('ulogin'))
    

# Function to create a post
@login_required
def create_post(request):
    if request.method == 'POST':
        text = request.POST.get('text')
        pic = request.FILES.get('picture')
        try:
            post = Post.objects.create(creater=request.user, content_text=text, content_image=pic)
            return HttpResponseRedirect(reverse('index'))
        except Exception as e:
            return HttpResponse(e)
    else:
        return HttpResponse("Method must be 'POST'")
    

# Function to edit the post
@login_required
@csrf_exempt
def edit_post(request, post_id):
    if request.method == 'POST':
        text = request.POST.get('text')
        pic = request.FILES.get('picture')
        img_chg = request.POST.get('img_change')
        post_id = request.POST.get('id')
        post = Post.objects.get(id = post_id)
        try:
            post.content_text = text
            if img_chg != 'false':
                post.content_image = pic
            post.save()

            if(post.content_text):
                post_text = post.content_text
            else:
                post_text = False
            
            if(post.context_image):
                post_image = post.img_url()
            else:
                post_image = False
            
            return JsonResponse({
                "success" : True,
                "text" : post_text,
                "picture" :post_image
            })
        except Exception as e:
            print('-----------------------------------------------')
            print(e)
            print('-----------------------------------------------')
            return JsonResponse({
                "success": False
            })
    else:
            return HttpResponse("Method must be 'POST'")
    


# Function to like the post
@csrf_exempt
def like_post(request, id):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            post = Post.objects.get(pk=id)
            try:
                post.likers.add(request.user)
                post.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))
    

# Function to unlike the post
@csrf_exempt
def unlike_post(request, id):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            post = Post.objects.get(pk=id)
            try:
                post.likers.remove(request.user)
                post.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))
    


# Function to save post
@csrf_exempt
def save_post(request, id):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            post = Post.objects.get(pk=id)
            try:
                post.savers.add(request.user)
                post.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))


# Function to unsave the post
@csrf_exempt
def unsave_post(request, id):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            post = Post.objects.get(pk=id)
            try:
                post.savers.remove(request.user)
                post.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))


# Follow function
@csrf_exempt
def follow(request, username):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            user = User.objects.get(username = username)
            try:
                (follower, create) = Follower.objects.get_or_create(user = user)
                follower.followers.add(request.user)
                follower.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))


# Unfollow function
@csrf_exempt
def unfollow(request, username):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            user = User.objects.get(username = username)
            try:
                (follower, create) = Follower.objects.get_or_create(user = user)
                follower.followers.remove(request.user)
                follower.save()
                return HttpResponse(status = 204)
            except Exception as e:
                return HttpResponse(e)
        else:
            HttpResponse("Method must be 'PUT'")
    else:
        HttpResponseRedirect(reverse('ulogin'))


# Comment function
@csrf_exempt
def comment(request, post_id):
    if request.user.is_authenticated:
        if request.method == 'POST':
            data = json.loads(request.body)
            comment = data.get('comment_text')
            post = Post.objects.get(id = post_id)
            try:
                new_comment = Comment.objects.create(post = post, commenter = request.user, comment_content = comment)
                post.comment_count += 1
                post.save()
                return JsonResponse([new_comment.serialize()], safe=False, status=201)
            except Exception as e:
                return HttpResponse(e)
        
        post = Post.objects.get(id = post_id)
        comments = Comment.objects.filter(post = post)
        comments = comments.order_by('-comment_time').all()
        return JsonResponse([comment.serialize() for comment in comments], safe=False)
    else:
        return HttpResponseRedirect(reverse('ulogin'))
    

# Function for Delete Post
@csrf_exempt
def delete_post(request, post_id):
    if request.user.is_authenticated:
        if request.method == 'PUT':
            post = Post.objects.get(id = post_id)
            if request.user == post.creater:
                try:
                    delet = post.delete()
                    return HttpResponse(status = 201)
                except Exception as e:
                    return HttpResponse(e)
            else:
                return HttpResponse(status = 404)
        else:
            return HttpResponse("Method must be 'PUT'")
    else:
        return HttpResponseRedirect(reverse('ulogin'))