import os
import json
import requests
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from dotenv import load_dotenv
import re

class ObsidianAI:
    def __init__(self, vault_path, model_name="mistral"):
        self.vault_path = Path(vault_path)
        self.model_name = model_name
        self.console = Console()
        self.ollama_url = "http://localhost:11434/api/generate"
        self.cache = {}  # Simple cache for file contents
        
        # Verify vault path exists
        if not self.vault_path.exists():
            raise Exception(f"Vault path does not exist: {vault_path}")
        
        # Verify Ollama is running
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                raise Exception("Ollama API is not responding correctly")
            print(f"Ollama is running and accessible")
        except Exception as e:
            raise Exception(f"Failed to connect to Ollama: {str(e)}")
        
    @staticmethod
    def find_obsidian_vaults():
        home = Path.home()
        possible_locations = [
            home / "Documents" / "Obsidian",
            home / "Desktop",
            home / "Documents",
            home
        ]
        
        vaults = []
        for location in possible_locations:
            if location.exists():
                for item in location.iterdir():
                    if item.is_dir():
                        # Check if it might be an Obsidian vault
                        if (item / ".obsidian").exists() or any(f.suffix == ".md" for f in item.rglob("*.md")):
                            vaults.append(item)
        
        return vaults
        
    def read_markdown_file(self, file_path):
        # Use cache if available
        if str(file_path) in self.cache:
            return self.cache[str(file_path)]
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Cache the content
                self.cache[str(file_path)] = content
                return content
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            return ""
            
    def get_all_markdown_files(self):
        files = list(self.vault_path.rglob("*.md"))
        print(f"Found {len(files)} markdown files in {self.vault_path}")
        return files
        
    def query_ollama(self, prompt, context=""):
        data = {
            "model": self.model_name,
            "prompt": f"Context: {context}\n\nQuestion: {prompt}",
            "stream": False
        }
        
        try:
            print(f"Sending request to Ollama with model: {self.model_name}")
            response = requests.post(self.ollama_url, json=data)
            response.raise_for_status()
            result = response.json()
            print(f"Received response from Ollama: {result}")
            return result["response"]
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to Ollama. Make sure it's running.")
        except requests.exceptions.HTTPError as e:
            raise Exception(f"Ollama API error: {str(e)}")
        except Exception as e:
            raise Exception(f"Error querying Ollama: {str(e)}")
            
    def search_notes(self, query):
        try:
            print(f"Searching notes in: {self.vault_path}")
            relevant_files = []
            query_terms = query.lower().split()
            
            # Get all markdown files once
            all_files = self.get_all_markdown_files()
            
            # Process files in batches for better performance
            batch_size = 10
            for i in range(0, len(all_files), batch_size):
                batch = all_files[i:i+batch_size]
                for file_path in batch:
                    content = self.read_markdown_file(file_path)
                    # Check if any of the query terms are in the content
                    if any(term in content.lower() for term in query_terms):
                        relevant_files.append((file_path, content))
                        print(f"Found relevant file: {file_path}")
            
            print(f"Found {len(relevant_files)} relevant files")
            return relevant_files
        except Exception as e:
            raise Exception(f"Error searching notes: {str(e)}")
        
    def process_query(self, user_query):
        relevant_files = self.search_notes(user_query)
        
        if not relevant_files:
            self.console.print("[yellow]No relevant notes found.[/yellow]")
            return
            
        context = ""
        for file_path, content in relevant_files[:3]:
            context += f"\nFile: {file_path.name}\n{content}\n"
            
        response = self.query_ollama(user_query, context)
        if response:
            self.console.print(Panel(response, title="AI Response", border_style="green"))
            
def main():
    console = Console()
    console.print(Panel("Obsidian AI Assistant", style="bold blue"))
    
    # Find available vaults
    vaults = ObsidianAI.find_obsidian_vaults()
    if not vaults:
        console.print("[red]No Obsidian vaults found in common locations.[/red]")
        vault_path = Prompt.ask("Please enter the full path to your Obsidian vault")
    else:
        console.print("\nAvailable Obsidian vaults:")
        for i, vault in enumerate(vaults, 1):
            console.print(f"{i}. {vault}")
        
        choice = Prompt.ask("Select a vault number", default="1")
        try:
            vault_path = str(vaults[int(choice) - 1])
        except (ValueError, IndexError):
            vault_path = Prompt.ask("Please enter the full path to your Obsidian vault")
    
    model_name = Prompt.ask("Enter Ollama model name", default="mistral")
    
    ai = ObsidianAI(vault_path, model_name)
    
    while True:
        query = Prompt.ask("\nEnter your question (or 'exit' to quit)")
        if query.lower() == 'exit':
            break
            
        ai.process_query(query)

if __name__ == "__main__":
    main() 