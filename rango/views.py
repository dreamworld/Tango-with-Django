from datetime import datetime
import urllib

from django.shortcuts import render
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.decorators import login_required


from rango.models import Category, Page, UserProfile
from rango.forms import CategoryForm, PageForm
from rango.forms import UserForm, UserProfileForm
from rango.bing_search import run_query

# helper functions to convert between category name and url
def encode_url(category_name):
    return category_name.replace(' ', '_')

def decode_url(url_name):
    return url_name.replace('_', ' ')

def get_category_list(max_results=0, starts_with=''):
    cat_list = None
    try:
        if (max_results==0):
            cat_list = Category.objects.filter(name__startswith=starts_with).order_by('-likes')
        elif (max_results>0):
            cat_list = Category.objects.filter(name__startswith=starts_with).order_by('-likes')[:max_results]
    except Category.DoesNotExist:
        pass
    
    for category in cat_list:
        category.url = encode_url(category.name)
        
    return cat_list

    
def index(request):
    
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)

    # sort by the number of likes in descending order, inclusion of '-'
    category_list = Category.objects.order_by('-likes')[:5]
    page_list = Page.objects.order_by('-views')[:5]
    
    
    context_dict = {'categories': category_list}
    context_dict['pages'] = page_list
    context_dict['cat_list'] = get_category_list()
    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    for category in category_list:
        category.url = encode_url(category.name)
    
    if request.session.get('last_visit'):
        last_visit = request.session.get('last_visit')
        visits = request.session.get('visits', 0)
        
        
        last_visit_time = datetime.strptime(last_visit[:-7], "%Y-%m-%d %H:%M:%S")
        
        if (datetime.now() - last_visit_time).seconds > 5:
            request.session['last_visit'] = str(datetime.now())
            request.session['visits'] = visits + 1
            
    else:
        request.session['last_visit'] = str( datetime.now())
        request.session['visits'] = 1
    
     
    return render_to_response('rango/index.html', context_dict, context)

def category(request, category_name_url):
    
    context = RequestContext(request)
    category_name = decode_url(category_name_url)

    # search function    
    result_list = []
    if request.method == 'POST':
        query = request.POST['query'].strip()
        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)
    
    context_dict = {}
    
    try:
        category = Category.objects.get(name__exact=category_name)
        pages = Page.objects.filter(category=category)
        
        
        context_dict['pages'] = pages
        context_dict['category'] = category
        context_dict['category_name'] = category.name
        context_dict['category_name_url'] = category_name_url
        context_dict['cat_list'] = get_category_list()
        context_dict['search_result_list'] = result_list
    except Category.DoesNotExist:
        pass
    
    return render_to_response('rango/category.html', context_dict, context)

def add_category(request):
    # Get the context from the request.
    context = RequestContext(request)

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)

            # Now call the index() view.
            # The user will be shown the homepage.
            return index(request)
        else:
            # The supplied form contained errors - just print them to the terminal.
            print form.errors
    else:
        # If the request was not a POST, display the form to enter details.
        form = CategoryForm()

    # Bad form (or form details), no form supplied...
    # Render the form with error messages (if any).
    return render_to_response('rango/add_category.html', {'form': form}, context)

@login_required
def like_category(request):
    context = RequestContext(request)
    cat_id = None
    
    if request.method == 'GET':
        if 'category_id' in request.GET:
            cat_id = request.GET['category_id']
    
    likes = 0;
    if cat_id:
        category = None
        try:
            category = Category.objects.get(pk=cat_id)
        except Category.DoesNotExist:
            pass
        if category:
            likes = category.likes + 1;
            category.likes = likes
            category.save()
    
    return HttpResponse(likes) 

def add_page(request, category_name_url):
    
    context = RequestContext(request)
    category_name = decode_url(category_name_url)
    
    if request.method == 'POST':
        form = PageForm(request.POST)
        # assert validation
        if form.is_valid():
            page = form.save(commit=False)
            
            try:
                cat = Category.objects.get(name__exact=category_name)
                page.category = cat
            except Category.DoesNotExist:
                return render_to_response('rango/add_category.html', {}, context)
        
            page.views = 0
            page.save()
        
            return category(request, category_name_url)
        else:
            print form.errors
    else:
        form = PageForm()
    
    return render_to_response('rango/add_page.html',
                              {'category_name_url': category_name_url,
                               'category_name': category_name,
                               'form': form
                               },
                              context)

def about(request):
    
    # Request the context of the request.
    # The context contains information such as the client's machine details, for example.
    context = RequestContext(request)
    
    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0
    context_dict={'visits': count}
    context_dict['cat_list'] = get_category_list()
    # Return a rendered response to send to the client.
    # We make use of the shortcut function to make our lives easier.
    # Note that the first parameter is the template we wish to use.
    return render_to_response('rango/about.html', context_dict, context)

def register(request):
    context = RequestContext(request)
    
    registered = False
    
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        
        # if the two forms are valid
        if user_form.is_valid() and profile_form.is_valid():
            # save the user's form to the database
            user = user_form.save(commit=False)
            
            user.set_password(user.password)
            user.save()
            
            profile = profile_form.save(commit=False)
            profile.user = user
            
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']
            
            profile.save()
            
            registered = True
        else:
            print user_form.errors, profile_form.errors
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()
        
    return render_to_response('rango/register.html',
                              {'user_form': user_form,
                               'profile_form': profile_form,
                               'registered':registered},
                              context)
    
def user_login(request):
    # Like before, obtain the context for the user's request.
    context = RequestContext(request)

    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        username = request.POST['username']
        password = request.POST['password']

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/rango/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            print "Invalid login details: {0}, {1}".format(username, password)
            return HttpResponse("Invalid login details supplied.")

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render_to_response('rango/login.html', {}, context)


@login_required
def restricted(request):
    
    return HttpResponse("Since you're logged in, you can see this text!")

# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/rango/')

def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            # Run our Bing function to get the results list!
            result_list = run_query(query)

    return render_to_response('rango/search.html', {'result_list': result_list}, context)

@login_required
def profile(request):
    context = RequestContext(request)
    user = request.user
    context_dict = {'cat_list':get_category_list()}
    # add additional information to 'user' object
    if user.is_authenticated():
        
        try:
            userProfile = UserProfile.objects.get(user=user)
            user.website = userProfile.website
            user.picture = userProfile.picture
        except UserProfile.DoesNotExist:
            user.website = None
            user.picture = None



    return render_to_response('rango/profile.html', context_dict, context)
          
def track_url(request):
    redirect_url = '/rango/'
    page_id = None
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
                
            try:
                page = Page.objects.get(pk=page_id)                
                redirect_url = page.url
                page.views += 1  # add 1 to field `views` in Page model
                page.save()
            except Page.DoesNotExist:
                pass
    return HttpResponseRedirect(redirect_url)

      
def suggest_category(request):
    context = RequestContext(request)
    
    max_results=8
    starts_with=''
    
    if request.method == 'GET':
        if 'starts_with' in request.GET:
            starts_with = request.GET['starts_with']
    
    if starts_with == '':
        max_results = 0 #if query with null string, then return all the categories
    

    category_list = get_category_list(max_results, starts_with)
    context_dict = {'cat_list': category_list}
    
    return render_to_response('rango/category_list.html', context_dict, context)

def auto_add_page(request):
    context = RequestContext(request)
    title = None
    url = None
    cat_id = None
    context_dict={}
    if request.method == 'GET':
        if 'title' in request.GET:
            title = urllib.unquote(request.GET['title']) # unquote the parameters in url
        if 'url' in request.GET:
            url = urllib.unquote(request.GET['url'])
        if 'catid' in request.GET:
            cat_id = int(request.GET['catid'])
        
        try:
            category = Category.objects.get(pk=cat_id)
            page = Page.objects.create(category=category, title=title, url=url)
            pages = Page.objects.filter(category=category).order_by('-views')
            context_dict['pages'] = pages
        except Category.DoesNotExist:
            pass
            
    return render_to_response('rango/page_list.html', context_dict, context )
    
    
    
