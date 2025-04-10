import sys
import os
import logging

# Set up logging
logging.basicConfig(filename='app_error.log', level=logging.DEBUG)
logging.debug(f'Python path: {sys.path}')
logging.debug(f'Current directory: {os.getcwd()}')
try:
    logging.debug('Starting imports...')
    from flask import Flask, render_template, request, jsonify
    from flask_socketio import SocketIO
    from obsidian_ai import ObsidianAI
    from pathlib import Path
    import traceback
    import markdown
    import re

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key'
    socketio = SocketIO(app)

    ai_instance = None

    # Configure markdown extensions
    md = markdown.Markdown(extensions=['extra', 'codehilite', 'tables'])

    @app.route('/')
    def index():
        # Find available vaults
        vaults = ObsidianAI.find_obsidian_vaults()
        vault_list = [str(vault) for vault in vaults]
        return render_template('index.html', vaults=vault_list)

    @app.route('/initialize', methods=['POST'])
    def initialize():
        global ai_instance
        data = request.json
        vault_path = data.get('vault_path')
        model_name = data.get('model_name', 'mistral')
        
        if not vault_path:
            return jsonify({'status': 'error', 'message': 'Vault path is required'})
        
        try:
            print(f"Initializing with vault path: {vault_path} and model: {model_name}")
            ai_instance = ObsidianAI(vault_path, model_name)
            return jsonify({'status': 'success', 'message': 'AI Assistant initialized successfully'})
        except Exception as e:
            print(f"Initialization error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)})

    @app.route('/query', methods=['POST'])
    def query():
        if not ai_instance:
            return jsonify({'status': 'error', 'message': 'AI Assistant not initialized'})
        
        data = request.json
        user_query = data.get('query')
        
        if not user_query:
            return jsonify({'status': 'error', 'message': 'Query is required'})
        
        try:
            print(f"Processing query: {user_query}")
            relevant_files = ai_instance.search_notes(user_query)
            
            if not relevant_files:
                return jsonify({
                    'status': 'success',
                    'response': 'No relevant notes found.',
                    'files': []
                })
            
            context = ""
            for file_path, content in relevant_files[:3]:
                context += f"\nFile: {file_path.name}\n{content}\n"
            
            print("Querying Ollama...")
            response = ai_instance.query_ollama(user_query, context)
            print(f"Received response: {response}")
            
            # Format the response as HTML
            formatted_response = format_markdown_response(response)
            
            return jsonify({
                'status': 'success',
                'response': formatted_response,
                'files': [{'name': str(f[0].name), 'path': str(f[0])} for f in relevant_files[:3]]
            })
        except Exception as e:
            print(f"Query error: {str(e)}")
            print(traceback.format_exc())
            return jsonify({'status': 'error', 'message': str(e)})

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
        socketio.run(app, debug=True)
except Exception as e:
    logging.error(f"Error starting the application: {str(e)}")
    logging.error(traceback.format_exc()) 