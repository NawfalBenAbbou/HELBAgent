#!/bin/bash


echo "INITIALISATION OF HELBAGENT"


# 1. Installation des dÃ©pendances

pip install django django-crispy-forms crispy-bootstrap4 Pillow groq

# 2. Application des migrations

python3 manage.py makemigrations
python3 manage.py migrate

if ! command -v curl &> /dev/null
then
    echo "Installing curl"
    echo "helb" | sudo -S apt install curl
else
    echo "curl already installed"
fi

if ! command -v ollama &> /dev/null
then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama already installed"
fi
ollama pull  smollm:135m



# 3. Lancement du serveur
echo "Everything is ready "

echo "----------------------------------------"


python3 manage.py runserver
