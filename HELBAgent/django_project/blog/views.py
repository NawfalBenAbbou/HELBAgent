from django.shortcuts import render,redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView
)
from .models import Post
from django.utils import timezone
import time
from django.contrib import messages
from groq import Groq
from django.conf import settings
import os
import subprocess
from django.contrib.auth.decorators import login_required
import base64
import requests
from django.http import HttpResponse

#Constantes
LOG_SEPARATOR = '|||'
HELBPLAYS_FRAME_URL = "https://helbplays2526.alwaysdata.net/frame.jpg"
HELBPLAYS_CHAT_URL = "https://helbplays2526.alwaysdata.net/chat.txt"
client = Groq(api_key=settings.GROQ_API_KEY)


def home(request):
    context = {
        'posts': Post.objects.all()
    }
    return render(request, 'blog/home.html', context)


class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'  
    context_object_name = 'posts'
    ordering = ['-last_activity']



class PostDetailView(DetailView):
    model = Post

    #fonction qui prepare les messages puis les envoie a l'html
    def get_context_data(self, **kwargs):
        # prepare les messages pour l'affichage
        context = super().get_context_data(**kwargs)
        raw_messages = self.object.messages
        
        
        clean_messages = []

        #on regarde si y a des messages avant
        if raw_messages:
            
            split_messages = raw_messages.split(LOG_SEPARATOR)
            
            
            for message in split_messages:
                
                #on ajoute seulement si y a du texte
                if message.strip() != "":
                    message_info = {
                        'content': message, 
                        'is_AgentAi': False 
                    }
                    if "(API):" in message or "(LOCAL):" in message:
                        message_info['is_AgentAi'] = True
                        cleaned_text = message.replace("(API):", "").replace("(LOCAL):", "")
                        message_info['content'] = cleaned_text
                    
                    clean_messages.append(message_info)

        context['chat_messages'] = clean_messages
        
        return context

    #fonction quand on clique sur le btn send 
    def post(self, request, *args, **kwargs):
        # gestion envoi message
        self.object = self.get_object()
        content = request.POST.get('content')#recup ce que l'user a ecrit  
        current_time = time.time()

        # si c'est la premiere fois on recupere 0
        last_time = request.session.get('last_message_time', 0)

        delay_required = self.object.cooldown 
        
        # verif cooldown
        if current_time - last_time < delay_required:
            
            # message d'avertissement à l'écran
            messages.warning(request, f"Calmdown ! The cooldown is {delay_required}s. Wait.")
            
            return redirect('post-detail', pk=self.object.pk)
            
        request.session['last_message_time'] = current_time
    
        if content:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M:%S")#recup le moment du msg
            user_message = f"{request.user.username} ({timestamp}): {content}"#on met le nom le moment et le msg

            system_instruction = self.object.prompt
            
            self.object.messages += user_message + LOG_SEPARATOR
            if self.object.type_AI == 'api':
                #model API
                try:
                    #on appelle groq ici
                    chat_completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "system", "content": system_instruction},
                                  {"role": "user", "content": content}], 
                    )
                    response_text = chat_completion.choices[0].message.content
                except Exception as e:
                    response_text = f"Erreur de connexion API : {e}"
                
                #tag (API)
                ai_message = f"{self.object.title} ({timestamp}) (API): : {response_text}"
                
            else:  
                try:
                    #model local
                    # La commande est : ollama run smollm:135m "le message de l'user"
                    full_prompt = f"System: {system_instruction}. (Be brief).\nUser: {content}\nAssistant:"
                    result = subprocess.run(
                        ["ollama", "run", "smollm:135m", full_prompt], 
                        capture_output=True, 
                        text=True,
                        encoding='utf-8' 
                    )
                    
                    response_text = result.stdout.strip()
                    
                    if not response_text and result.stderr:
                        response_text = f"Erreur : {result.stderr}"
                    elif not response_text:
                         response_text = "..."

                except Exception as e:
                    response_text = f"Erreur système : {e}"
                
                
                
                # tag (LOCAL) 
                ai_message = f"{self.object.title} ({timestamp}) (LOCAL): : {response_text}"

            #ajout du msg de l'IA
            self.object.messages += ai_message + LOG_SEPARATOR

            #sauvegarde du Post sauvegarde tout l'historique
            self.object.last_activity = timezone.now()
            self.object.save()
        
        return redirect('post-detail', pk=self.object.pk)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    fields = ['title', 'content', 'prompt', 'type_AI', 'profile_picture', 'cooldown']#creer un agent 

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    fields = ['title', 'content', 'prompt', 'type_AI', 'profile_picture', 'cooldown']#modif l'agent 

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        if self.request.user == post.author:
            return True
        return False


def about(request):
    return render(request, 'blog/about.html', {'title': 'About'})

@login_required
def helbplays(request):
    # URL 
    frame_url = HELBPLAYS_FRAME_URL
    chat_url = HELBPLAYS_CHAT_URL
    
    error_msg = None
    success_msg = None
    chat_content = "Loading chat..."
    
    # Récupération du chat
    try:
        chat_response = requests.get(chat_url, timeout=3)
        if chat_response.status_code == 200:
            chat_content = chat_response.text
        else:
            chat_content = f"Error loading chat (HTTP {chat_response.status_code})"
    except Exception as e:
        chat_content = f"Connection error: {str(e)}"
    
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        
        if message:
            
            secret_key = getattr(settings, 'HELBPLAYS_SECRET_KEY', '')
            
            if not secret_key:
                error_msg = "Secret key not configured."
            else:
                try:
                    # Encodage Base64
                    user64 = base64.b64encode(request.user.username.encode('utf-8')).decode('utf-8')
                    msg64 = base64.b64encode(message.encode('utf-8')).decode('utf-8')
                    key64 = base64.b64encode(secret_key.encode('utf-8')).decode('utf-8')
                    
                    # construction de l'URL 
                    url = f"https://helbplays2526.alwaysdata.net/chat.php?username={user64}&message={msg64}&key={key64}"
                    
                    response = requests.get(url, timeout=5)
                    
                    if response.status_code == 200:
                        success_msg = "Message sent!"
                        # Recharge le chat
                        try:
                            chat_response = requests.get(chat_url, timeout=3)
                            if chat_response.status_code == 200:
                                chat_content = chat_response.text
                        except:
                            pass
                    else:
                        error_msg = f"Server error: {response.status_code}"
                        
                except Exception as e:
                    error_msg = f"Connection error: {str(e)}"
        else:
            error_msg = "Message cannot be empty."
    
    context = {
        'frame_url': frame_url,
        'chat_content': chat_content,
        'error_msg': error_msg,
        'success_msg': success_msg
    }
    
    return render(request, 'blog/helbplays.html', context)

#fonction pour le refresh auto du chat
def helbplays_chat_poll(request):
    r = requests.get(HELBPLAYS_CHAT_URL, timeout=3)
    return HttpResponse(r.text if r.status_code == 200 else "Error loading chat")

#fonction pour le refresh auto des messages du chat
def post_chat_poll(request, pk):
    post = Post.objects.get(pk=pk)
    parts = (post.messages or "").split(LOG_SEPARATOR)
    
    html = ""
    for msg in parts:
        msg = msg.strip()
        if msg:
            is_ai = "(API):" in msg or "(LOCAL):" in msg
            if is_ai:
                msg = msg.replace("(API):", "").replace("(LOCAL):", "")
                html += f'<div class="alert alert-secondary">{msg}</div>'
            else:
                html += f'<div class="alert alert-primary text-right"><span class="message">{msg}</span></div>'
    
    return HttpResponse(html if html else "<p>No messages yet. Start the conversation!</p>")
