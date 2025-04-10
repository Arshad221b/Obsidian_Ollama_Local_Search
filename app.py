import sys
import os
import logging
import traceback
import requests

# Set up logging
logging.basicConfig(filename='app_error.log', level=logging.DEBUG)
logging.debug(f'Python path: {sys.path}')
logging.debug(f'Current directory: {os.getcwd()}')
try:
    logging.debug('Starting imports...')
    from flask import Flask, render_template
    from flask_socketio import SocketIO, emit
    from obsidian_ai import ObsidianAI
    from pathlib import Path
    import markdown
    import re

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    socketio = SocketIO(app, cors_allowed_origins="*")

    ai_instance = None

    # Configure markdown extensions
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables'])

    def get_available_models():
        """Fetch available models from Ollama"""
        try:
            response = requests.get('http://localhost:11434/api/tags')
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
            return []
        except Exception as e:
            print(f"Error fetching models: {str(e)}")
            return []

    @app.route('/')
    def index():
        # Find available vaults
        vaults = ObsidianAI.find_obsidian_vaults()
        vault_list = [str(vault) for vault in vaults]
        
        # Get available models
        models = get_available_models()
        if not models:  # Fallback models if Ollama is not running
            models = ['mistral', 'llama2', 'codellama', 'neural-chat']
        
        return render_template('index.html', vaults=vault_list, models=models)

    @socketio.on('initialize')
    def handle_initialize(data):
        global ai_instance
        vault_path = data.get('vault_path')
        model_name = data.get('model_name', 'mistral')
        
        if not vault_path:
            emit('initialize_response', {'status': 'error', 'message': 'Vault path is required'})
            return
        
        try:
            print(f"Initializing with vault path: {vault_path} and model: {model_name}")
            ai_instance = ObsidianAI(vault_path, model_name)
            emit('initialize_response', {'status': 'success', 'message': 'AI Assistant initialized successfully'})
        except Exception as e:
            print(f"Initialization error: {str(e)}")
            print(traceback.format_exc())
            emit('initialize_response', {'status': 'error', 'message': str(e)})

    @socketio.on('query')
    def handle_query(data):
        if not ai_instance:
            emit('query_response', {'status': 'error', 'message': 'AI Assistant not initialized'})
            return
        
        user_query = data.get('query')
        
        if not user_query:
            emit('query_response', {'status': 'error', 'message': 'Query is required'})
            return
        
        try:
            print(f"Processing query: {user_query}")
            relevant_files = ai_instance.search_notes(user_query)
            
            if not relevant_files:
                emit('query_response', {
                    'status': 'success',
                    'response': 'No relevant notes found.',
                    'files': []
                })
                return
            
            context = ""
            for file_path, content in relevant_files[:3]:
                context += f"\nFile: {file_path.name}\n{content}\n"
            
            print("Querying Ollama...")
            response = ai_instance.query_ollama(user_query, context)
            print(f"Received response: {response}")
            
            # Format the response as HTML
            formatted_response = format_markdown_response(response)
            
            emit('query_response', {
                'status': 'success',
                'response': formatted_response,
                'files': [{'name': str(f[0].name), 'path': str(f[0])} for f in relevant_files[:3]]
            })
        except Exception as e:
            print(f"Query error: {str(e)}")
            print(traceback.format_exc())
            emit('query_response', {'status': 'error', 'message': str(e)})

    def format_markdown_response(text):
        """Format the response with proper Markdown styling"""
        # Convert markdown to HTML
        html = md.convert(text)
        
        # Add custom styling for Obsidian-like formatting
        styled_html = f"""
        <div class="markdown-content">
            {html}
        </div>
        """
        
        return styled_html

    if __name__ == '__main__':
        socketio.run(app, host='0.0.0.0', port=5001, debug=True)
except Exception as e:
    logging.error(f"Error starting the application: {str(e)}")
    logging.error(traceback.format_exc()) 