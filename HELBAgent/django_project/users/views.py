from django.shortcuts import render, redirect# redirect 
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from blog.models import Post
from django.contrib.auth.models import User
from django.conf import settings

#messages.debug
#messages.info
#messages.success
#msg.warning
#"".error

#Constantes
LOG_SEPARATOR = '|||'

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Your accunt has been created! You are now able to log in {username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html',{'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, 
                                   request.FILES, 
                                   instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, f'Your accunt has been updated! ')
            return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    
    # récupération des agents
    agent_list = Post.objects.all()
    
    # listes pour graph A
    agent_names_chart = []
    agent_counts_chart = []
    
    
    all_extracted_dates = []

    # parcours des agents et des messages
    for agent in agent_list:
        if agent.messages:
            message_history = agent.messages.split(LOG_SEPARATOR)
            
            # compteur pour cet agent
            current_agent_msg_count = 0
            
            for raw_message in message_history:
                clean_message = raw_message.strip()
                
                if clean_message.startswith(request.user.username):
                    current_agent_msg_count += 1
                    
                    idx = clean_message.find(" (")
                    if idx > 0:
                        start = idx + 2
                        end = clean_message.find(")", start)
                        if end > start:
                            full_timestamp = clean_message[start:end]
                            #pour seulement prendre les dates et non les heures (ancien post)
                            if len(full_timestamp) >= 10 and full_timestamp[:2] == "20":
                                date_str = full_timestamp[:10]
                                all_extracted_dates.append(date_str)
            
            # ajout aux stats si msg trouvées
            if current_agent_msg_count > 0:
                agent_names_chart.append(agent.title)
                agent_counts_chart.append(current_agent_msg_count)

    #comptage des dates 
    date_counts_map = {}
    
    for date_str in all_extracted_dates:
        if date_str in date_counts_map:
            date_counts_map[date_str] += 1
        else:
            date_counts_map[date_str] = 1
            
    #tri pour le graph B
    sorted_date_labels = sorted(date_counts_map.keys())
    sorted_date_counts = []


    
    for date_key in sorted_date_labels:
        sorted_date_counts.append(date_counts_map[date_key])
    

    context = {
        'u_form':u_form,
        'p_form':p_form,
        
        
        #new pour le graph
        'agent_names': agent_names_chart,
        'agent_counts': agent_counts_chart,
        'dates_labels': sorted_date_labels,
        'dates_counts': sorted_date_counts
    }
    
    return render(request, 'users/profile.html',context)

def public_profile(request, username):
    #recup de l'utilisateur 
    target_user = User.objects.filter(username=username).first()

    #si l'utilisateur n'existe pas on redirige
    if target_user is None:
        messages.error(request, f"The user {username} does not exist.")
        return redirect('blog-home')

    #Récupération des agents
    agent_list = Post.objects.all()
    
    # listes pour le graph A
    agent_names_chart = []
    agent_counts_chart = []

    
    for agent in agent_list:
        if agent.messages:
            message_history = agent.messages.split(LOG_SEPARATOR)
            current_agent_msg_count = 0
            
            for raw_message in message_history:
                clean_message = raw_message.strip()
                
                
                if clean_message.startswith(target_user.username):
                    current_agent_msg_count += 1
                    
            
            if current_agent_msg_count > 0:
                agent_names_chart.append(agent.title)
                agent_counts_chart.append(current_agent_msg_count)

    #Envoi au template 
    context = {
        'target_user': target_user,  
        'agent_names': agent_names_chart,
        'agent_counts': agent_counts_chart
    }
    
    return render(request, 'users/profile_public.html', context)


